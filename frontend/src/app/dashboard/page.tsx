'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiListPolicies, apiListPortfolios } from '@/lib/api'
import { formatINR } from '@/lib/utils'
import { Shield, Briefcase, TrendingUp, AlertTriangle, ArrowRight, Activity, CheckCircle, Clock } from 'lucide-react'
import Link from 'next/link'

// SVG mini bar chart — no external dependency needed
function MiniBarChart({ data, color = '#3b82f6' }: { data: number[], color?: string }) {
    if (!data || data.length === 0) return null
    const max = Math.max(...data, 1)
    const w = 100 / data.length
    return (
        <svg viewBox="0 0 100 40" className="w-full h-10" preserveAspectRatio="none">
            {data.map((v, i) => {
                const h = (v / max) * 36
                return (
                    <rect
                        key={i}
                        x={i * w + 1}
                        y={40 - h}
                        width={w - 2}
                        height={h}
                        rx="2"
                        fill={color}
                        opacity={0.7 + (i / data.length) * 0.3}
                    />
                )
            })}
        </svg>
    )
}

// SVG donut chart for portfolio/policy breakdown
function DonutChart({ segments, size = 80 }: { segments: { value: number, color: string, label: string }[], size?: number }) {
    const total = segments.reduce((a, s) => a + s.value, 0)
    if (total === 0) return (
        <svg viewBox="0 0 80 80" width={size} height={size}>
            <circle cx="40" cy="40" r="30" fill="none" stroke="#27272a" strokeWidth="14" />
        </svg>
    )
    const r = 30
    const cx = 40, cy = 40
    const circumference = 2 * Math.PI * r
    let cumulative = 0
    return (
        <svg viewBox="0 0 80 80" width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="#27272a" strokeWidth="14" />
            {segments.map((seg, i) => {
                const pct = seg.value / total
                const dash = pct * circumference
                const gap = circumference - dash
                const offset = -cumulative * circumference
                cumulative += pct
                return (
                    <circle
                        key={i}
                        cx={cx} cy={cy} r={r}
                        fill="none"
                        stroke={seg.color}
                        strokeWidth="14"
                        strokeDasharray={`${dash} ${gap}`}
                        strokeDashoffset={offset}
                    />
                )
            })}
        </svg>
    )
}

// Coverage timeline mini chart
function CoverageTimeline({ policies }: { policies: any[] }) {
    if (policies.length === 0) return <div className="text-sm text-muted-foreground text-center py-4">No active policies</div>
    const sorted = [...policies].sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    const earliest = new Date(sorted[0].start_date).getTime()
    const latest = sorted.reduce((max, p) => Math.max(max, new Date(p.end_date).getTime()), 0)
    const range = latest - earliest || 1
    const termColors: Record<string, string> = { INTRADAY: '#f59e0b', WEEKLY: '#3b82f6', MONTHLY: '#10b981' }

    return (
        <div className="space-y-2 mt-2">
            {sorted.map((p, i) => {
                const start = (new Date(p.start_date).getTime() - earliest) / range * 100
                const width = Math.max(4, (new Date(p.end_date).getTime() - new Date(p.start_date).getTime()) / range * 100)
                return (
                    <div key={p.id} className="flex items-center gap-3 text-xs">
                        <span className="text-muted-foreground w-16 shrink-0 truncate" title={p.term}>{p.term}</span>
                        <div className="flex-1 relative h-3 bg-secondary rounded-full overflow-hidden">
                            <div
                                className="absolute h-full rounded-full"
                                style={{
                                    left: `${start}%`,
                                    width: `${width}%`,
                                    backgroundColor: termColors[p.term] || '#6366f1',
                                    opacity: p.status === 'ACTIVE' ? 1 : 0.4
                                }}
                            />
                        </div>
                        <span className={`w-14 text-right ${p.status === 'ACTIVE' ? 'text-blue-500' : 'text-zinc-500'}`}>{formatINR(p.notional_inr)}</span>
                    </div>
                )
            })}
        </div>
    )
}

