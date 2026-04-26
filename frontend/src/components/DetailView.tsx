import {useCallback, useEffect, useState} from 'react'
import {
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import {AlertTriangle, CheckCircle, Search, XCircle} from 'lucide-react'
import {getAnalysis, getEdges} from '../api/client'
import type {AnalysisResult, EdgePage, EdgeResult} from '../api/types'
import {useTheme} from '../hooks/useTheme'

interface Props {
    projectId: number
}

function useChartColors() {
    const {theme} = useTheme()
    return {
        grid: theme === 'light' ? 'rgba(0,0,0,0.055)' : 'rgba(255,255,255,0.06)',
        axis: theme === 'light' ? '#9A9890' : '#64748b',
        bg: theme === 'light' ? '#FFFFFF' : '#1a1d27',
        p50: '#27b07a',
        p75: '#d4900a',
        p95: '#d63c3c',
        rps: '#3557E8',
        raw: theme === 'light' ? '#aaa8a0' : '#94a3b8',
    }
}

function ChartBox({title, children}: { title: string; children: React.ReactNode }) {
    return (
        <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '10px 12px',
        }}>
            <div style={{
                fontSize: 10,
                color: 'var(--muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 8
            }}>
                {title}
            </div>
            {children}
        </div>
    )
}

function SeverityAlert({edge}: { edge: EdgeResult }) {
    const icon = edge.severity === 'critical'
        ? <XCircle size={15}/>
        : edge.severity === 'warning'
            ? <AlertTriangle size={15}/>
            : <CheckCircle size={15}/>

    const style: React.CSSProperties = {
        background: `var(--${edge.severity === 'ok' ? 'ok' : edge.severity}-bg)`,
        border: `1px solid var(--${edge.severity === 'ok' ? 'ok' : edge.severity}-border)`,
        color: `var(--${edge.severity === 'ok' ? 'ok' : edge.severity})`,
        borderRadius: 'var(--radius)',
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 12,
    }

    const label = edge.severity === 'ok'
        ? 'Узкое место не обнаружено'
        : edge.severity === 'warning'
            ? `Предупреждение — P95 вырос в ${edge.p95_growth.toFixed(2)}× при росте нагрузки`
            : `Критическое узкое место — P95 вырос в ${edge.p95_growth.toFixed(2)}×`

    return <div style={style}>{icon}{label}</div>
}

function MetricCard({label, value}: { label: string; value: string }) {
    return (
        <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '8px 12px'
        }}>
            <div style={{fontSize: 10, color: 'var(--muted)', marginBottom: 3}}>{label}</div>
            <div style={{fontSize: 17, fontWeight: 600, color: 'var(--text)'}}>{value}</div>
        </div>
    )
}

