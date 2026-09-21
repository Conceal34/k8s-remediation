import axios from 'axios'

export const API_BASE = import.meta.env.VITE_API_URL || '/api';
const api = axios.create({ baseURL: API_BASE })

export const getEscalatedDecisions = () => api.get('/decisions/escalated')
export const getDecisions          = (params?: { risk?: string; outcome?: string }) =>
  api.get('/decisions/', { params })
export const getDecisionDetail     = (id: number) => api.get(`/decisions/${id}`)
export const getLiveMetrics        = () => api.get('/metrics/live')
export const getActiveAnomalies    = () => api.get('/metrics/anomalies/active')
export const getSettings           = () => api.get('/settings/')
export const submitApproval        = (decisionId: number, body: {
  operator: string; action_taken: string; edited_action?: string
}) => api.post(`/approvals/${decisionId}`, body)
