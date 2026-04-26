import type {AnalysisResult, EdgeFilters, EdgePage, Project, Snapshot,} from './types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
    const res = await fetch(url, {
        headers: {'Content-Type': 'application/json'},
        ...options,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({error: res.statusText}))
        throw new Error(err.error ?? res.statusText)
    }
    return res.json()
}

// Projects
export const getProjects = () =>
    request<Project[]>(`${BASE}/projects`)

export const createProject = (name: string, description: string, format = 'alibaba') =>
    request<Project>(`${BASE}/projects`, {
        method: 'POST',
        body: JSON.stringify({name, description, format}),
    })

export const getProject = (id: number) =>
    request<Project>(`${BASE}/projects/${id}`)

export const deleteProject = (id: number) =>
    request<{ deleted: number }>(`${BASE}/projects/${id}`, {method: 'DELETE'})

// Load
export const loadProject = (id: number, path: string) =>
    request<{ snapshot_id: number; edges: number; bottlenecks: number }>(
        `${BASE}/projects/${id}/load`,
        {method: 'POST', body: JSON.stringify({path})},
    )

// Edges
export const getEdges = (id: number, filters: EdgeFilters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== '' && v !== null) params.set(k, String(v))
    })
    const qs = params.toString()
    return request<EdgePage>(`${BASE}/projects/${id}/edges${qs ? `?${qs}` : ''}`)
}

// Snapshots
export const getSnapshots = (id: number) =>
    request<Snapshot[]>(`${BASE}/projects/${id}/snapshots`)

// Folder picker (Windows only — backend opens native dialog)
export const browseFolder = () =>
    request<{ path?: string; cancelled?: boolean; error?: string }>('/api/browse')

// Analysis
export const getAnalysis = (projectId: number, edgeName: string) =>
    request<AnalysisResult>(
        `${BASE}/projects/${projectId}/analyse/${encodeURIComponent(edgeName)}`,
    )
