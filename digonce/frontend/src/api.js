import axios from 'axios'

const BASE = '/api'
export const api = axios.create({ baseURL: BASE, timeout: 15000 })

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ns_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const getSummary = () => api.get('/summary').then(r => r.data)
export const getCorridors = () => api.get('/corridors').then(r => r.data)
export const getAssets = (params) => api.get('/assets', { params }).then(r => r.data)
export const getAsset = (id) => api.get(`/assets/${id}`).then(r => r.data)
export const getWards = () => api.get('/wards').then(r => r.data)
export const getAuditEvents = (params) => api.get('/admin/audit', { params }).then(r => r.data)
export const getLeaks = () => api.get('/leaks').then(r => r.data)
export const getTraffic = () => api.get('/traffic').then(r => r.data)
export const getModels = () => api.get('/models').then(r => r.data)
export const getExperiments = () => api.get('/experiments').then(r => r.data)
export const getLive = () => api.get('/live', { timeout: 4000 }).then(r => r.data)
export const postPlan = (body) => api.post('/plan', body).then(r => r.data)
export const postRecommend = (body) => api.post('/recommend', body).then(r => r.data)
export const postAgent = (message, history = []) => api.post('/agent', { message, history }).then(r => r.data)
export const postScore = (asset_id) => api.post('/score', { asset_id }).then(r => r.data)
export const getFeedback = (params) => api.get('/feedback', { params }).then(r => r.data)
export const postFeedback = (body) => api.post('/feedback', body).then(r => r.data)
export const patchFeedback = (id, status) => api.patch(`/feedback/${id}`, { status }).then(r => r.data)

// Auth
export const authRegister = (body) => api.post('/auth/register', body).then(r => r.data)
export const authBootstrap = (body) => api.post('/auth/bootstrap', body).then(r => r.data)
export const authLogin = (body) => api.post('/auth/login', body, { timeout: 8000 }).then(r => r.data)
export const authLogout = () => api.post('/auth/logout').then(r => r.data)
export const authMe = () => api.get('/auth/me').then(r => r.data)

// Users (admin)
export const getUsers = (params) => api.get('/users', { params }).then(r => r.data)
export const createManagedUser = (body) => api.post('/users', body).then(r => r.data)
export const updateManagedUser = (id, body) => api.patch(`/users/${id}`, body).then(r => r.data)
export const archiveManagedUser = (id) => api.post(`/users/${id}/archive`).then(r => r.data)
export const restoreManagedUser = (id) => api.post(`/users/${id}/restore`).then(r => r.data)
export const updateReport = (id, body) => api.put(`/reports/${id}`, body).then(r => r.data)
export const archiveReport = (id) => api.post(`/reports/${id}/archive`).then(r => r.data)
export const restoreReport = (id) => api.post(`/reports/${id}/restore`).then(r => r.data)
export const updateIncident = (id, body) => api.put(`/incidents/${id}`, body).then(r => r.data)
export const archiveIncident = (id) => api.post(`/incidents/${id}/archive`).then(r => r.data)
export const restoreIncident = (id) => api.post(`/incidents/${id}/restore`).then(r => r.data)
export const getManagedAssets = (params) => api.get('/admin/assets', { params }).then(r => r.data)
export const createManagedAsset = (body) => api.post('/admin/assets', body).then(r => r.data)
export const updateManagedAsset = (id, body) => api.put(`/admin/assets/${id}`, body).then(r => r.data)
export const archiveManagedAsset = (id) => api.post(`/admin/assets/${id}/archive`).then(r => r.data)
export const restoreManagedAsset = (id) => api.post(`/admin/assets/${id}/restore`).then(r => r.data)

// Citizen reports
export const createReport = (body) => api.post('/reports', body).then(r => r.data)
export const getReports = (params) => api.get('/reports', { params }).then(r => r.data)
export const getReport = (id) => api.get(`/reports/${id}`).then(r => r.data)
export const patchReport = (id, body) => api.patch(`/reports/${id}`, body).then(r => r.data)
export const getCommunityReports = (params) => api.get('/community/reports', { params }).then(r => r.data)
export const getCommunityWork = (params) => api.get('/community/work', { params }).then(r => r.data)
export const acknowledgeCommunityReport = (id) => api.post(`/community/reports/${id}/acknowledge`).then(r => r.data)
export const commentOnCommunityReport = (id, message) => api.post(`/community/reports/${id}/comments`, { message }).then(r => r.data)
export const getCommunitySubscription = () => api.get('/community/subscription').then(r => r.data)
export const setCommunitySubscription = (area) => api.put('/community/subscription', area).then(r => r.data)

