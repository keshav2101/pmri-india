'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiListPortfolios, apiUpdatePortfolio, apiDeletePortfolio } from '@/lib/api'
import Link from 'next/link'
import { Briefcase, Plus, Archive, Trash2, Eye, EyeOff, Shield, ChevronRight, ArchiveX, AlertCircle, Search } from 'lucide-react'

export default function PortfolioList() {
    const { user, activeOrgId } = useAuth()
    const router = useRouter()
    const [portfolios, setPortfolios] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [showArchived, setShowArchived] = useState(false)
    const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
    const [actionLoading, setActionLoading] = useState<string | null>(null)
    const [search, setSearch] = useState('')
    const [error, setError] = useState('')

    const fetchPortfolios = () => {
        setLoading(true)
        apiListPortfolios(activeOrgId || undefined)
            .then((data: any[]) => setPortfolios(data))
            .catch(() => setError('Failed to load portfolios'))
            .finally(() => setLoading(false))
    }

    useEffect(() => { if (user) fetchPortfolios() }, [user, activeOrgId])

    const handleArchive = async (p: any, e: React.MouseEvent) => {
        e.preventDefault(); e.stopPropagation()
        const nextStatus = p.status === 'ARCHIVED' ? 'ACTIVE' : 'ARCHIVED'
        setActionLoading(p.id)
        try {
            await apiUpdatePortfolio(p.id, { status: nextStatus })
            setPortfolios(prev => prev.map(x => x.id === p.id ? { ...x, status: nextStatus } : x))
        } catch (err: any) { setError(err.message) }
        setActionLoading(null)
    }

    const handleDeleteClick = (id: string, e: React.MouseEvent) => {
        e.preventDefault(); e.stopPropagation()
        setConfirmDelete(id)
    }

    const handleDeleteConfirm = async () => {
        if (!confirmDelete) return
        setActionLoading(confirmDelete)
        try {
            await apiDeletePortfolio(confirmDelete)
            setPortfolios(prev => prev.filter(x => x.id !== confirmDelete))
        } catch (err: any) { setError(err.message) }
        setConfirmDelete(null)
        setActionLoading(null)
    }

    if (!user) return null

    const filtered = portfolios.filter(p => {
        const matchSearch = p.name.toLowerCase().includes(search.toLowerCase())
        const matchArchive = showArchived ? true : p.status !== 'ARCHIVED'
        return matchSearch && matchArchive
    })

    const archivedCount = portfolios.filter(p => p.status === 'ARCHIVED').length

    return (
        <>
            <Navbar />
            {/* Delete Confirmation Modal */}
            {confirmDelete && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
                    <div className="card p-6 max-w-sm w-full mx-4 shadow-2xl border-red-500/20">
                        <div className="flex items-start gap-3 mb-4">
                            <span className="h-10 w-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0">
                                <Trash2 className="h-5 w-5 text-red-500" />
                            </span>
                            <div>
                                <h3 className="font-semibold">Delete Portfolio?</h3>
                                <p className="text-sm text-muted-foreground mt-1">This action cannot be undone. Active insurance policies on this portfolio will prevent deletion.</p>
                            </div>
                        </div>
                        <div className="flex gap-3 justify-end">
                            <button onClick={() => setConfirmDelete(null)} className="btn-secondary text-sm py-1.5">Cancel</button>
                            <button onClick={handleDeleteConfirm} className="btn-secondary text-sm py-1.5 border-red-500/40 text-red-500 hover:bg-red-500/10">
                                {actionLoading ? 'Deleting...' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="container mx-auto px-4 py-8 max-w-5xl">
                {/* Header */}
                <div className="flex justify-between items-start mb-8 gap-4 flex-wrap">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight mb-1">Portfolios</h1>
                        <p className="text-sm text-muted-foreground">Manage your investment portfolios and get market risk coverage.</p>
                    </div>
                    <Link href="/portfolios/new" className="btn-primary flex items-center gap-2 shrink-0">
                        <Plus className="h-4 w-4" />
                        New Portfolio
                    </Link>
                </div>

                {error && (
                    <div className="flex items-center gap-2 text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20 mb-6">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{error}</span>
                        <button onClick={() => setError('')} className="ml-auto">✕</button>
                    </div>
                )}

                {/* Toolbar */}
                <div className="flex items-center gap-3 mb-5 flex-wrap">
                    <div className="relative flex-1 min-w-48">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <input
                            type="text"
                            placeholder="Search portfolios..."
                            value={search}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
                            className="input-field pl-9"
                        />
                    </div>
                    {archivedCount > 0 && (
                        <button
                            onClick={() => setShowArchived(v => !v)}
                            className="btn-secondary flex items-center gap-2 text-sm py-2"
                        >
                            {showArchived ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            {showArchived ? 'Hide Archived' : `Show Archived (${archivedCount})`}
                        </button>
                    )}
                </div>

                {/* Portfolio List */}
                {loading ? (
                    <div className="space-y-3">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-20 bg-secondary/50 rounded-xl animate-pulse" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="card p-12 text-center">
                        <Briefcase className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
                        <h3 className="font-semibold mb-2">
                            {search ? 'No portfolios found' : portfolios.length === 0 ? 'No portfolios yet' : 'All portfolios are archived'}
                        </h3>
                        <p className="text-sm text-muted-foreground mb-6">
                            {search ? 'Try a different search term.' : portfolios.length === 0 ? 'Upload a CSV to create your first portfolio.' : 'Toggle "Show Archived" to see them.'}
                        </p>
                        {portfolios.length === 0 && (
                            <Link href="/portfolios/new" className="btn-primary inline-flex items-center gap-2">
                                <Plus className="h-4 w-4" />
                                Create Portfolio
                            </Link>
                        )}
                    </div>
                ) : (
                    <div className="space-y-3">
                        {filtered.map(p => {
                            const isArchived = p.status === 'ARCHIVED'
                            const holdCount = p.holdings?.length ?? 0
                            const isDeleting = actionLoading === p.id && confirmDelete === p.id
                            const isActioning = actionLoading === p.id

                            return (
                                <div
                                    key={p.id}
                                    className={`card group flex items-center gap-4 px-5 py-4 transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 ${isArchived ? 'opacity-60' : ''}`}
                                >
                                    {/* Icon */}
                                    <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 border transition-colors ${isArchived ? 'bg-zinc-800 border-zinc-700 text-zinc-400' : 'bg-primary/10 border-primary/20 text-primary'}`}>
                                        {isArchived ? <ArchiveX className="h-5 w-5" /> : <Briefcase className="h-5 w-5" />}
                                    </div>

                                    {/* Name & Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-semibold text-sm">{p.name}</span>
                                            {isArchived && (
                                                <span className="text-[10px] font-semibold uppercase bg-zinc-800 text-zinc-400 border border-zinc-700 px-2 py-0.5 rounded-full tracking-widest">
                                                    Archived
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3 mt-0.5">
                                            <span className="text-xs text-muted-foreground">{holdCount} {holdCount === 1 ? 'holding' : 'holdings'}</span>
                                            <span className="text-xs text-muted-foreground">•</span>
                                            <span className="text-xs text-muted-foreground">Created {new Date(p.created_at).toLocaleDateString('en-IN')}</span>
                                        </div>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                                        {/* Get Quote */}
                                        {!isArchived && (
                                            <Link
                                                href={`/quotes/new?portfolio=${p.id}`}
                                                title="Get Insurance Quote"
                                                className="h-8 w-8 rounded-lg border border-border flex items-center justify-center hover:bg-blue-500/10 hover:border-blue-500/30 hover:text-blue-500 text-muted-foreground transition-colors"
                                                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                                            >
                                                <Shield className="h-3.5 w-3.5" />
                                            </Link>
                                        )}

                                        {/* Archive */}
                                        <button
                                            onClick={(e: React.MouseEvent) => handleArchive(p, e)}
                                            disabled={!!isActioning}
                                            title={isArchived ? 'Unarchive' : 'Archive'}
                                            className="h-8 w-8 rounded-lg border border-border flex items-center justify-center hover:bg-amber-500/10 hover:border-amber-500/30 hover:text-amber-500 text-muted-foreground transition-colors disabled:opacity-50"
                                        >
                                            {isActioning ? (
                                                <span className="h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full animate-spin inline-block" />
                                            ) : isArchived ? (
                                                <Eye className="h-3.5 w-3.5" />
                                            ) : (
                                                <Archive className="h-3.5 w-3.5" />
                                            )}
                                        </button>

                                        {/* Delete */}
                                        <button
                                            onClick={(e: React.MouseEvent) => handleDeleteClick(p.id, e)}
                                            disabled={!!actionLoading}
                                            title="Delete"
                                            className="h-8 w-8 rounded-lg border border-border flex items-center justify-center hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-500 text-muted-foreground transition-colors disabled:opacity-50"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                    </div>

                                    {/* Navigate */}
                                    <Link
                                        href={`/portfolios/${p.id}`}
                                        className="flex items-center text-muted-foreground hover:text-foreground transition-colors shrink-0 ml-1"
                                        title="View portfolio"
                                    >
                                        <ChevronRight className="h-5 w-5" />
                                    </Link>
                                </div>
                            )
                        })}
                    </div>
                )}

                {/* Summary footer */}
                {filtered.length > 0 && (
                    <p className="text-xs text-muted-foreground text-center mt-5">
                        Showing {filtered.length} of {portfolios.length} portfolio{portfolios.length !== 1 ? 's' : ''}
                    </p>
                )}
            </div>
        </>
    )
}
