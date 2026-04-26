import {useEffect, useState} from 'react'
import {ChevronDown, ChevronUp, Search} from 'lucide-react'
import {getAnalysis, getEdges} from '../api/client'
import type {AnalysisResult, EdgeFilters, EdgePage, EdgeResult} from '../api/types'
import {EdgeChart} from './EdgeChart'

interface Props {
    projectId: number
}

const SEVERITY_OPTIONS = ['', 'ok', 'warning', 'critical']
const RPC_OPTIONS = ['', 'http', 'rpc']
const SORT_OPTIONS = [
    {value: 'p95_growth', label: 'P95 рост'},
    {value: 'records_amount', label: 'Записей'},
    {value: 'severity', label: 'Severity'},
    {value: 'source', label: 'Source'},
]

function SeverityBadge({s}: { s: string }) {
    return <span className={`badge badge-${s}`}>{s}</span>
}

export function EdgeTable({projectId}: Props) {
    const [data, setData] = useState<EdgePage | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [filters, setFilters] = useState<EdgeFilters>({
        page: 1, page_size: 50, sort_by: 'p95_growth',
    })
    const [serviceInput, setServiceInput] = useState('')

    const [expanded, setExpanded] = useState<string | null>(null)
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [anaLoading, setAnaLoading] = useState(false)

    const load = async (f: EdgeFilters) => {
        setLoading(true)
        setError(null)
        try {
            setData(await getEdges(projectId, f))
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load(filters)
    }, [projectId])

    const applyFilters = () => {
        const f = {...filters, page: 1, service: serviceInput || undefined}
        setFilters(f)
        load(f)
    }

    const setPage = (p: number) => {
        const f = {...filters, page: p}
        setFilters(f)
        load(f)
    }

    const toggleRow = async (edge: EdgeResult) => {
        if (expanded === edge.name) {
            setExpanded(null);
            setAnalysis(null);
            return
        }
        setExpanded(edge.name)
        setAnalysis(null)
        setAnaLoading(true)
        try {
            setAnalysis(await getAnalysis(projectId, edge.name))
        } catch {
            setAnalysis(null)
        } finally {
            setAnaLoading(false)
        }
    }

    return (
        <div>
            {/* Filters bar */}
            <div style={{display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'flex-end'}}>
                <select
                    style={{width: 130}}
                    value={filters.severity ?? ''}
                    onChange={e => setFilters(f => ({...f, severity: e.target.value || undefined}))}
                >
                    {SEVERITY_OPTIONS.map(s => <option key={s} value={s}>{s || 'Все severity'}</option>)}
                </select>

                <select
                    style={{width: 110}}
                    value={filters.rpc_type ?? ''}
                    onChange={e => setFilters(f => ({...f, rpc_type: e.target.value || undefined}))}
                >
                    {RPC_OPTIONS.map(r => <option key={r} value={r}>{r || 'Все типы'}</option>)}
                </select>

                <div style={{position: 'relative', width: 180}}>
                    <input
                        placeholder="Сервис (mc-1)"
                        value={serviceInput}
                        onChange={e => setServiceInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && applyFilters()}
                    />
                    <Search size={13} style={{
                        position: 'absolute',
                        right: 8,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: '#64748b'
                    }}/>
                </div>

                <input
                    type="number"
                    placeholder="Min p95 growth"
                    style={{width: 130}}
                    value={filters.min_p95_growth ?? ''}
                    onChange={e => setFilters(f => ({
                        ...f,
                        min_p95_growth: e.target.value ? +e.target.value : undefined
                    }))}
                />

                <select
                    style={{width: 130}}
                    value={filters.sort_by ?? 'p95_growth'}
                    onChange={e => setFilters(f => ({...f, sort_by: e.target.value}))}
                >
                    {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>↓ {o.label}</option>)}
                </select>

                <button className="btn-primary" onClick={applyFilters}>Применить</button>
            </div>

            {error && <div className="error-box" style={{marginBottom: 12}}>{error}</div>}
            {loading && <div style={{textAlign: 'center', padding: 24}}>
                <div className="spinner"/>
            </div>}

            {data && !loading && (
                <>
                    <div style={{color: '#64748b', fontSize: 12, marginBottom: 8}}>
                        Найдено: {data.total} · Страница {data.page} из {data.pages}
                        {data.snapshot_at && ` · Снапшот от ${new Date(data.snapshot_at).toLocaleString('ru')}`}
                    </div>

                    <div style={{overflowX: 'auto'}}>
                        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: 13}}>
                            <thead>
                            <tr style={{
                                borderBottom: '1px solid var(--border)',
                                color: '#64748b',
                                fontSize: 11,
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em'
                            }}>
                                <th style={th}>Ребро</th>
                                <th style={th}>RPC</th>
                                <th style={th}>Записей</th>
                                <th style={th}>Severity</th>
                                <th style={th}>P95 рост</th>
                                <th style={th}>Onset RPS</th>
                                <th style={th}></th>
                            </tr>
                            </thead>
                            <tbody>
                            {data.items.map(edge => (
                                <>
                                    <tr
                                        key={edge.name}
                                        onClick={() => toggleRow(edge)}
                                        style={{
                                            borderBottom: '1px solid var(--border)',
                                            cursor: 'pointer',
                                            transition: 'background .1s',
                                            background: expanded === edge.name ? 'var(--surface2)' : 'transparent',
                                        }}
                                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface2)')}
                                        onMouseLeave={e => (e.currentTarget.style.background = expanded === edge.name ? 'var(--surface2)' : 'transparent')}
                                    >
                                        <td style={{...td, fontFamily: 'monospace', color: '#94a3b8'}}>{edge.name}</td>
                                        <td style={td}><span className="rpc-tag">{edge.rpc_type}</span></td>
                                        <td style={td}>{edge.records_amount.toLocaleString()}</td>
                                        <td style={td}><SeverityBadge s={edge.severity}/></td>
                                        <td style={{...td, color: growthColor(edge.p95_growth), fontWeight: 600}}>
                                            {edge.p95_growth > 0 ? `×${edge.p95_growth.toFixed(2)}` : '—'}
                                        </td>
                                        <td style={{
                                            ...td,
                                            color: '#64748b'
                                        }}>{edge.onset_rps ? `${edge.onset_rps.toFixed(1)}` : '—'}</td>
                                        <td style={td}>{expanded === edge.name ? <ChevronUp size={14}/> :
                                            <ChevronDown size={14}/>}</td>
                                    </tr>

                                    {expanded === edge.name && (
                                        <tr key={`${edge.name}-detail`}>
                                            <td colSpan={7}
                                                style={{padding: '12px 0 16px', background: 'var(--surface2)'}}>
                                                {anaLoading
                                                    ? <div style={{textAlign: 'center', padding: 16}}>
                                                        <div className="spinner"/>
                                                    </div>
                                                    : analysis
                                                        ? <div style={{padding: '0 12px'}}><EdgeChart
                                                            analysis={analysis}/></div>
                                                        : <div style={{
                                                            color: '#64748b',
                                                            textAlign: 'center',
                                                            padding: 12
                                                        }}>Нет данных анализа</div>
                                                }
                                            </td>
                                        </tr>
                                    )}
                                </>
                            ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {data.pages > 1 && (
                        <div style={{display: 'flex', gap: 6, marginTop: 12, justifyContent: 'center'}}>
                            <button className="btn-ghost" disabled={data.page === 1}
                                    onClick={() => setPage(data.page - 1)}>←
                            </button>
                            {Array.from({length: Math.min(data.pages, 7)}, (_, i) => {
                                const p = data.pages <= 7 ? i + 1 : i + Math.max(1, data.page - 3)
                                if (p > data.pages) return null
                                return (
                                    <button
                                        key={p}
                                        className={p === data.page ? 'btn-primary' : 'btn-ghost'}
                                        onClick={() => setPage(p)}
                                        style={{minWidth: 32}}
                                    >{p}</button>
                                )
                            })}
                            <button className="btn-ghost" disabled={data.page === data.pages}
                                    onClick={() => setPage(data.page + 1)}>→
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

const th: React.CSSProperties = {padding: '8px 10px', textAlign: 'left', fontWeight: 500}
const td: React.CSSProperties = {padding: '10px 10px'}

function growthColor(g: number) {
    if (g >= 3) return 'var(--critical)'
    if (g >= 1.5) return 'var(--warning)'
    return 'var(--muted)'
}
