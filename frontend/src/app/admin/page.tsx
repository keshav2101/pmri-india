'use client'

import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiRunSettlements } from '@/lib/api'
import { Play, Settings2, ShieldAlert, CheckCircle2 } from 'lucide-react'

export default function AdminDashboard() {
    const { user } = useAuth()
    const [running, setRunning] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [error, setError] = useState('')

    if (!user || !user.is_admin) {
        return (
            <>
                <Navbar />
                <div className="container mx-auto px-4 py-16 text-center">
                    <ShieldAlert className="h-16 w-16 text-red-500 mx-auto mb-4" />
                    <h1 className="text-2xl font-bold">Access Denied</h1>
                    <p className="text-muted-foreground mt-2">You need administrator privileges to view this area.</p>
                </div>
            </>
        )
    }

    const handleRunSettlements = async () => {
        setRunning(true)
        setError('')
        setResult(null)
        try {
            const res = await apiRunSettlements() // Run for all terms
            setResult(res)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setRunning(false)
        }
    }

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-8 max-w-5xl">
                <header className="mb-8">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Admin Control Center</h1>
                    <p className="text-muted-foreground">Manage global risk parameters and system cron jobs.</p>
                </header>

                <div className="grid md:grid-cols-2 gap-8">
                    <div className="card p-6">
                        <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-border pb-4 mb-4">
                            <Play className="h-5 w-5 text-primary" /> System Settlement Engine
                        </h2>
                        <p className="text-sm text-muted-foreground mb-6">
                            Manually trigger the maturity evaluation cycle. This checks all ACTIVE policies to see if their end date has passed, fetches closing prices, calculates payoffs, updates the ledger, and marks them SETTLED.
                        </p>

                        <button
                            onClick={handleRunSettlements}
                            disabled={running}
                            className="btn-primary w-full shadow-lg"
                        >
                            {running ? 'Processing Settlements...' : 'Trigger Global Settlements'}
                        </button>

                        {error && <div className="mt-4 text-red-500 text-sm bg-red-500/10 p-3 rounded-md">{error}</div>}

                        {result && (
                            <div className="mt-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                                <h3 className="text-sm font-semibold text-green-500 mb-2 flex items-center gap-1">
                                    <CheckCircle2 className="h-4 w-4" /> Job Complete
                                </h3>
                                <ul className="text-xs space-y-1 text-green-400/80">
                                    <li>Policies Evaluated: {result.policies_checked}</li>
                                    <li>Policies Settled: {result.policies_settled}</li>
                                    <li>Errors Encountered: {result.errors}</li>
                                </ul>
                                {result.details.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-green-500/20 max-h-32 overflow-y-auto text-[10px] space-y-1 font-mono text-green-400/50">
                                        {result.details.map((d: any, i: number) => (
                                            <div key={i}>{d.policy_id.split('-')[0]}: {d.outcome || d.error}</div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="card p-6 bg-secondary/20">
                        <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-border pb-4 mb-4">
                            <Settings2 className="h-5 w-5 text-muted-foreground" /> Tier Margins & Limits
                        </h2>
                        <p className="text-sm text-muted-foreground mb-6">
                            Risk margins are evaluated dynamically during quoting via the Rules router.
                        </p>
                        <div className="space-y-3">
                            <div className="p-3 rounded bg-card border border-border text-sm flex justify-between">
                                <span>RETAIL</span>
                                <span className="font-mono text-muted-foreground">Margin: 30% | Conc: 40%</span>
                            </div>
                            <div className="p-3 rounded bg-card border border-border text-sm flex justify-between">
                                <span>INST_BASIC</span>
                                <span className="font-mono text-muted-foreground">Margin: 20% | Conc: 50%</span>
                            </div>
                            <div className="p-3 rounded bg-card border border-border text-sm flex justify-between">
                                <span>INST_PREMIUM</span>
                                <span className="font-mono text-muted-foreground">Margin: 15% | Conc: 60%</span>
                            </div>
                        </div>
                        <p className="text-xs text-center text-muted-foreground mt-6">
                            (Configuration updates via UI coming soon. For MVP, use the Rules API direct access).
                        </p>
                    </div>
                </div>
            </div>
        </>
    )
}
