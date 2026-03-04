'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiListPolicies, apiActivatePolicy, apiDeactivatePolicy, apiDeletePolicy } from '@/lib/api'
import Link from 'next/link'
import { Shield, Clock, CheckCircle, AlertTriangle, XCircle, Trash2, PlayCircle, PauseCircle } from 'lucide-react'
import { formatINR, formatDate } from '@/lib/utils'

export default function PoliciesList() {
    const { user, activeOrgId } = useAuth()
    const [policies, setPolicies] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [actionId, setActionId] = useState<string | null>(null)
    const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
    const [error, setError] = useState('')

    const load = () => {
        if (!user) return
        apiListPolicies(activeOrgId || undefined)
            .then(setPolicies)
            .finally(() => setLoading(false))
    }

    useEffect(() => { load() }, [user, activeOrgId])

    if (!user) return null

    const getStatusMeta = (status: string) => {
        switch (status) {
            case 'ACTIVE': return { icon: <Clock className="h-4 w-4" />, color: 'bg-blue-500/10 text-blue-500 border-blue-500/20' }
            case 'INACTIVE': return { icon: <PauseCircle className="h-4 w-4" />, color: 'bg-zinc-800 text-zinc-400 border-zinc-700' }
            case 'SETTLED': return { icon: <CheckCircle className="h-4 w-4" />, color: 'bg-green-500/10 text-green-500 border-green-500/20' }
            case 'MATURED': return { icon: <AlertTriangle className="h-4 w-4" />, color: 'bg-orange-500/10 text-orange-400 border-orange-500/20' }
            default: return { icon: <XCircle className="h-4 w-4" />, color: 'bg-red-500/10 text-red-400 border-red-500/20' }
        }
    }

    const handleAction = async (action: () => Promise<any>, id: string, updater?: (res: any) => void) => {
        setActionId(id); setError('')
        try {
            const res = await action()
            if (updater) updater(res)
            else setPolicies(ps => ps.filter(p => p.id !== id))
        } catch (e: any) { setError(e.message) }
        finally { setActionId(null) }
    }

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-8 max-w-5xl">
                <header className="mb-8 flex justify-between items-start">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight mb-2">Insurance Policies</h1>
                        <p className="text-muted-foreground">Activate, deactivate, or delete your coverage policies.</p>
                    </div>
                    <Link href="/quotes/new" className="btn-primary flex items-center gap-2">
                        <Shield className="h-4 w-4" /> New Quote
                    </Link>
                </header>

                {error && <div className="mb-4 text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20">{error}</div>}

                {/* Delete confirmation modal */}
                {confirmDelete && (
                    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
                        <div className="card p-6 max-w-sm w-full">
                            <h3 className="text-lg font-bold mb-2">Delete Policy?</h3>
                            <p className="text-muted-foreground text-sm mb-6">This permanently removes the policy record and cannot be undone.</p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => handleAction(() => apiDeletePolicy(confirmDelete), confirmDelete)}
                                    className="flex-1 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
                                >Delete</button>
                                <button onClick={() => setConfirmDelete(null)} className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-secondary/50 transition-colors">
                                    Keep
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {loading ? (
                    <div className="animate-pulse space-y-3">
                        {[1, 2, 3].map(i => <div key={i} className="h-16 bg-secondary rounded-xl"></div>)}
                    </div>
                ) : policies.length === 0 ? (
                    <div className="text-center py-16 bg-card border border-border rounded-xl">
                        <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium">No Policies Found</h3>
                        <p className="text-muted-foreground mt-2 mb-6">You haven't purchased any coverage yet.</p>
                        <Link href="/portfolios" className="btn-primary">View Portfolios</Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {policies.map(p => {
                            const { icon, color } = getStatusMeta(p.status)
                            const busy = actionId === p.id
                            return (
                                <div key={p.id} className="card p-4 flex flex-col sm:flex-row sm:items-center gap-4 hover:border-primary/30 transition-colors">
                                    {/* Status badge */}
                                    <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border w-fit ${color}`}>
                                        {icon} {p.status}
                                    </span>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                                            <span className="capitalize font-medium">{p.term.toLowerCase()} term</span>
                                            <span className="font-mono text-primary">{formatINR(p.notional_inr)} notional</span>
                                            <span className="text-muted-foreground">Premium: {formatINR(p.premium_inr)}</span>
                                            <span className="text-muted-foreground">Expires: {formatDate(p.end_date)}</span>
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-2 shrink-0">
                                        <Link href={`/policies/${p.id}`} className="text-xs px-3 py-1.5 rounded-lg border border-border hover:bg-secondary/50 transition-colors font-medium">
                                            Details
                                        </Link>

                                        {/* Activate / Deactivate toggle */}
                                        {p.status === 'ACTIVE' && (
                                            <button
                                                disabled={busy}
                                                onClick={() => handleAction(() => apiDeactivatePolicy(p.id), p.id, res => setPolicies(ps => ps.map(x => x.id === p.id ? res : x)))}
                                                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-orange-500/30 text-orange-400 hover:bg-orange-500/10 transition-colors disabled:opacity-50"
                                            >
                                                <PauseCircle className="h-3.5 w-3.5" />
                                                {busy ? '...' : 'Deactivate'}
                                            </button>
                                        )}
                                        {p.status === 'INACTIVE' && (
                                            <button
                                                disabled={busy}
                                                onClick={() => handleAction(() => apiActivatePolicy(p.id), p.id, res => setPolicies(ps => ps.map(x => x.id === p.id ? res : x)))}
                                                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-green-500/30 text-green-400 hover:bg-green-500/10 transition-colors disabled:opacity-50"
                                            >
                                                <PlayCircle className="h-3.5 w-3.5" />
                                                {busy ? '...' : 'Activate'}
                                            </button>
                                        )}

                                        {/* Delete — only when not ACTIVE */}
                                        {p.status !== 'ACTIVE' && (
                                            <button
                                                disabled={busy}
                                                onClick={() => setConfirmDelete(p.id)}
                                                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                                Delete
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                        <p className="text-xs text-muted-foreground text-right pt-1">{policies.length} {policies.length === 1 ? 'policy' : 'policies'}</p>
                    </div>
                )}
            </div>
        </>
    )
}
