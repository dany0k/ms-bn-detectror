export interface Project {
    id: number
    name: string
    description: string
    format: string
    created_at: string
    snapshots_count: number
}

export interface Snapshot {
    id: number
    project_id: number
    created_at: string
    edge_count: number
    bottleneck_count: number
}

export interface EdgeResult {
    name: string
    source: string
    destination: string
    rpc_type: string
    records_amount: number
    severity: 'ok' | 'warning' | 'critical'
    p95_growth: number
    is_bottleneck: boolean
    bin_count: number
    onset_rps: number | null
}

export interface EdgePage {
    total: number
    page: number
    page_size: number
    pages: number
    items: EdgeResult[]
    snapshot_id: number
    snapshot_at: string
}

export interface RpsBin {
    rps_min: number
    rps_max: number
    rps_center: number
    p50_ms: number
    p75_ms: number
    p95_ms: number
    count: number
    reliable: boolean
}

export interface PerSecond {
    second: number
    rps: number
    p50_ms: number
    p75_ms: number
    p95_ms: number
}

export interface AnalysisResult {
    edge_name: string
    global_min_ms: number
    global_max_ms: number
    global_p50_ms: number
    global_p75_ms: number
    global_p95_ms: number
    total_records: number
    rps_bins: RpsBin[]
    per_second: PerSecond[]
    raw_timestamps: number[]
    raw_latencies: number[]
}

export interface EdgeFilters {
    severity?: string
    rpc_type?: string
    service?: string
    min_p95_growth?: number
    sort_by?: string
    page?: number
    page_size?: number
}
