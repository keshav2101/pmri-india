'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiGetPolicy, apiListLedger } from '@/lib/api'
import { formatINR, formatDate } from '@/lib/utils'
import { ArrowLeft, Clock, CheckCircle, AlertTriangle, FileText, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function PolicyDetail() {
    const { user } = useAuth()
    const { id } = useParams()
    const router = useRouter()
    const [policy, setPolicy] = useState<any>(null)
    const [ledger, setLedger] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        if (!id) return
        Promise.all([
            apiGetPolicy(id as string),
            apiListLedger(id as string)
        ])
            .then(([pol, leg]) => {
                setPolicy(pol)
                setLedger(leg)
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [id])

    if (loading) return null

    if (error) {
        return (
            <>
                <Navbar />
                <div className="container mx-auto px-4 py-8 text-center text-red-500">{error}</div>
            </>
        )
    }

    const getStatusBorder = (status: string) => {
        if (status === 'ACTIVE') return 'border-blue-500/50'
        if (status === 'SETTLED') return 'border-green-500/50'
        return 'border-border'
    }

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                <div className="mb-6">
                    <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
                        <ArrowLeft className="h-4 w-4" /> Back
                    </button>
                </div>

                <div className="flex flex-col md:flex-row gap-6">
                    <div className="flex-1 space-y-6">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <h1 className="text-3xl font-bold tracking-tight">Policy Overview</h1>
                                <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${policy.status === 'ACTIVE' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20' :
                                        policy.status === 'SETTLED' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                                            'bg-zinc-800 text-zinc-400 border-zinc-700'
                                    }`}>
                                    {policy.status}
                                </span>
                            </div>
                            <p className="text-muted-foreground mt-1 font-mono text-sm">
                                ID: {policy.id.split('-')[0]}...
                            </p>
                        </div>

                        <div className={`card p-6 border-l-4 ${getStatusBorder(policy.status)}`}>
                            <h2 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wider flex items-center gap-2">
                                <FileText className="h-4 w-4" /> Contract Terms
                            </h2>
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Insured Notional</p>
                                    <p className="font-bold text-lg">{formatINR(policy.notional_inr)}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Premium Paid</p>
                                    <p className="font-medium text-lg text-primary">{formatINR(policy.premium_inr)}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Start Date</p>
                                    <p className="font-medium text-sm">{formatDate(policy.start_date)}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">End Date</p>
                                    <p className="font-medium text-sm text-amber-500">{formatDate(policy.end_date)}</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-6 mt-6 pt-6 border-t border-border">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Loss Threshold (Payout triggers below)</p>
                                    <p className="font-bold text-red-500 text-xl">{(policy.loss_threshold * 100).toFixed(1)}%</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Profit Threshold (Rebate triggers above)</p>
                                    <p className="font-bold text-green-500 text-xl">+{(policy.profit_threshold * 100).toFixed(1)}%</p>
                                </div>
                            </div>
                        </div>

                        {policy.settlement && (
                            <div className="card p-6 border border-green-500/30 bg-green-500/5">
                                <h2 className="text-sm font-semibold text-green-500 mb-4 uppercase tracking-wider flex items-center gap-2">
                                    <CheckCircle className="h-4 w-4" /> Settlement Result
                                </h2>
                                <div className="grid grid-cols-2 gap-6">
                                    <div>
                                        <p className="text-xs text-green-500/70 mb-1">Portfolio Return</p>
                                        <p className="font-mono text-xl font-bold">{(policy.settlement.portfolio_return_pct * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-green-500/70 mb-1">Outcome Triggered</p>
                                        <p className="font-medium text-lg capitalize">{policy.settlement.outcome.replace('_', ' ')}</p>
                                    </div>
                                    {policy.settlement.payout_inr > 0 && (
                                        <div className="col-span-2 mt-2 pt-4 border-t border-green-500/20">
                                            <p className="text-xs text-green-500/70 mb-1">Insurance Payout</p>
                                            <p className="font-bold text-2xl text-green-400">{formatINR(policy.settlement.payout_inr)}</p>
                                        </div>
                                    )}
                                    {policy.settlement.surplus_inr > 0 && (
                                        <div className="col-span-2 mt-2 pt-4 border-t border-green-500/20">
                                            <p className="text-xs text-green-500/70 mb-1">Premium Rebate (Surplus Share)</p>
                                            <p className="font-bold text-2xl text-green-400">{formatINR(policy.settlement.surplus_inr)}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="w-full md:w-80 space-y-6">
                        <div className="card p-6">
                            <h2 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Ledger History</h2>

                            {ledger.length === 0 ? (
                                <p className="text-xs text-muted-foreground">No transactions found.</p>
                            ) : (
                                <div className="space-y-4 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
                                    {ledger.map(tx => (
                                        <div key={tx.id} className="relative flex items-center justify-between gap-4">
                                            <div>
                                                <div className={`flex items-center gap-2 text-xs font-semibold ${tx.amount_inr > 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                    {tx.amount_inr > 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                                                    {tx.tx_type.replace('_', ' ')}
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-0.5" title={tx.description}>{tx.description.substring(0, 40)}...</p>
                                                <p className="text-[10px] text-zinc-500 mt-1">{formatDate(tx.created_at)}</p>
                                            </div>
                                            <div className={`font-mono text-sm font-medium ${tx.amount_inr > 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                {formatINR(Math.abs(tx.amount_inr))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="card p-6 bg-secondary/30">
                            <h2 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Initial Snapshot</h2>
                            <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                {Object.entries(policy.portfolio_snapshot).map(([sym, data]: [string, any]) => (
                                    <div key={sym} className="flex justify-between text-xs">
                                        <span className="font-medium">{sym.split('.')[0]}</span>
                                        <span className="text-muted-foreground">{data.qty} @ {data.price.toFixed(2)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}