const STAT_CARDS = (stats: any, user: any) => [
    {
        label: 'Active Coverage',
        value: formatINR(stats.totalNotional),
        sub: `${stats.activePolicies} active ${stats.activePolicies === 1 ? 'policy' : 'policies'}`,
        icon: <Shield className="h-5 w-5 text-blue-500" />,
        color: 'text-blue-500',
        bg: 'from-blue-500/10 to-transparent',
    },
    {
        label: 'Total Premiums Paid',
        value: formatINR(stats.totalPremium),
        sub: 'Lifetime total',
        icon: <TrendingUp className="h-5 w-5 text-emerald-500" />,
        color: 'text-emerald-500',
        bg: 'from-emerald-500/10 to-transparent',
    },
    {
        label: 'Portfolios',
        value: stats.totalPortfolios,
        sub: `${stats.activePortfolios} active`,
        icon: <Briefcase className="h-5 w-5 text-violet-500" />,
        color: 'text-violet-500',
        bg: 'from-violet-500/10 to-transparent',
    },
    {
        label: 'Risk Tier',
        value: user?.tier?.replace(/_/g, ' ') ?? '—',
        sub: 'Underwriting class',
        icon: <AlertTriangle className="h-5 w-5 text-amber-500" />,
        color: 'text-amber-500',
        bg: 'from-amber-500/10 to-transparent',
    },
]

