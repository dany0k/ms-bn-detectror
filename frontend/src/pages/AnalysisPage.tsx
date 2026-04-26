import {useCallback, useEffect, useState} from 'react'
import {useNavigate, useParams} from 'react-router-dom'
import {AlertTriangle, CheckCircle, ChevronLeft, ChevronRight, XCircle} from 'lucide-react'
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
import {getAnalysis, getEdges} from '../api/client'
import type {AnalysisResult, EdgeResult} from '../api/types'
import {useTheme} from '../hooks/useTheme'

const COLORS = {p50: '#27b07a', p75: '#d4900a', p95: '#d63c3c', rps: '#3557E8'}

function useChartColors() {
    const {theme} = useTheme()
    return {
        grid: theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.06)',
        axis: theme === 'light' ? '#9A9890' : '#64748b',
    }
}

function ChartBox({title, children}: { title: string; children: React.ReactNode }) {
    return (
        <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '12px 14px'
        }}>
            <div style={{
                fontSize: 10,
                color: 'var(--muted)',
                textTransform: 'uppercase' as const,
                letterSpacing: '0.06em',
                marginBottom: 10,
                fontWeight: 600
            }}>
                {title}
            </div>
            {children}
        </div>
    )
}

function SeverityBanner({edge}: { edge: EdgeResult }) {
    const sev = edge.severity
    const Icon = sev === 'critical' ? XCircle : sev === 'warning' ? AlertTriangle : CheckCircle
    const msg = sev === 'ok'
        ? 'Узкое место не обнаружено'
        : sev === 'warning'
            ? `Предупреждение — P95 вырос в ${edge.p95_growth.toFixed(2)}× при росте нагрузки`
            : `Критическое узкое место — P95 вырос в ${edge.p95_growth.toFixed(2)}×`
    return (
        <div style={{
            background: `var(--${sev === 'ok' ? 'ok' : sev}-bg)`,
            border: `1px solid var(--${sev === 'ok' ? 'ok' : sev}-border)`,
            borderRadius: 'var(--radius)', padding: '8px 12px',
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 12, color: `var(--${sev === 'ok' ? 'ok' : sev})`,
        }}>
            <Icon size={14}/>{msg}
        </div>
    )
}

