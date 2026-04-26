import React, {useCallback, useEffect, useState} from 'react'
import {useNavigate, useParams} from 'react-router-dom'
import {ChevronDown, ChevronUp, ExternalLink, FolderSearch, History, Upload} from 'lucide-react'
import {CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,} from 'recharts'
import {browseFolder, getAnalysis, getEdges, getProject, getSnapshots, loadProject} from '../api/client'
import type {AnalysisResult, EdgeResult, Project, Snapshot} from '../api/types'
import {useTheme} from '../hooks/useTheme'

const COLORS = {p50: '#27b07a', p75: '#d4900a', p95: '#d63c3c', rps: '#3557E8'}

function growthColor(g: number) {
  if (g >= 3) return 'var(--critical)'
  if (g >= 1.5) return 'var(--warning)'
  return 'var(--muted)'
}

function SeverityDot({s}: { s: string }) {
  const color = s === 'critical' ? 'var(--critical)' : s === 'warning' ? 'var(--warning)' : 'var(--ok)'
  return <span style={{
    display: 'inline-block',
    width: 7,
    height: 7,
    borderRadius: '50%',
    background: color,
    marginRight: 6,
    flexShrink: 0
  }}/>
}

function InlineCharts({analysis}: { analysis: AnalysisResult }) {
  const {theme} = useTheme()
  const grid = theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.06)'
  const axis = theme === 'light' ? '#9A9890' : '#64748b'
  const tooltipStyle = {
    backgroundColor: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 6, fontSize: 11, color: 'var(--text)',
  }
  const binData = analysis.rps_bins.map(b => ({
    rps: +b.rps_center.toFixed(1), P50: Math.round(b.p50_ms),
    P75: Math.round(b.p75_ms), P95: Math.round(b.p95_ms),
  }))
  const timeData = analysis.per_second.slice(0, 300).map(s => ({
    t: s.second, RPS: +s.rps.toFixed(1), P95: Math.round(s.p95_ms),
  }))

  return (
      <div style={{
        padding: '14px 16px',
        background: 'var(--bg)',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12
      }}>
        <div style={{
          gridColumn: '1 / -1',
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: 8,
          marginBottom: 4
        }}>
          {[
            {label: 'P50', value: `${analysis.global_p50_ms.toFixed(1)} ms`},
            {label: 'P75', value: `${analysis.global_p75_ms.toFixed(1)} ms`},
            {label: 'P95', value: `${analysis.global_p95_ms.toFixed(1)} ms`},
            {label: 'Max', value: `${analysis.global_max_ms.toFixed(0)} ms`},
            {label: 'Записей', value: analysis.total_records.toLocaleString()},
            {label: 'Бинов', value: String(analysis.rps_bins.length)},
          ].map(({label, value}) => (
              <div key={label} style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '7px 10px',
                textAlign: 'center'
              }}>
                <div style={{fontSize: 15, fontWeight: 700, color: 'var(--text)'}}>{value}</div>
                <div style={{fontSize: 10, color: 'var(--muted)', marginTop: 1}}>{label}</div>
              </div>
          ))}
        </div>

        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '10px 12px'
        }}>
          <div style={{
            fontSize: 10,
            color: 'var(--muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 8
          }}>P50 / P75 / P95 по RPS-бинам
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={binData} margin={{top: 4, right: 8, left: 0, bottom: 0}}>
              <CartesianGrid strokeDasharray="3 3" stroke={grid}/>
              <XAxis dataKey="rps" stroke={axis} fontSize={10} unit=" rps"/>
              <YAxis stroke={axis} fontSize={10} unit=" ms"/>
              <Tooltip contentStyle={tooltipStyle}/>
              <Legend wrapperStyle={{fontSize: 11}}/>
              <Line isAnimationActive={false} type="monotone" dataKey="P50" stroke={COLORS.p50} dot={false}
                    strokeWidth={1.5}/>
              <Line isAnimationActive={false} type="monotone" dataKey="P75" stroke={COLORS.p75} dot={false}
                    strokeWidth={1.5}/>
              <Line isAnimationActive={false} type="monotone" dataKey="P95" stroke={COLORS.p95} dot={{r: 3}}
                    strokeWidth={2}/>
            </LineChart>
          </ResponsiveContainer>
        </div>

        {timeData.length > 0 && (
            <div style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '10px 12px'
            }}>
              <div style={{
                fontSize: 10,
                color: 'var(--muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 8
              }}>Нагрузка и P95 по времени
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={timeData} margin={{top: 4, right: 36, left: 0, bottom: 0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke={grid}/>
                  <XAxis dataKey="t" stroke={axis} fontSize={10} unit="s"/>
                  <YAxis yAxisId="l" stroke={COLORS.rps} fontSize={10} unit=" rps"/>
                  <YAxis yAxisId="r" stroke={COLORS.p95} fontSize={10} unit=" ms" orientation="right"/>
                  <Tooltip contentStyle={tooltipStyle}/>
                  <Legend wrapperStyle={{fontSize: 11}}/>
                  <Line isAnimationActive={false} yAxisId="l" type="monotone" dataKey="RPS" stroke={COLORS.rps}
                        dot={false} strokeWidth={1.5}/>
                  <Line isAnimationActive={false} yAxisId="r" type="monotone" dataKey="P95" stroke={COLORS.p95}
                        dot={false} strokeWidth={1.5}/>
                </LineChart>
              </ResponsiveContainer>
            </div>
        )}
      </div>
  )
}