// Incidents
export const createIncident = (body) => api.post('/incidents', body).then(r => r.data)
export const getIncidents = (params) => api.get('/incidents', { params }).then(r => r.data)
export const getIncident = (id) => api.get(`/incidents/${id}`).then(r => r.data)
export const patchIncident = (id, body) => api.patch(`/incidents/${id}`, body).then(r => r.data)
export const addEvidence = (id, bodyOrUrl, note = '') => {
  if (typeof bodyOrUrl === 'object') {
    return api.post(`/incidents/${id}/evidence`, bodyOrUrl).then(r => r.data)
  }
  return api.post(`/incidents/${id}/evidence`, null, { params: { evidence_url: bodyOrUrl, note } }).then(r => r.data)
}

// Attention & Priority
export const getAttentionAreas = (params) => api.get('/attention', { params }).then(r => r.data)

// Governance portal
export const getGovernanceState = () => api.get('/governance/state').then(r => r.data)
export const getGovernanceDistrict = (district) => api.get('/governance/district', { params: { district } }).then(r => r.data)
export const getGovernanceArea = (params) => api.get('/governance/area', { params }).then(r => r.data)

// Development projects
export const getProjects = (params) => api.get('/projects', { params }).then(r => r.data)
export const getProject = (id) => api.get(`/projects/${id}`).then(r => r.data)
export const createProject = (body) => api.post('/projects', body).then(r => r.data)
export const updateProject = (id, body) => api.patch(`/projects/${id}`, body).then(r => r.data)
export const archiveProject = (id) => api.post(`/projects/${id}/archive`).then(r => r.data)
export const addProjectMilestone = (id, body) => api.post(`/projects/${id}/milestones`, body).then(r => r.data)
export const updateProjectMilestone = (id, milestoneId, completed) => api.patch(`/projects/${id}/milestones/${milestoneId}`, { completed }).then(r => r.data)
export const addProjectExpenditure = (id, body) => api.post(`/projects/${id}/expenditures`, body).then(r => r.data)

// In-app Notifications
export const getNotifications = (params) => api.get('/notifications', { params }).then(r => r.data)
export const markNotificationRead = (id) => api.patch(`/notifications/${id}/read`).then(r => r.data)
export const markAllNotificationsRead = () => api.post('/notifications/read-all').then(r => r.data)

// Geography & jurisdiction
export const getGeoHierarchy = () => api.get('/geo/hierarchy').then(r => r.data)
export const getGeoDistricts = () => api.get('/geo/districts').then(r => r.data)
export const searchGeo = (q, limit = 8) => api.get('/geo/search', { params: { q, limit } }).then(r => r.data)
export const reverseGeo = (lat, lon) => api.get('/geo/reverse', { params: { lat, lon } }).then(r => r.data)
export const getJurisdiction = (params) => api.get('/geo/jurisdiction', { params }).then(r => r.data)
export const getNearbyReports = (params) => api.get('/reports/nearby', { params }).then(r => r.data)

export function liveWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  if (import.meta.env.DEV) return `${proto}://${window.location.host}/ws/live`
  return `${proto}://${window.location.host}/ws/live`
}

// District intelligence & directory
export const getDistrictDirectory = (params) => api.get('/directory/districts', { params }).then(r => r.data)
export const getDistrictProfile = (id) => api.get(`/directory/districts/${id}`).then(r => r.data)
export const getOfficers = (params) => api.get('/directory/officers', { params }).then(r => r.data)
export const getOfficer = (id) => api.get(`/directory/officers/${id}`).then(r => r.data)
export const createOfficer = (body) => api.post('/directory/officers', body).then(r => r.data)
export const updateOfficer = (id, body) => api.put(`/directory/officers/${id}`, body).then(r => r.data)
export const archiveOfficer = (id) => api.post(`/directory/officers/${id}/archive`).then(r => r.data)
export const getOffices = (params) => api.get('/directory/offices', { params }).then(r => r.data)
export const getOffice = (id) => api.get(`/directory/offices/${id}`).then(r => r.data)
export const createOffice = (body) => api.post('/directory/offices', body).then(r => r.data)
export const updateOffice = (id, body) => api.put(`/directory/offices/${id}`, body).then(r => r.data)
export const archiveOffice = (id) => api.post(`/directory/offices/${id}/archive`).then(r => r.data)
export const getPublicServices = (params) => api.get('/directory/services', { params }).then(r => r.data)
export const updatePublicService = (id, body) => api.put(`/directory/services/${id}`, body).then(r => r.data)
export const findLocalOfficer = (params) => api.get('/directory/find-local-officer', { params }).then(r => r.data)
export const getAnnouncements = (params) => api.get('/directory/announcements', { params }).then(r => r.data)
export const createAnnouncement = (body) => api.post('/directory/announcements', body).then(r => r.data)
export const updateAnnouncement = (id, body) => api.put(`/directory/announcements/${id}`, body).then(r => r.data)
export const archiveAnnouncement = (id) => api.post(`/directory/announcements/${id}/archive`).then(r => r.data)

// Map/location notifications
export const notifyMapLocation = (body) => api.post('/map/notify', body).then(r => r.data)