export function AnalysisPage() {
    const {projectId, '*': edgeWild} = useParams<{ projectId: string; '*': string }>()
    const pid = Number(projectId)
    const edgeName = decodeURIComponent(edgeWild ?? '')
    const navigate = useNavigate()
    const c = useChartColors()

    const [edges, setEdges] = useState<EdgeResult[]>([])
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [search, setSearch] = useState('')
    const [onlyBn, setOnlyBn] = useState(false)

    const tooltipStyle = {
        backgroundColor: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 6, fontSize: 11, color: 'var(--text)',
    }

    // Load edge list for sidebar (fast — DB query)
    useEffect(() => {
        getEdges(pid, {page_size: 200, sort_by: 'p95_growth'})
            .then(p => setEdges(p.items))
            .catch(() => {
            })
    }, [pid])

    // Load analysis for selected edge (fast — DB query)
    const loadAnalysis = useCallback(async (name: string) => {
        setLoading(true);
        setError(null);
        setAnalysis(null)
        try {
            setAnalysis(await getAnalysis(pid, name))
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }, [pid])

    useEffect(() => {
        if (edgeName) loadAnalysis(edgeName)
    }, [edgeName, loadAnalysis])

    const idx = edges.findIndex(e => e.name === edgeName)
    const goPrev = () => idx > 0 && navigate(`/projects/${pid}/analyse/${encodeURIComponent(edges[idx - 1].name).replace(/%2F/g, "/")}`)
    const goNext = () => idx < edges.length - 1 && navigate(`/projects/${pid}/analyse/${encodeURIComponent(edges[idx + 1].name).replace(/%2F/g, "/")}`)

    const filtered = edges.filter(e => {
        if (onlyBn && !e.is_bottleneck) return false
        if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false
        return true
    })

    const current = edges.find(e => e.name === edgeName) ?? null
    const binData = analysis?.rps_bins.map(b => ({
        rps: +b.rps_mid.toFixed(1),
        P50: Math.round(b.p50_ms),
        P75: Math.round(b.p75_ms),
        P95: Math.round(b.p95_ms)
    })) ?? []
    const timeData = (analysis?.per_second ?? []).slice(0, 400).map(s => ({
        t: s.second,
        RPS: +s.rps.toFixed(1),
        P50: Math.round(s.p50_ms),
        P75: Math.round(s.p75_ms),
        P95: Math.round(s.p95_ms)
    }))
    const scatterData = analysis ? analysis.raw_timestamps.slice(0, 1500).map((t, i) => ({
        x: +t.toFixed(1),
        y: Math.round(analysis.raw_latencies[i] ?? 0)
    })) : []

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: '230px 1fr',
            height: 'calc(100vh - 50px)',
            overflow: 'hidden'
        }}>

            {/* ── Sidebar ── */}
            <div style={{
                background: 'var(--surface)',
                borderRight: '1px solid var(--border)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                <div style={{padding: '10px 10px 6px', borderBottom: '1px solid var(--border)', flexShrink: 0}}>
                    <input placeholder="Поиск..." value={search} onChange={e => setSearch(e.target.value)}
                           style={{marginBottom: 7}}/>
                    <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 11,
                        color: 'var(--text2)',
                        cursor: 'pointer'
                    }}>
                        <input type="checkbox" checked={onlyBn} onChange={e => setOnlyBn(e.target.checked)}
                               style={{width: 13, height: 13}}/>
                        Только bottleneck
                    </label>
                </div>
                <div style={{fontSize: 10, color: 'var(--muted)', padding: '5px 10px', flexShrink: 0}}>
                    {filtered.length} рёбер
                </div>
                <div style={{overflowY: 'auto', flex: 1}}>
                    {filtered.map(e => {
                        const isActive = e.name === edgeName
                        const leftColor = e.severity === 'critical' ? 'var(--critical)' : e.severity === 'warning' ? 'var(--warning)' : 'transparent'
                        return (
                            <div
                                key={e.name}
                                onClick={() => navigate(`/projects/${pid}/analyse/${encodeURIComponent(e.name).replace(/%2F/g, "/")}`)}
                                style={{
                                    padding: '7px 10px',
                                    cursor: 'pointer',
                                    borderLeft: `2px solid ${leftColor}`,
                                    background: isActive ? 'var(--surface2)' : 'transparent',
                                    transition: 'background .1s'
                                }}
                                onMouseEnter={el => {
                                    if (!isActive) el.currentTarget.style.background = 'var(--surface2)'
                                }}
                                onMouseLeave={el => {
                                    if (!isActive) el.currentTarget.style.background = 'transparent'
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
                                    {e.source} → {e.destination}
                                </div>
                                <div style={{fontSize: 10, color: 'var(--text2)', marginTop: 1}}>
                                    {e.rpc_type} · {e.records_amount.toLocaleString()} зап.
                                    {e.is_bottleneck && <span style={{
                                        color: e.severity === 'critical' ? 'var(--critical)' : 'var(--warning)',
                                        marginLeft: 4
                                    }}>×{e.p95_growth.toFixed(1)}</span>}
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* ── Detail panel ── */}
            <div style={{
                overflowY: 'auto',
                background: 'var(--bg)',
                padding: 14,
                display: 'flex',
                flexDirection: 'column',
                gap: 10
            }}>

                {/* Prev / Next */}
                <div style={{display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0}}>
                    <button className="btn-ghost" style={{padding: '4px 8px'}} onClick={goPrev} disabled={idx <= 0}>
                        <ChevronLeft size={14}/></button>
                    <span style={{
                        fontSize: 11,
                        color: 'var(--muted)'
                    }}>{idx >= 0 ? `${idx + 1} / ${edges.length}` : '—'}</span>
                    <button className="btn-ghost" style={{padding: '4px 8px'}} onClick={goNext}
                            disabled={idx >= edges.length - 1}><ChevronRight size={14}/></button>
                    <code style={{fontSize: 12, color: 'var(--text)', marginLeft: 4}}>{edgeName}</code>
                </div>

                {/* Always-visible status */}
                {loading && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: 24,
                        justifyContent: 'center',
                        color: 'var(--muted)',
                        fontSize: 13
                    }}>
                        <div className="spinner"/>
                        Загрузка анализа...
                    </div>
                )}

                {error && (
                    <div className="error-box">
                        <div style={{fontWeight: 600, marginBottom: 4}}>Ошибка загрузки анализа</div>
                        <div>{error}</div>
                        <div style={{marginTop: 8, fontSize: 11, opacity: 0.8}}>
                            Если данные были загружены до обновления — удалите <code>bottleneck.db</code> и загрузите
                            логи заново.
                        </div>
                        <button className="btn-ghost" style={{marginTop: 10, fontSize: 11}}
                                onClick={() => loadAnalysis(edgeName)}>
                            Попробовать снова
                        </button>
                    </div>
                )}

                {!loading && !error && !analysis && edgeName && (
                    <div style={{padding: 32, textAlign: 'center', color: 'var(--muted)', fontSize: 13}}>
                        Нет данных анализа. Удалите <code>bottleneck.db</code> и загрузите логи заново.
                    </div>
                )}

                {current && <SeverityBanner edge={current}/>}

                {analysis && (
                    <>
                        {/* Metrics */}
                        <div style={{display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8}}>
                            {[
                                {label: 'P50', value: `${analysis.global_p50_ms.toFixed(1)} ms`},
                                {label: 'P75', value: `${analysis.global_p75_ms.toFixed(1)} ms`},
                                {label: 'P95', value: `${analysis.global_p95_ms.toFixed(1)} ms`},
                                {label: 'Max', value: `${analysis.global_max_ms.toFixed(0)} ms`},
                                {label: 'Записей', value: analysis.total_records.toLocaleString()},
                                {label: 'RPS-бинов', value: String(analysis.rps_bins.length)},
                            ].map(({label, value}) => (
                                <div key={label} style={{
                                    background: 'var(--surface)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius)',
                                    padding: '8px 10px',
                                    textAlign: 'center'
                                }}>
                                    <div style={{fontSize: 16, fontWeight: 700, color: 'var(--text)'}}>{value}</div>
                                    <div style={{fontSize: 10, color: 'var(--muted)', marginTop: 2}}>{label}</div>
                                </div>
                            ))}
                        </div>

                        <ChartBox title="P50 / P75 / P95 по RPS-группам">
                            <ResponsiveContainer width="100%" height={210}>
                                <LineChart data={binData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                    <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                    <XAxis dataKey="rps" stroke={c.axis} fontSize={10} unit=" rps"/>
                                    <YAxis stroke={c.axis} fontSize={10} unit=" ms"/>
                                    <Tooltip contentStyle={tooltipStyle}/>
                                    <Legend wrapperStyle={{fontSize: 11}}/>
                                    <Line isAnimationActive={false} type="monotone" dataKey="P50" stroke={COLORS.p50}
                                          dot={false} strokeWidth={1.5}/>
                                    <Line isAnimationActive={false} type="monotone" dataKey="P75" stroke={COLORS.p75}
                                          dot={false} strokeWidth={1.5}/>
                                    <Line isAnimationActive={false} type="monotone" dataKey="P95" stroke={COLORS.p95}
                                          dot={{r: 3}} strokeWidth={2}/>
                                </LineChart>
                            </ResponsiveContainer>
                        </ChartBox>

                        {timeData.length > 0 && <>
                            <ChartBox title="RPS от времени">
                                <ResponsiveContainer width="100%" height={150}>
                                    <LineChart data={timeData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                        <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                        <YAxis stroke={c.axis} fontSize={10} unit=" rps"/>
                                        <Tooltip contentStyle={tooltipStyle}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="RPS"
                                              stroke={COLORS.rps} dot={false} strokeWidth={1.5}/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </ChartBox>

                            <ChartBox title="P50 / P75 / P95 от времени">
                                <ResponsiveContainer width="100%" height={170}>
                                    <LineChart data={timeData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                        <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                        <YAxis stroke={c.axis} fontSize={10} unit=" ms"/>
                                        <Tooltip contentStyle={tooltipStyle}/>
                                        <Legend wrapperStyle={{fontSize: 11}}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P50"
                                              stroke={COLORS.p50} dot={false} strokeWidth={1.5}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P75"
                                              stroke={COLORS.p75} dot={false} strokeWidth={1.5}/>
                                        <Line isAnimationActive={false} type="monotone" dataKey="P95"
                                              stroke={COLORS.p95} dot={false} strokeWidth={2}/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </ChartBox>

                            <ChartBox title="Нагрузка и P95 (совмещённый)">
                                <ResponsiveContainer width="100%" height={170}>
                                    <LineChart data={timeData} margin={{top: 4, right: 40, left: 0, bottom: 0}}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                        <XAxis dataKey="t" stroke={c.axis} fontSize={10} unit="s"/>
                                        <YAxis yAxisId="l" stroke={COLORS.rps} fontSize={10} unit=" rps"/>
                                        <YAxis yAxisId="r" stroke={COLORS.p95} fontSize={10} unit=" ms"
                                               orientation="right"/>
                                        <Tooltip contentStyle={tooltipStyle}/>
                                        <Legend wrapperStyle={{fontSize: 11}}/>
                                        <Line isAnimationActive={false} yAxisId="l" type="monotone" dataKey="RPS"
                                              stroke={COLORS.rps} dot={false} strokeWidth={1.5}/>
                                        <Line isAnimationActive={false} yAxisId="r" type="monotone" dataKey="P95"
                                              stroke={COLORS.p95} dot={false} strokeWidth={1.5}/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </ChartBox>
                        </>}

                        {scatterData.length > 0 && (
                            <ChartBox title={`Raw latency (${scatterData.length} точек)`}>
                                <ResponsiveContainer width="100%" height={150}>
                                    <ScatterChart margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.grid}/>
                                        <XAxis dataKey="x" stroke={c.axis} fontSize={10} unit="s" name="Time"/>
                                        <YAxis dataKey="y" stroke={c.axis} fontSize={10} unit=" ms" name="Latency"/>
                                        <Tooltip contentStyle={tooltipStyle}/>
                                        <Scatter isAnimationActive={false} data={scatterData} fill={c.axis}
                                                 opacity={0.35}/>
                                    </ScatterChart>
                                </ResponsiveContainer>
                            </ChartBox>
                        )}
                    </>
                )}
            </div>
        </div>
    )
}