export function ProjectDetailPage() {
  const {projectId} = useParams<{ projectId: string }>()
  const pid = Number(projectId)
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [edges, setEdges] = useState<EdgeResult[]>([])
  const [total, setTotal] = useState(0)
  const [pageReady, setPageReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [showLoad, setShowLoad] = useState(false)
  const [loadPath, setLoadPath] = useState('')
  const [loadBusy, setLoadBusy] = useState(false)
  const [loadMsg, setLoadMsg] = useState<string | null>(null)
  const [browsing, setBrowsing] = useState(false)

  // Expanded state lives HERE — not inside EdgeRow — so it survives re-renders
  const [expandedEdge, setExpandedEdge] = useState<string | null>(null)
  const [expandedData, setExpandedData] = useState<AnalysisResult | null>(null)
  const [expandLoading, setExpandLoading] = useState(false)
  const [expandError, setExpandError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      const [proj, snaps] = await Promise.all([getProject(pid), getSnapshots(pid)])
      setProject(proj);
      setSnapshots(snaps)
      if (snaps.length > 0) {
        const page = await getEdges(pid, {page_size: 200, sort_by: 'p95_growth'})
        setEdges(page.items);
        setTotal(page.total)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setPageReady(true)
    }
  }, [pid])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleRowClick = useCallback(async (edgeName: string) => {
    // Collapse if already open
    if (expandedEdge === edgeName) {
      setExpandedEdge(null);
      setExpandedData(null);
      setExpandError(null)
      return
    }
    setExpandedEdge(edgeName)
    setExpandedData(null)
    setExpandError(null)
    setExpandLoading(true)
    try {
      setExpandedData(await getAnalysis(pid, edgeName))
    } catch (e: unknown) {
      setExpandError(e instanceof Error ? e.message : String(e))
    } finally {
      setExpandLoading(false)
    }
  }, [expandedEdge, pid])

  const handleBrowse = async () => {
    setBrowsing(true)
    try {
      const r = await browseFolder();
      if (r.path) setLoadPath(r.path)
    } catch { /* non-Windows */
    } finally {
      setBrowsing(false)
    }
  }

  const handleLoad = async () => {
    if (!loadPath.trim()) return
    setLoadBusy(true);
    setLoadMsg(null)
    try {
      const r = await loadProject(pid, loadPath.trim())
      setLoadMsg(`✓ ${r.edges} рёбер, ${r.bottlenecks} узких мест`)
      setShowLoad(false);
      setLoadPath('')
      setExpandedEdge(null);
      setExpandedData(null)
      await loadData()
    } catch (e: unknown) {
      setLoadMsg(`✗ ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setLoadBusy(false)
    }
  }

  if (!pageReady) return <div style={{padding: 40, textAlign: 'center'}}>
    <div className="spinner"/>
  </div>
  if (!project) return <div className="error-box" style={{margin: 24}}>{error ?? 'Проект не найден'}</div>

  const latest = snapshots[0]

  return (
      <main style={{maxWidth: 1200, margin: '0 auto', padding: '20px 20px', width: '100%'}}>

        {/* Header */}
        <div className="card" style={{marginBottom: 14}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
            <div>
              <div style={{fontWeight: 700, fontSize: 18, color: 'var(--text)'}}>{project.name}</div>
              {project.description &&
                  <div style={{color: 'var(--text2)', fontSize: 13, marginTop: 3}}>{project.description}</div>}
              <div style={{display: 'flex', gap: 20, marginTop: 10}}>
                {[
                  {label: 'Снапшотов', value: snapshots.length},
                  {label: 'Рёбер', value: latest?.edge_count ?? 0},
                  {label: 'Узких мест', value: latest?.bottleneck_count ?? 0},
                ].map(({label, value}) => (
                    <div key={label}>
                      <span style={{fontWeight: 700, fontSize: 16, color: 'var(--text)'}}>{value}</span>
                      <span style={{color: 'var(--muted)', fontSize: 12, marginLeft: 5}}>{label}</span>
                    </div>
                ))}
              </div>
            </div>
            <button className="btn-primary" onClick={() => setShowLoad(v => !v)}>
              <Upload size={13} style={{marginRight: 6}}/>Загрузить логи
            </button>
          </div>

          {showLoad && (
              <div style={{marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)'}}>
                <div style={{display: 'flex', gap: 8}}>
                  <input placeholder="Путь к файлу или директории" value={loadPath}
                         onChange={e => setLoadPath(e.target.value)}
                         onKeyDown={e => e.key === 'Enter' && handleLoad()}/>
                  <button className="btn-ghost" onClick={handleBrowse} disabled={browsing}
                          style={{whiteSpace: 'nowrap'}}>
                    <FolderSearch size={13} style={{marginRight: 4}}/>{browsing ? '...' : 'Обзор'}
                  </button>
                  <button className="btn-primary" onClick={handleLoad} disabled={loadBusy || !loadPath.trim()}>
                    {loadBusy ? 'Загрузка...' : 'Загрузить'}
                  </button>
                  <button className="btn-ghost" onClick={() => setShowLoad(false)}>✕</button>
                </div>
                {loadMsg && (
                    <div style={{
                      marginTop: 8,
                      fontSize: 12,
                      color: loadMsg.startsWith('✓') ? 'var(--ok)' : 'var(--critical)'
                    }}>
                      {loadMsg}
                    </div>
                )}
              </div>
          )}
        </div>

        {/* Snapshots */}
        {snapshots.length > 0 && (
            <details className="card" style={{marginBottom: 14}}>
              <summary style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text)'
              }}>
                <History size={14}/> История снапшотов ({snapshots.length})
              </summary>
              <div style={{marginTop: 10}}>
                {snapshots.map(s => (
                    <div key={s.id} style={{
                      display: 'flex',
                      gap: 16,
                      fontSize: 12,
                      padding: '5px 0',
                      borderBottom: '1px solid var(--border)',
                      color: 'var(--text2)'
                    }}>
                      <span style={{color: 'var(--muted)'}}>#{s.id}</span>
                      <span>{new Date(s.created_at).toLocaleString('ru')}</span>
                      <span style={{color: 'var(--text)'}}>{s.edge_count} рёбер</span>
                      <span style={{color: s.bottleneck_count > 0 ? 'var(--critical)' : 'var(--ok)'}}>
                  {s.bottleneck_count} узких мест
                </span>
                    </div>
                ))}
              </div>
            </details>
        )}

        {/* Edge table */}
        {edges.length === 0 ? (
            <div className="card" style={{textAlign: 'center', padding: 40, color: 'var(--muted)'}}>
              {snapshots.length === 0 ? 'Загрузите логи для начала анализа' : 'Нет рёбер'}
            </div>
        ) : (
            <div className="card" style={{padding: 0, overflow: 'hidden'}}>
              <div style={{
                padding: '10px 14px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span style={{fontWeight: 600, fontSize: 13, color: 'var(--text)'}}>Рёбра</span>
                <span style={{fontSize: 11, color: 'var(--muted)'}}>Всего: {total} · показаны {edges.length}</span>
              </div>
              <table style={{width: '100%', borderCollapse: 'collapse', fontSize: 12}}>
                <thead>
                <tr style={{
                  background: 'var(--surface2)',
                  fontSize: 10,
                  textTransform: 'uppercase' as const,
                  letterSpacing: '0.05em'
                }}>
                  {['Ребро', 'RPC', 'Записей', 'Severity', 'P95 рост', 'Onset RPS', ''].map(h => (
                      <th key={h} style={{
                        padding: '7px 12px',
                        textAlign: 'left',
                        fontWeight: 500,
                        color: 'var(--muted)'
                      }}>{h}</th>
                  ))}
                </tr>
                </thead>
                <tbody>
                {edges.map(edge => {
                  const isExpanded = expandedEdge === edge.name
                  return (
                      <React.Fragment key={edge.name}>
                        <tr
                            onClick={e => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleRowClick(edge.name)
                            }}
                            style={{
                              borderBottom: isExpanded ? 'none' : '1px solid var(--border)',
                              cursor: 'pointer', transition: 'background .1s',
                              background: isExpanded ? 'var(--surface2)' : 'transparent',
                            }}
                            onMouseEnter={e => {
                              if (!isExpanded) e.currentTarget.style.background = 'var(--surface2)'
                            }}
                            onMouseLeave={e => {
                              if (!isExpanded) e.currentTarget.style.background = 'transparent'
                            }}
                        >
                          <td style={{
                            padding: '9px 12px',
                            fontFamily: 'monospace',
                            color: 'var(--text)',
                            fontSize: 12
                          }}>
                            <SeverityDot s={edge.severity}/>{edge.source} → {edge.destination}
                          </td>
                          <td style={{padding: '9px 12px'}}><span className="rpc-tag">{edge.rpc_type}</span></td>
                          <td style={{
                            padding: '9px 12px',
                            color: 'var(--text2)'
                          }}>{edge.records_amount.toLocaleString()}</td>
                          <td style={{padding: '9px 12px'}}>
                            <span className={`badge badge-${edge.severity}`}>{edge.severity}</span>
                          </td>
                          <td style={{padding: '9px 12px', fontWeight: 600, color: growthColor(edge.p95_growth)}}>
                            {edge.p95_growth > 0 ? `×${edge.p95_growth.toFixed(2)}` : '—'}
                          </td>
                          <td style={{padding: '9px 12px', color: 'var(--text2)'}}>
                            {edge.onset_rps ? edge.onset_rps.toFixed(1) : '—'}
                          </td>
                          <td style={{padding: '9px 12px', textAlign: 'right'}}>
                            {isExpanded ? <ChevronUp size={14} color="var(--muted)"/> :
                                <ChevronDown size={14} color="var(--muted)"/>}
                          </td>
                        </tr>

                        {isExpanded && (
                            <tr key={`${edge.name}-detail`}>
                              <td colSpan={7} style={{borderBottom: '1px solid var(--border)', padding: 0}}>
                                {expandLoading && (
                                    <div style={{padding: 32, textAlign: 'center'}}>
                                      <div className="spinner"/>
                                    </div>
                                )}
                                {expandError && (
                                    <div style={{padding: 12}}>
                                      <div className="error-box">
                                        <div style={{fontWeight: 600, marginBottom: 4}}>{expandError}</div>
                                        <div style={{fontSize: 11, opacity: 0.8}}>
                                          Удалите <code>bottleneck.db</code> и загрузите логи заново.
                                        </div>
                                      </div>
                                    </div>
                                )}
                                {expandedData && (
                                    <>
                                      <InlineCharts analysis={expandedData}/>
                                      <div style={{
                                        padding: '8px 16px 14px',
                                        display: 'flex',
                                        justifyContent: 'flex-end'
                                      }}>
                                        <button
                                            className="btn-ghost"
                                            onClick={e => {
                                              e.stopPropagation();
                                              navigate(`/projects/${pid}/analyse/${encodeURIComponent(edge.name).replace(/%2F/g, "/")}`)
                                            }}
                                            style={{display: 'flex', alignItems: 'center', gap: 6, fontSize: 12}}
                                        >
                                          <ExternalLink size={13}/> Подробнее — все графики
                                        </button>
                                      </div>
                                    </>
                                )}
                              </td>
                            </tr>
                        )}
                      </React.Fragment>
                  )
                })}
                </tbody>
              </table>
            </div>
        )}
      </main>
  )
}