export default function Dashboard() {
    const { user, loading, activeOrgId } = useAuth()
    const [policies, setPolicies] = useState<any[]>([])
    const [portfolios, setPortfolios] = useState<any[]>([])
    const [stats, setStats] = useState({ totalNotional: 0, activePolicies: 0, activePortfolios: 0, totalPortfolios: 0, totalPremium: 0 })
    const [fetching, setFetching] = useState(true)

    useEffect(() => {
        if (!user) return
        setFetching(true)
        Promise.all([
            apiListPolicies(activeOrgId || undefined),
            apiListPortfolios(activeOrgId || undefined)
        ]).then(([pols, ports]) => {
            setPolicies(pols)
            setPortfolios(ports)
            const active = pols.filter((p: any) => p.status === 'ACTIVE')
            setStats({
                activePolicies: active.length,
                totalNotional: active.reduce((acc: number, p: any) => acc + p.notional_inr, 0),
                totalPremium: pols.reduce((acc: number, p: any) => acc + p.premium_inr, 0),
                totalPortfolios: ports.length,
                activePortfolios: ports.filter((p: any) => p.status !== 'ARCHIVED').length,
            })
        }).finally(() => setFetching(false))
    }, [user, activeOrgId])

    if (loading || !user) return null

    const activePolicies = policies.filter(p => p.status === 'ACTIVE')
    const settledPolicies = policies.filter(p => p.status === 'SETTLED')

    // Donut segments
    const termCounts = { INTRADAY: 0, WEEKLY: 0, MONTHLY: 0 }
    activePolicies.forEach(p => { if (p.term in termCounts) (termCounts as any)[p.term]++ })
    const donutSegs = [
        { value: termCounts.INTRADAY, color: '#f59e0b', label: 'Intraday' },
        { value: termCounts.WEEKLY, color: '#3b82f6', label: 'Weekly' },
        { value: termCounts.MONTHLY, color: '#10b981', label: 'Monthly' },
    ]

    // Mini bar chart: notional per policy (last 6)
    const barData = policies.slice(-6).map(p => p.notional_inr / 100000)

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <header className="mb-8 flex justify-between items-end">
                    <div>
                        <div className="text-xs font-semibold uppercase tracking-widest text-primary mb-1">PMRI Platform</div>
                        <h1 className="text-3xl font-bold tracking-tight mb-1">
                            {activeOrgId ? 'Organisation Dashboard' : `Welcome, ${user.email?.split('@')[0] ?? 'User'}`}
                        </h1>
                        <p className="text-muted-foreground text-sm">Your market risk coverage overview — {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
                    </div>
                    <div className="flex gap-3">
                        <Link href="/portfolios/new" className="btn-secondary flex items-center gap-2">
                            <Briefcase className="h-4 w-4" />
                            New Portfolio
                        </Link>
                        <Link href="/quotes/new" className="btn-primary flex items-center gap-2">
                            <Shield className="h-4 w-4" />
                            Get Coverage
                        </Link>
                    </div>
                </header>

                {fetching ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-pulse">
                        {[...Array(4)].map((_, i) => <div key={i} className="h-32 bg-secondary rounded-xl" />)}
                    </div>
                ) : (
                    <>
                        {/* Stat Cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                            {STAT_CARDS(stats, user).map((card, i) => (
                                <div key={i} className="card p-6 overflow-hidden relative">
                                    <div className={`absolute inset-0 bg-gradient-to-br ${card.bg} opacity-60 pointer-events-none`} />
                                    <div className="flex items-center justify-between mb-3 relative z-10">
                                        <h3 className="text-sm font-medium text-muted-foreground">{card.label}</h3>
                                        {card.icon}
                                    </div>
                                    <div className={`text-2xl font-bold ${card.color} relative z-10`}>{card.value}</div>
                                    <p className="text-xs text-muted-foreground mt-1 relative z-10">{card.sub}</p>
                                </div>
                            ))}
                        </div>

                        {/* Charts Row */}
                        <div className="grid lg:grid-cols-3 gap-6 mb-6">
                            {/* Coverage Timeline */}
                            <div className="card p-6 lg:col-span-2">
                                <div className="flex justify-between items-center mb-4">
                                    <div>
                                        <h2 className="text-base font-semibold">Coverage Timeline</h2>
                                        <p className="text-xs text-muted-foreground mt-0.5">All your policies across time</p>
                                    </div>
                                    <Activity className="h-4 w-4 text-muted-foreground" />
                                </div>
                                <CoverageTimeline policies={policies} />
                                {policies.length === 0 && (
                                    <div className="flex flex-col items-center py-6 gap-3">
                                        <Shield className="h-10 w-10 text-muted-foreground/40" />
                                        <p className="text-sm text-muted-foreground">No policies yet</p>
                                        <Link href="/quotes/new" className="btn-primary text-xs py-1.5 px-3">Get Your First Quote</Link>
                                    </div>
                                )}
                            </div>

                            {/* Policy Mix Donut */}
                            <div className="card p-6 flex flex-col">
                                <div className="flex justify-between items-center mb-4">
                                    <div>
                                        <h2 className="text-base font-semibold">Policy Mix</h2>
                                        <p className="text-xs text-muted-foreground mt-0.5">By protection term</p>
                                    </div>
                                </div>
                                <div className="flex flex-1 items-center justify-between gap-4 mt-2">
                                    <DonutChart segments={donutSegs} size={90} />
                                    <div className="space-y-2 flex-1">
                                        {donutSegs.map(s => (
                                            <div key={s.label} className="flex items-center gap-2 text-xs">
                                                <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: s.color }} />
                                                <span className="text-muted-foreground">{s.label}</span>
                                                <span className="ml-auto font-mono font-semibold">{s.value}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                {barData.length > 0 && (
                                    <div className="mt-4 pt-4 border-t border-border">
                                        <p className="text-xs text-muted-foreground mb-2">Notional (₹L) — last {barData.length} policies</p>
                                        <MiniBarChart data={barData} color="#3b82f6" />
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Tables Row */}
                        <div className="grid lg:grid-cols-2 gap-6">
                            {/* Policies */}
                            <div className="card overflow-hidden">
                                <div className="p-5 border-b border-border flex justify-between items-center">
                                    <h2 className="text-base font-semibold">Active Policies</h2>
                                    <Link href="/policies" className="text-xs text-primary hover:underline flex items-center gap-1">All <ArrowRight className="h-3 w-3" /></Link>
                                </div>
                                {activePolicies.length === 0 ? (
                                    <div className="p-8 text-center">
                                        <Shield className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
                                        <p className="text-sm text-muted-foreground mb-4">No active policies.</p>
                                        <Link href="/quotes/new" className="btn-primary text-xs py-1.5 px-3">Get Coverage</Link>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-border">
                                        {activePolicies.slice(0, 5).map(p => (
                                            <Link href={`/policies/${p.id}`} key={p.id} className="flex items-center px-5 py-3.5 hover:bg-secondary/50 transition-colors gap-4">
                                                <span className="h-8 w-8 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
                                                    <Shield className="h-4 w-4 text-blue-500" />
                                                </span>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium truncate">{formatINR(p.notional_inr)} Coverage</p>
                                                    <p className="text-xs text-muted-foreground">{p.term} • Expires {new Date(p.end_date).toLocaleDateString('en-IN')}</p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-semibold font-mono text-emerald-500">{formatINR(p.premium_inr)}</span>
                                                    <span className="text-xs bg-blue-500/10 text-blue-500 border border-blue-500/20 px-2 py-0.5 rounded-full">ACTIVE</span>
                                                </div>
                                            </Link>
                                        ))}
                                    </div>
                                )}
                                {settledPolicies.length > 0 && (
                                    <div className="px-5 py-3 border-t border-border bg-secondary/20">
                                        <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                            <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                                            {settledPolicies.length} settled {settledPolicies.length === 1 ? 'policy' : 'policies'} in history
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Portfolios */}
                            <div className="card overflow-hidden">
                                <div className="p-5 border-b border-border flex justify-between items-center">
                                    <h2 className="text-base font-semibold">Your Portfolios</h2>
                                    <Link href="/portfolios" className="text-xs text-primary hover:underline flex items-center gap-1">Manage <ArrowRight className="h-3 w-3" /></Link>
                                </div>
                                {portfolios.length === 0 ? (
                                    <div className="p-8 text-center">
                                        <Briefcase className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
                                        <p className="text-sm text-muted-foreground mb-4">No portfolios yet.</p>
                                        <Link href="/portfolios/new" className="btn-primary text-xs py-1.5 px-3">Upload CSV</Link>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-border">
                                        {portfolios.slice(0, 5).map(pt => {
                                            const isArchived = pt.status === 'ARCHIVED'
                                            const holdCount = pt.holdings?.length || 0
                                            const barVals = pt.holdings?.slice(0, 6).map((h: any) => h.quantity) || []
                                            return (
                                                <Link href={`/portfolios/${pt.id}`} key={pt.id} className={`flex items-center px-5 py-3.5 hover:bg-secondary/50 transition-colors gap-4 ${isArchived ? 'opacity-50' : ''}`}>
                                                    <span className="h-8 w-8 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
                                                        <Briefcase className="h-4 w-4 text-violet-500" />
                                                    </span>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-medium flex items-center gap-2">
                                                            {pt.name}
                                                            {isArchived && <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">ARCHIVED</span>}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">{holdCount} {holdCount === 1 ? 'holding' : 'holdings'}</p>
                                                    </div>
                                                    <div className="w-16 hidden sm:block">
                                                        <MiniBarChart data={barVals} color="#8b5cf6" />
                                                    </div>
                                                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                                                </Link>
                                            )
                                        })}
                                    </div>
                                )}
                                <div className="px-5 py-3 border-t border-border bg-secondary/20">
                                    <Link href="/portfolios/new" className="text-xs text-primary hover:underline flex items-center gap-1">
                                        <Briefcase className="h-3.5 w-3.5" /> Upload new portfolio via CSV
                                    </Link>
                                </div>
                            </div>
                        </div>

                        {/* Quick Actions */}
                        <div className="mt-6 card p-5">
                            <h2 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-widest">Quick Actions</h2>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                {[
                                    { href: '/portfolios/new', label: 'Upload Portfolio', icon: <Briefcase className="h-5 w-5" />, color: 'text-violet-400' },
                                    { href: '/quotes/new', label: 'Get Quote', icon: <Shield className="h-5 w-5" />, color: 'text-blue-400' },
                                    { href: '/policies', label: 'View Policies', icon: <CheckCircle className="h-5 w-5" />, color: 'text-emerald-400' },
                                    { href: '/portfolios', label: 'Manage Portfolios', icon: <Clock className="h-5 w-5" />, color: 'text-amber-400' },
                                ].map(a => (
                                    <Link key={a.href} href={a.href} className="flex flex-col items-center gap-2 p-4 rounded-lg border border-border hover:bg-secondary/60 transition-all text-center group">
                                        <span className={`${a.color} group-hover:scale-110 transition-transform`}>{a.icon}</span>
                                        <span className="text-xs font-medium">{a.label}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </>
    )
}