export function DetailView({projectId}: Props) {
    const c = useChartColors()
    const tooltipStyle = {
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        fontSize: 11,
        color: 'var(--text)',
    }

    const [edges, setEdges] = useState<EdgeResult[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [search, setSearch] = useState('')
    const [onlyBn, setOnlyBn] = useState(false)

    const [selected, setSelected] = useState<EdgeResult | null>(null)
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [anaLoad, setAnaLoad] = useState(false)

    const loadEdges = useCallback(async () => {
        setLoading(true)
        try {
            const page: EdgePage = await getEdges(projectId, {page_size: 200, sort_by: 'p95_growth'})
            setEdges(page.items)
            setTotal(page.total)
        } finally {
            setLoading(false)
        }
    }, [projectId])

    useEffect(() => {
        loadEdges()
    }, [loadEdges])

    const selectEdge = async (edge: EdgeResult) => {
        setSelected(edge)
        setAnalysis(null)
        setAnaLoad(true)
        try {
            setAnalysis(await getAnalysis(projectId, edge.name))
        } finally {
            setAnaLoad(false)
        }
    }

    const filtered = edges.filter(e => {
        if (onlyBn && !e.is_bottleneck) return false
        if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false
        return true
    })

    const binData = analysis?.rps_bins.map(b => ({
        rps: +b.rps_mid.toFixed(1),
        P50: Math.round(b.p50_ms),
        P75: Math.round(b.p75_ms),
        P95: Math.round(b.p95_ms),
    })) ?? []

    const timeData = (analysis?.per_second ?? []).slice(0, 400).map(s => ({
        t: s.second,
        RPS: +s.rps.toFixed(1),
        P50: Math.round(s.p50_ms),
        P75: Math.round(s.p75_ms),
        P95: Math.round(s.p95_ms),
    }))

    const scatterData = analysis
        ? analysis.raw_timestamps.slice(0, 2000).map((t, i) => ({
            x: +t.toFixed(1),
            y: Math.round(analysis.raw_latencies[i] ?? 0),
        }))
        : []

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: '240px 1fr',
            height: 'calc(100vh - 52px)',
            overflow: 'hidden'
        }}>

            {/* ── Sidebar ── */}
            <div style={{
                background: 'var(--surface)',
                borderRight: '1px solid var(--border)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}>
                {/* Search */}
                <div style={{padding: '10px 10px 6px', borderBottom: '1px solid var(--border)', flexShrink: 0}}>
                    <div style={{position: 'relative'}}>
                        <input
                            placeholder="Поиск рёбер..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            style={{paddingLeft: 28}}
                        />
                        <Search size={12} style={{
                            position: 'absolute',
                            left: 8,
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'var(--muted)'
                        }}/>
                    </div>
                    <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        marginTop: 7,
                        fontSize: 11,
                        color: 'var(--text2)',
                        cursor: 'pointer'
                    }}>
                        <input type="checkbox" checked={onlyBn} onChange={e => setOnlyBn(e.target.checked)}
                               style={{width: 13, height: 13}}/>
                        Только bottleneck
                    </label>
                </div>

                {/* Count */}
                <div style={{fontSize: 10, color: 'var(--muted)', padding: '5px 10px', flexShrink: 0}}>
                    {loading ? '...' : `${filtered.length} из ${total}`}
                </div>

                {/* List */}
                <div style={{overflowY: 'auto', flex: 1}}>
                    {filtered.map(edge => {
                        const isActive = selected?.name === edge.name
                        const sev = edge.severity
                        const leftColor = sev === 'critical' ? 'var(--critical)' : sev === 'warning' ? 'var(--warning)' : 'transparent'
                        return (
                            <div
                                key={edge.name}
                                onClick={() => selectEdge(edge)}
                                style={{
                                    padding: '7px 10px',
                                    cursor: 'pointer',
                                    borderLeft: `2px solid ${leftColor}`,
                                    background: isActive ? 'var(--surface2)' : 'transparent',
                                    transition: 'background .1s',
                                }}
                                onMouseEnter={e => {
                                    if (!isActive) e.currentTarget.style.background = 'var(--surface2)'
                                }}
                                onMouseLeave={e => {
                                    if (!isActive) e.currentTarget.style.background = 'transparent'
                                }}
                            >
                                <div style={{
                                    fontSize: 11,
                                    fontWeight: 500,
                                    color: 'var(--text)',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis'
                                }}>
                                    {edge.source} → {edge.destination}
                                </div>
                                <div style={{fontSize: 10, color: 'var(--muted)', marginTop: 1}}>
                                    {edge.rpc_type} · {edge.records_amount.toLocaleString()} зап.
                                    {edge.is_bottleneck && (
                                        <span style={{
                                            color: sev === 'critical' ? 'var(--critical)' : 'var(--warning)',
                                            marginLeft: 4
                                        }}>
                      ×{edge.p95_growth.toFixed(1)}
                    </span>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* ── Detail panel ── */}
            <div style={{
                overflowY: 'auto',
                padding: 12,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                background: 'var(--bg)'
            }}>

                {!selected && (
                    <div style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--muted)',
                        flexDirection: 'column',
                        gap: 8
                    }}>
                        <div>Выберите ребро из списка слева</div>
                        <div style={{fontSize: 11}}>Рёбра отсортированы по росту P95</div>
                    </div>
                )}

                {selected && (
                    <>
                        {/* Alert */}
                        <SeverityAlert edge={selected}/>

                        {/* Metrics row */}
                        {analysis && (
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8}}>
                                <MetricCard label="P50" value={`${analysis.global_p50_ms.toFixed(1)} ms`}/>
                                <MetricCard label="P75" value={`${analysis.global_p75_ms.toFixed(1)} ms`}/>
                                <MetricCard label="P95" value={`${analysis.global_p95_ms.toFixed(1)} ms`}/>
                                <MetricCard label="Max" value={`${analysis.global_max_ms.toFixed(0)} ms`}/>
                                <MetricCard label="Записей" value={analysis.total_records.toLocaleString()}/>
                            </div>
                        )}

                        {anaLoad && <div style={{padding: 32, textAlign: 'center'}}>
                            <div className="spinner"/>
                        </div>}

                        {analysis && (<>

                            {/* Chart 1 — P95 by RPS bins */}
                            <ChartBox title="P95 задержки по RPS-группам">
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={binData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                        <XAxis dataKey="rps" stroke={c.axis} fontSize={10} unit=" rps"/>
                                        <YAxis stroke={c.axis} fontSize={10} unit=" ms"/>
                                        <Tooltip contentStyle={tooltipStyle}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P50" stroke={c.p50}
                                              dot={false} strokeWidth={1.5}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P75" stroke={c.p75}
                                              dot={false} strokeWidth={1.5}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P95" stroke={c.p95}
                                              dot={{r: 3}} strokeWidth={2}/>
                                        <Legend wrapperStyle={{fontSize: 11}}/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </ChartBox>

                            {/* Chart 2 — RPS over time */}
                            {timeData.length > 0 && (
                                <ChartBox title="RPS от времени">
                                    <ResponsiveContainer width="100%" height={160}>
                                        <LineChart data={timeData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                            <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                            <YAxis stroke={c.axis} fontSize={10} unit=" rps"/>
                                            <Tooltip contentStyle={tooltipStyle}/>
                                            <Line isAnimationActive={false} type="monotone" dataKey="RPS" stroke={c.rps}
                                                  dot={false} strokeWidth={1.5}/>
                                        </LineChart>
                                    </ResponsiveContainer>
                                </ChartBox>
                            )}

                            {/* Chart 3 — Latency percentiles over time */}
                            {timeData.length > 0 && (
                                <ChartBox title="P50 / P75 / P95 от времени">
                                    <ResponsiveContainer width="100%" height={180}>
                                        <LineChart data={timeData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                            <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                            <YAxis stroke={c.axis} fontSize={10} unit=" ms"/>
                                            <Tooltip contentStyle={tooltipStyle}/>
                                            <Line isAnimationActive={false} type="monotone" dataKey="P50" stroke={c.p50}
                                                  dot={false} strokeWidth={1.5}/>
                                            <Line isAnimationActive={false} type="monotone" dataKey="P75" stroke={c.p75}
                                                  dot={false} strokeWidth={1.5}/>
                                            <Line isAnimationActive={false} type="monotone" dataKey="P95" stroke={c.p95}
                                                  dot={false} strokeWidth={2}/>
                                            <Legend wrapperStyle={{fontSize: 11}}/>
                                        </LineChart>
                                    </ResponsiveContainer>
                                </ChartBox>
                            )}

                            {/* Chart 4 — RPS vs P95 combined */}
                            {timeData.length > 0 && (
                                <ChartBox title="Нагрузка и P95 (совмещённый)">
                                    <ResponsiveContainer width="100%" height={180}>
                                        <LineChart data={timeData} margin={{top: 4, right: 40, left: 0, bottom: 0}}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                            <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                            <YAxis yAxisId="l" stroke={c.rps} fontSize={10} unit=" rps"/>
                                            <YAxis yAxisId="r" stroke={c.p95} fontSize={10} unit=" ms"
                                                   orientation="right"/>
                                            <Tooltip contentStyle={tooltipStyle}/>
                                            <Line isAnimationActive={false} yAxisId="l" type="monotone" dataKey="RPS"
                                                  stroke={c.rps} dot={false} strokeWidth={1.5}/>
                                            <Line isAnimationActive={false} yAxisId="r" type="monotone" dataKey="P95"
                                                  stroke={c.p95} dot={false} strokeWidth={1.5}/>
                                            <Legend wrapperStyle={{fontSize: 11}}/>
                                        </LineChart>
                                    </ResponsiveContainer>
                                </ChartBox>
                            )}

                            {/* Chart 5 — Raw scatter */}
                            {scatterData.length > 0 && (
                                <ChartBox title={`Raw latency (первые ${scatterData.length} точек)`}>
                                    <ResponsiveContainer width="100%" height={160}>
                                        <ScatterChart margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                            <XAxis dataKey="x" stroke={c.axis} fontSize={10} unit="s" name="Time"/>
                                            <YAxis dataKey="y" stroke={c.axis} fontSize={10} unit=" ms" name="Latency"/>
                                            <Tooltip contentStyle={tooltipStyle} cursor={{strokeDasharray: '3 3'}}/>
                                            <Scatter isAnimationActive={false} data={scatterData} fill={c.raw}
                                                     opacity={0.4}/>
                                        </ScatterChart>
                                    </ResponsiveContainer>
                                </ChartBox>
                            )}

                        </>)}
                    </>
                )}
            </div>
        </div>
    )
}
