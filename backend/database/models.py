# backend/database/models.py

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean,
    SmallInteger, Text, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class MetricSample(Base):
    """
    FR-1.2: Stores every raw metric poll from Kubernetes.
    One row per (service x metric_type) per polling tick.
    """
    __tablename__ = "metric_samples"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    timestamp    = Column(DateTime(timezone=True), nullable=False, default=_now)
    service      = Column(String(100), nullable=False)       # e.g. "payment-service"
    metric_type  = Column(String(30),  nullable=False)       # cpu | memory | restarts | error_rate
    value        = Column(Numeric,     nullable=False)

    anomalies    = relationship("Anomaly", back_populates="metric_sample")


class Anomaly(Base):
    """
    Created when Isolation Forest score > threshold.
    Triggers the multi-agent pipeline.
    """
    __tablename__ = "anomalies"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    metric_sample_id = Column(Integer, ForeignKey("metric_samples.id"), nullable=False)
    score            = Column(Numeric, nullable=False)        # Isolation Forest score [0, 1]
    severity         = Column(String(10), nullable=False)     # low | medium | high
    detected_at      = Column(DateTime(timezone=True), nullable=False, default=_now)

    metric_sample    = relationship("MetricSample", back_populates="anomalies")
    decision         = relationship("Decision", back_populates="anomaly", uselist=False)


class Decision(Base):
    """
    Central audit record: holds the FULL multi-agent debate trail.
    One row per anomaly. JSONB columns carry all rounds of proposals + verdicts.
    """
    __tablename__ = "decisions"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    anomaly_id            = Column(Integer, ForeignKey("anomalies.id"), nullable=False)
    diagnosis_text        = Column(Text, nullable=False)
    remediation_proposals = Column(JSONB, nullable=False)    # [{round, action, justification, confidence}]
    critic_verdicts       = Column(JSONB, nullable=False)    # [{round, verdict, reason}]
    round_count           = Column(SmallInteger, nullable=False)   # 1 or 2
    consensus_reached     = Column(Boolean, nullable=False)
    final_action          = Column(String(30), nullable=False)     # restart|scale_up|...
    risk_tier             = Column(String(10), nullable=False)     # low | high
    confidence_score      = Column(Numeric, nullable=False)
    autonomy_outcome      = Column(String(20), nullable=False)     # auto_executed | escalated
    pipeline_error        = Column(Text, nullable=True)            # FR-3.6: stores error if pipeline fails
    created_at            = Column(DateTime(timezone=True), nullable=False, default=_now)

    anomaly          = relationship("Anomaly", back_populates="decision")
    approval         = relationship("Approval", back_populates="decision", uselist=False)
    execution_result = relationship("ExecutionResult", back_populates="decision", uselist=False)


class Approval(Base):
    """
    Populated ONLY for escalated decisions, after the operator acts.
    action_taken = approve | edit | reject
    """
    __tablename__ = "approvals"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    decision_id     = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    operator        = Column(String(100), nullable=False)
    action_taken    = Column(String(20),  nullable=False)    # approve | edit | reject
    override_action = Column(String(30),  nullable=True)     # populated when action_taken = "edit"
    decided_at      = Column(DateTime(timezone=True), nullable=False, default=_now)

    decision        = relationship("Decision", back_populates="approval")


class ExecutionResult(Base):
    """
    Kubernetes API response (success or failure) after an action executes.
    """
    __tablename__ = "execution_results"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    status      = Column(String(20), nullable=False)    # success | failure
    output      = Column(Text)                           # Raw K8s API response / error trace
    executed_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    decision    = relationship("Decision", back_populates="execution_result")


class AuditLogEntry(Base):
    """
    FR-5.2: Append-only log. Every state transition is written here.
    ref_type = anomaly | decision | execution
    event     = anomaly_detected | diagnosis_complete | round1_proposal |
                round1_critic_approve | round1_critic_revise | round2_proposal |
                round2_critic_approve | round2_critic_revise | no_consensus |
                auto_executed | escalated | operator_approve | operator_edit |
                operator_reject | execution_success | execution_failure
    """
    __tablename__ = "audit_log_entries"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    ref_type  = Column(String(30), nullable=False)
    ref_id    = Column(Integer,    nullable=False)
    event     = Column(String(50), nullable=False)
    detail    = Column(JSONB,      nullable=True)          # optional structured detail
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now)
