const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

function getToken() {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('pmri_token')
}

export function setToken(token: string) {
    if (typeof window !== 'undefined') localStorage.setItem('pmri_token', token)
}

export function logout() {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('pmri_token')
        // Only redirect if not already on auth pages — prevents redirect loops
        const path = window.location.pathname
        if (path !== '/login' && path !== '/signup') {
            window.location.href = '/login'
        }
    }
}

async function fetchApi(endpoint: string, options: RequestInit = {}) {
    const token = getToken()
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {})
    }

    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers })
    if (res.status === 401) {
        logout()
        throw new Error('Session expired')
    }

    const text = await res.text()
    let data
    try { data = text ? JSON.parse(text) : {} } catch (e) { data = text }

    if (!res.ok) {
        throw new Error(data.detail || data.message || `API Error: ${res.status}`)
    }
    return data
}

// ------ AUTH ------
export const apiLogin = (data: any) => fetchApi('/auth/login', { method: 'POST', body: JSON.stringify(data) })
export const apiRegister = (data: any) => fetchApi('/auth/register', { method: 'POST', body: JSON.stringify(data) })
export const apiMe = () => fetchApi('/auth/me')

// ------ ORGS ------
export const apiListOrgs = () => fetchApi('/orgs')
export const apiCreateOrg = (data: any) => fetchApi('/orgs', { method: 'POST', body: JSON.stringify(data) })
export const apiGetOrg = (id: string) => fetchApi(`/orgs/${id}`)
export const apiAddOrgMember = (id: string, email: string, role: string) => fetchApi(`/orgs/${id}/members`, { method: 'POST', body: JSON.stringify({ email, role }) })

// ------ PORTFOLIOS ------
export const apiListPortfolios = (orgId?: string) => fetchApi(`/portfolios${orgId ? `?org_id=${orgId}` : ''}`)
export const apiCreatePortfolio = (data: any) => fetchApi('/portfolios', { method: 'POST', body: JSON.stringify(data) })
export const apiGetPortfolio = (id: string) => fetchApi(`/portfolios/${id}`)
export const apiUpdatePortfolio = (id: string, data: any) => fetchApi(`/portfolios/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
export const apiDeletePortfolio = (id: string) => fetchApi(`/portfolios/${id}`, { method: 'DELETE' })
export const apiUploadCsv = async (id: string, file: File, replace: boolean = false) => {
    const token = getToken()
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/portfolios/${id}/upload?replace=${replace}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd
    })
    if (res.status === 401) {
        logout()
        throw new Error('Session expired. Please log in again.')
    }
    if (!res.ok) {
        let errMsg = `Upload failed (${res.status})`
        try {
            const data = await res.json()
            errMsg = data.detail || data.message || errMsg
        } catch { }
        throw new Error(errMsg)
    }
    return await res.json()
}

// ------ QUOTES ------
export const apiCreateQuote = (data: any) => fetchApi('/quotes', { method: 'POST', body: JSON.stringify(data) })
export const apiGetQuote = (id: string) => fetchApi(`/quotes/${id}`)

// ------ POLICIES ------
export const apiBindPolicy = (quote_id: string) => fetchApi('/policies', { method: 'POST', body: JSON.stringify({ quote_id }) })
export const apiListPolicies = (orgId?: string, status?: string) => {
    const params = new URLSearchParams()
    if (orgId) params.append('org_id', orgId)
    if (status) params.append('status', status)
    const qs = params.toString()
    return fetchApi(`/policies${qs ? `?${qs}` : ''}`)
}
export const apiGetPolicy = (id: string) => fetchApi(`/policies/${id}`)
export const apiDeactivatePolicy = (id: string) => fetchApi(`/policies/${id}/deactivate`, { method: 'PATCH' })
export const apiActivatePolicy = (id: string) => fetchApi(`/policies/${id}/activate`, { method: 'PATCH' })
export const apiDeletePolicy = (id: string) => fetchApi(`/policies/${id}`, { method: 'DELETE' })

// ------ LEDGER & SETTLEMENTS ------
export const apiListLedger = (policyId?: string, orgId?: string) => {
    const params = new URLSearchParams()
    if (policyId) params.append('policy_id', policyId)
    if (orgId) params.append('org_id', orgId)
    const qs = params.toString()
    return fetchApi(`/ledger${qs ? `?${qs}` : ''}`)
}
export const apiRunSettlements = (term?: string) => fetchApi(`/settlements/run${term ? `?term=${term}` : ''}`, { method: 'POST' })
