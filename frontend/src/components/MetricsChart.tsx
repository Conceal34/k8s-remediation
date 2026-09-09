import { useEffect, useRef } from 'react';
import { getLiveMetrics, getActiveAnomalies } from '../api';

export default function MetricsChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let isMounted = true;
    async function drawMetricsChart() {
      const canvas = canvasRef.current;
      if (!canvas || !isMounted) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (!rect) return;

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.scale(dpr, dpr);

      const W = rect.width;
      const H = rect.height;
      const pad = { top: 20, right: 20, bottom: 40, left: 50 };
      const chartW = W - pad.left - pad.right;
      const chartH = H - pad.top - pad.bottom;

      // Fetch live metric samples and anomalies from FastAPI backend (5-minute window)
      let cpuData: number[] = [];
      let memData: number[] = [];
      let errData: number[] = [];
      let hasAnomaly = false;
      const timeLabels: string[] = [];

      try {
        const [metricsRes, anomaliesRes] = await Promise.all([
          getLiveMetrics(),
          getActiveAnomalies()
        ]);

        const rawSamples = metricsRes.data || [];
        const activeAnomalies = anomaliesRes.data || [];
        hasAnomaly = activeAnomalies.length > 0;

        if (rawSamples.length >= 4) {
          // If there's an anomaly, focus the chart on that service, otherwise default to payment-service
          const targetService = activeAnomalies.length > 0 && activeAnomalies[0].service ? activeAnomalies[0].service : 'payment-service';
          
          // Isolate telemetry for the monitored service
          const targetSamples = rawSamples.filter((s: any) => s.service === targetService);
          const samplesToUse = targetSamples.length >= 4 ? targetSamples : rawSamples;

          const cpus = samplesToUse.filter((s: any) => s.metric_type === 'cpu');
          const mems = samplesToUse.filter((s: any) => s.metric_type === 'memory');
          const errs = samplesToUse.filter((s: any) => s.metric_type === 'error_rate' || s.metric_type === 'errors');

          // Up to 30 samples (5 minutes @ 10-15s intervals)
          const sliceLen = 30;
          const cpuSlice = cpus.slice(-sliceLen);
          const memSlice = mems.slice(-sliceLen);
          const errSlice = errs.slice(-sliceLen);

          cpuData = cpuSlice.map((s: any) => Math.min(100, Math.max(0, parseFloat(s.value) || 0)));
          memData = memSlice.map((s: any) => Math.min(100, Math.max(0, parseFloat(s.value) || 0)));
          errData = errSlice.map((s: any) => {
            const rawErr = parseFloat(s.value) || 0;
            // Scale error rate if fractional (e.g. 0.85 -> 85%)
            return Math.min(100, Math.max(0, rawErr <= 1.0 ? rawErr * 100 : rawErr));
          });

          cpuSlice.forEach((s: any) => {
            const d = new Date(s.timestamp);
            timeLabels.push(d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
          });
        }
      } catch (e) {
        // Fallback to smooth 5m data if offline
      }

      if (cpuData.length < 5) {
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = "var(--text-muted)";
        ctx.font = '14px "Inter", sans-serif';
        ctx.textAlign = "center";
        ctx.fillText("Waiting for telemetry data...", W / 2, H / 2);
        return;
      }

      ctx.clearRect(0, 0, W, H);

      // Grid lines
      ctx.strokeStyle = "rgba(255,255,255,0.04)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {
        const y = pad.top + (chartH / 5) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(W - pad.right, y);
        ctx.stroke();
      }

      // Y-axis labels
      ctx.fillStyle = "#5a6371";
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = "right";
      for (let i = 0; i <= 5; i++) {
        const val = 100 - i * 20;
        const y = pad.top + (chartH / 5) * i;
        ctx.fillText(val + "%", pad.left - 8, y + 4);
      }

      // X-axis time labels (displayed at regular intervals across the 5 minutes)
      ctx.textAlign = "center";
      const step = chartW / Math.max(1, timeLabels.length - 1);
      const labelInterval = Math.max(1, Math.floor(timeLabels.length / 6));
      for (let i = 0; i < timeLabels.length; i += labelInterval) {
        const x = pad.left + step * i;
        ctx.fillText(timeLabels[i], x, H - pad.bottom + 20);
      }

      function drawLine(data: number[], color: string, alpha: number) {
        if (!ctx || data.length === 0) return;
        const points = data.map((v, i) => ({
          x: pad.left + (chartW / Math.max(1, data.length - 1)) * i,
          y: pad.top + chartH - (v / 100) * chartH,
        }));

        const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
        gradient.addColorStop(0, color.replace(")", `,${alpha})`).replace("rgb", "rgba"));
        gradient.addColorStop(1, color.replace(")", ",0)").replace("rgb", "rgba"));

        ctx.beginPath();
        ctx.moveTo(points[0].x, pad.top + chartH);
        points.forEach((p) => ctx.lineTo(p.x, p.y));
        ctx.lineTo(points[points.length - 1].x, pad.top + chartH);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) {
          const cpx = (points[i - 1].x + points[i].x) / 2;
          ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, cpx, (points[i - 1].y + points[i].y) / 2);
        }
        ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        points.forEach((p) => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
          ctx.fillStyle = "#0b0e14";
          ctx.fill();
        });
      }

      drawLine(errData, "rgb(248,81,73)", 0.08);
      drawLine(memData, "rgb(188,140,255)", 0.1);
      drawLine(cpuData, "rgb(99,140,255)", 0.12);

      // Anomaly Highlight Zone
      if (hasAnomaly || cpuData.some(v => v > 80)) {
        const spikeIdx = cpuData.findIndex(v => v > 80);
        const centerIdx = spikeIdx !== -1 ? spikeIdx : Math.max(1, cpuData.length - 5);
        const anomalyX = pad.left + step * Math.max(0, centerIdx - 2);
        const anomalyW = step * 4;
        ctx.fillStyle = "rgba(248,81,73,0.08)";
        ctx.fillRect(anomalyX, pad.top, anomalyW, chartH);
        ctx.strokeStyle = "rgba(248,81,73,0.3)";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(anomalyX, pad.top, anomalyW, chartH);
        ctx.setLineDash([]);

        ctx.fillStyle = "#f85149";
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.textAlign = "center";
        ctx.fillText("⚠️ anomaly detected", anomalyX + anomalyW / 2, pad.top - 6);
      }
    }

    drawMetricsChart();
    const handleResize = () => drawMetricsChart();
    window.addEventListener("resize", handleResize);
    const intervalId = setInterval(drawMetricsChart, 5000);

    return () => {
      isMounted = false;
      window.removeEventListener("resize", handleResize);
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="card chart-card wide" id="metrics-chart-card">
      <div className="card-header">
        <h2 className="card-title">Live Metrics (Last 5 Minutes)</h2>
        <div className="chart-legend">
          <span className="legend-item"><span className="legend-dot cpu"></span>CPU %</span>
          <span className="legend-item"><span className="legend-dot memory"></span>Memory %</span>
          <span className="legend-item"><span className="legend-dot errors"></span>Error Rate</span>
        </div>
      </div>
      <div className="chart-container">
        <canvas id="metrics-chart" ref={canvasRef}></canvas>
      </div>
    </div>
  );
}
