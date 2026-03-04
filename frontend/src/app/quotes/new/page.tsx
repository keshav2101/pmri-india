'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiListPortfolios, apiCreateQuote } from '@/lib/api'
import { Shield } from 'lucide-react'

function QuoteForm() {
    const { user, activeOrgId } = useAuth()
    const router = useRouter()
    const searchParams = useSearchParams()
    const initPortfolioId = searchParams.get('portfolio') || ''

    const [portfolios, setPortfolios] = useState<any[]>([])
    const [selectedPortfolio, setSelectedPortfolio] = useState(initPortfolioId)
    const [term, setTerm] = useState('WEEKLY')
    const [notional, setNotional] = useState(500000)

    const [loading, setLoading] = useState(true)
    const [quoting, setQuoting] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        apiListPortfolios(activeOrgId || undefined).then(pts => {
            setPortfolios(pts)
            if (!selectedPortfolio && pts.length > 0) {
                setSelectedPortfolio(pts[0].id)
            }
        }).finally(() => setLoading(false))
    }, [activeOrgId])

    const handleQuote = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!selectedPortfolio) return setError('Please select a portfolio')

        setError('')
        setQuoting(true)
        try {
            const q = await apiCreateQuote({
                portfolio_id: selectedPortfolio,
                term,
                notional_inr: Number(notional),
                org_id: activeOrgId || undefined
            })
            router.push(`/quotes/${q.id}`)
        } catch (err: any) {
            setError(err.message)
            setQuoting(false) // Let user try again if fails
        }
    }

    if (loading) return null

    return (
        <div className="card p-8 bg-secondary/20">
            <form onSubmit={handleQuote} className="space-y-6">
                {error && <div className="text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20">{error}</div>}

                <div>
                    <label className="block text-sm font-medium mb-1">Select Portfolio</label>
                    <select
                        required
                        className="input-field cursor-pointer"
                        value={selectedPortfolio}
                        onChange={e => setSelectedPortfolio(e.target.value)}
                    >
                        <option value="" disabled>-- Select a portfolio --</option>
                        {portfolios.map(p => (
                            <option key={p.id} value={p.id}>{p.name} ({p.holdings.length} items)</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-1">Protection Term</label>
                    <select
                        required
                        className="input-field cursor-pointer"
                        value={term}
                        onChange={e => setTerm(e.target.value)}
                    >
                        <option value="INTRADAY">Intraday (Same Day)</option>
                        <option value="WEEKLY">Weekly (Ends Friday)</option>
                        <option value="MONTHLY">Monthly (Ends Month-end)</option>
                    </select>
                    <p className="text-xs text-muted-foreground mt-1">Shorter terms generally have lower premiums.</p>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">Insured Notional (₹)</label>
                    <div className="flex items-center gap-3 mb-2">
                        <input
                            type="number"
                            min="10000"
                            max={user?.tier.startsWith('INSTITUTIONAL') ? 50000000 : 2500000}
                            step="1000"
                            className="input-field w-48 font-mono text-primary font-semibold"
                            value={notional}
                            onChange={e => {
                                const max = user?.tier.startsWith('INSTITUTIONAL') ? 50000000 : 2500000
                                const v = Math.min(Math.max(Number(e.target.value) || 10000, 10000), max)
                                setNotional(v)
                            }}
                        />
                        <span className="text-sm text-muted-foreground">
                            = ₹{Number(notional).toLocaleString('en-IN')}
                        </span>
                    </div>
                    <input
                        type="range"
                        min="10000" max={user?.tier.startsWith('INSTITUTIONAL') ? 50000000 : 2500000} step="10000"
                        className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer mb-1 accent-primary"
                        value={notional}
                        onChange={e => setNotional(Number(e.target.value))}
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Min: ₹10K</span>
                        <span>Max: {user?.tier.startsWith('INSTITUTIONAL') ? '₹5Cr' : '₹25L'}</span>
                    </div>
                </div>

                <button type="submit" disabled={quoting} className="btn-primary w-full py-3 flex items-center justify-center gap-2">
                    {quoting ? 'Running ML Pricing...' : <><Shield className="h-4 w-4" /> Get Quote</>}
                </button>
            </form>
        </div>
    )
}

export default function NewQuote() {
    const { user } = useAuth()
    if (!user) return null

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-12 max-w-2xl">
                <div className="text-center mb-10">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Request Insurance Quote</h1>
                    <p className="text-muted-foreground">Our AI engine will analyze your portfolio components, correlate risk across NSE and NASDAQ sectors, and instantly price downside protection.</p>
                </div>
                <Suspense fallback={<div className="h-64 bg-secondary/20 animate-pulse rounded-xl" />}>
                    <QuoteForm />
                </Suspense>
            </div>
        </>
    )
}
