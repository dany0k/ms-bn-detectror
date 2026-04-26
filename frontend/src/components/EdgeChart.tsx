import {CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,} from 'recharts'
import type {AnalysisResult} from '../api/types'

interface Props {
    analysis: AnalysisResult
}

const COLORS = {p50: '#27b07a', p75: '#d4900a', p95: '#d63c3c', rps: '#3557E8'}

const tooltipStyle = {
    backgroundColor: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    fontSize: 11,
    color: 'var(--text)',
}
const GRID = 'var(--chart-grid)'
const AXIS = 'var(--chart-axis)'

export function EdgeChart({analysis}: Props) {
    const binData = analysis.rps_bins.map(b => ({
        rps: Math.round(b.rps_center * 10) / 10,
        P50: Math.round(b.p50_ms),
        P75: Math.round(b.p75_ms),
        P95: Math.round(b.p95_ms),
    }))

    const timeData = analysis.per_second.slice(0, 300).map(s => ({
        t: s.second,
        RPS: Math.round(s.rps * 10) / 10,
        P95: Math.round(s.p95_ms),
    }))

    return (
        <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>

            {/* P95 by RPS bins */}
            <div className="card">
                <div style={{
                    marginBottom: 10,
                    color: 'var(--muted)',
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em'
                }}>
                    P95 задержки по RPS-группам
                </div>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={binData} margin={{top: 4, right: 10, left: 0, bottom: 0}}>
                        <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
                        <XAxis dataKey="rps" stroke={AXIS} fontSize={10} unit=" rps"/>
                        <YAxis stroke={AXIS} fontSize={10} unit=" ms"/>
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

            {/* RPS + P95 over time */}
            {timeData.length > 0 && (
                <div className="card">
                    <div style={{
                        marginBottom: 10,
                        color: 'var(--muted)',
                        fontSize: 10,
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em'
                    }}>
                        Нагрузка и P95 по времени
                    </div>
                    <ResponsiveContainer width="100%" height={190}>
                        <LineChart data={timeData} margin={{top: 4, right: 36, left: 0, bottom: 0}}>
                            <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
                            <XAxis dataKey="t" stroke={AXIS} fontSize={10} unit="s"/>
                            <YAxis yAxisId="left" stroke={COLORS.rps} fontSize={10} unit=" rps"/>
                            <YAxis yAxisId="right" stroke={COLORS.p95} fontSize={10} unit=" ms" orientation="right"/>
                            <Tooltip contentStyle={tooltipStyle}/>
                            <Legend wrapperStyle={{fontSize: 11}}/>
                            <Line yAxisId="left" isAnimationActive={false} type="monotone" dataKey="RPS"
                                  stroke={COLORS.rps} dot={false} strokeWidth={1.5}/>
                            <Line yAxisId="right" isAnimationActive={false} type="monotone" dataKey="P95"
                                  stroke={COLORS.p95} dot={false} strokeWidth={1.5}/>
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Global stats */}
            <div className="card" style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12}}>
                {[
                    {label: 'Всего записей', value: analysis.total_records.toLocaleString()},
                    {label: 'P50 глобал.', value: `${Math.round(analysis.global_p50_ms)} ms`},
                    {label: 'P95 глобал.', value: `${Math.round(analysis.global_p95_ms)} ms`},
                    {label: 'Min', value: `${Math.round(analysis.global_min_ms)} ms`},
                    {label: 'Max', value: `${Math.round(analysis.global_max_ms)} ms`},
                    {label: 'RPS-бинов', value: analysis.rps_bins.length},
                ].map(({label, value}) => (
                    <div key={label} style={{textAlign: 'center'}}>
                        <div style={{fontSize: 17, fontWeight: 700, color: 'var(--text)'}}>{value}</div>
                        <div style={{fontSize: 10, color: 'var(--muted)', marginTop: 2}}>{label}</div>
                    </div>
                ))}
            </div>
        </div>
    )
}
