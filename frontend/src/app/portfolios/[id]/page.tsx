'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiGetPortfolio, apiUpdatePortfolio, apiDeletePortfolio } from '@/lib/api'
import Link from 'next/link'
import { Shield, ArrowLeft, Briefcase, Edit2, Check, X, Archive, Trash2 } from 'lucide-react'

export default function PortfolioDetail() {
    const { user } = useAuth()
    const { id } = useParams()
    const router = useRouter()
    const [portfolio, setPortfolio] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [isEditing, setIsEditing] = useState(false)
    const [newName, setNewName] = useState('')

    const fetchPortfolio = () => {
        if (!id) return
        setLoading(true)
        apiGetPortfolio(id as string)
            .then(p => {
                setPortfolio(p)
                setNewName(p.name)
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }

    useEffect(() => {
        fetchPortfolio()
    }, [id])

    const handleSaveName = async () => {
        try {
            await apiUpdatePortfolio(id as string, { name: newName })
            setPortfolio({ ...portfolio, name: newName })
            setIsEditing(false)
        } catch (err: any) {
            alert(err.message)
        }
    }

    const handleArchive = async () => {
        const nextStatus = portfolio.status === 'ARCHIVED' ? 'ACTIVE' : 'ARCHIVED'
        try {
            await apiUpdatePortfolio(id as string, { status: nextStatus })
            setPortfolio({ ...portfolio, status: nextStatus })
        } catch (err: any) {
            alert(err.message)
        }
    }

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to permanently delete this portfolio?')) return
        try {
            await apiDeletePortfolio(id as string)
            router.push('/portfolios')
        } catch (err: any) {
            alert(err.message)
        }
    }

    if (loading) return null

    if (error) {
        return (
            <>
                <Navbar />
                <div className="container mx-auto px-4 py-8 text-center text-red-500">{error}</div>
            </>
        )
    }

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-8 max-w-5xl">
                <div className="mb-4 flex justify-between items-center">
                    <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
                        <ArrowLeft className="h-4 w-4" /> Back
                    </button>
                    <div className="flex gap-2">
                        <button
                            onClick={handleArchive}
                            className="btn-secondary py-1.5 px-3 flex items-center gap-2 text-sm"
                            title={portfolio.status === 'ARCHIVED' ? 'Unarchive' : 'Archive'}
                        >
                            <Archive className="h-4 w-4" />
                            {portfolio.status === 'ARCHIVED' ? 'Unarchive' : 'Archive'}
                        </button>
                        <button
                            onClick={handleDelete}
                            className="btn-secondary py-1.5 px-3 border-red-500/30 text-red-500 hover:bg-red-500/10 flex items-center gap-2 text-sm"
                            title="Delete"
                        >
                            <Trash2 className="h-4 w-4" />
                            Delete
                        </button>
                    </div>
                </div>

                <header className="mb-8 flex justify-between items-start sm:items-end flex-col sm:flex-row gap-6">
                    <div className="flex items-center gap-4 w-full">
                        <div className="h-16 w-16 shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                            <Briefcase className="h-8 w-8" />
                        </div>
                        <div className="flex-1 min-w-0">
                            {isEditing ? (
                                <div className="flex items-center gap-2 w-full max-w-md">
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="text-2xl font-bold bg-secondary/50 border border-primary/30 rounded px-2 py-1 w-full focus:outline-none focus:ring-1 focus:ring-primary"
                                        autoFocus
                                    />
                                    <button onClick={handleSaveName} className="p-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors">
                                        <Check className="h-5 w-5" />
                                    </button>
                                    <button onClick={() => { setIsEditing(false); setNewName(portfolio.name); }} className="p-2 bg-secondary text-muted-foreground rounded-lg hover:bg-secondary/80 transition-colors">
                                        <X className="h-5 w-5" />
                                    </button>
                                </div>
                            ) : (
                                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3 truncate">
                                    {portfolio?.name}
                                    <button onClick={() => setIsEditing(true)} className="p-1.5 text-muted-foreground hover:text-primary transition-colors hover:bg-primary/10 rounded">
                                        <Edit2 className="h-4 w-4" />
                                    </button>
                                    {portfolio.status === 'ARCHIVED' && (
                                        <span className="text-xs uppercase tracking-widest bg-zinc-800 px-2.5 py-1 rounded text-zinc-400">Archived</span>
                                    )}
                                </h1>
                            )}
                            <p className="text-muted-foreground mt-1 text-sm">
                                Created {new Date(portfolio.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    </div>
                    <Link href={`/quotes/new?portfolio=${portfolio.id}`} className={`btn-primary flex items-center gap-2 shrink-0 ${portfolio.status === 'ARCHIVED' ? 'opacity-50 pointer-events-none' : ''}`}>
                        <Shield className="h-4 w-4" />
                        Get Insurance Quote
                    </Link>
                </header>

                <div className="card">
                    <div className="p-6 border-b border-border">
                        <h2 className="text-lg font-semibold">Holdings</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-muted-foreground uppercase bg-secondary/30">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Symbol</th>
                                    <th className="px-6 py-4 font-medium">Exchange</th>
                                    <th className="px-6 py-4 font-medium text-right">Quantity</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {portfolio.holdings.length === 0 ? (
                                    <tr>
                                        <td colSpan={3} className="px-6 py-8 text-center text-muted-foreground">No holdings in this portfolio.</td>
                                    </tr>
                                ) : (
                                    portfolio.holdings.map((h: any) => (
                                        <tr key={h.id} className="hover:bg-secondary/20 transition-colors">
                                            <td className="px-6 py-4 font-medium">{h.symbol}</td>
                                            <td className="px-6 py-4">
                                                <span className="bg-zinc-800 px-2 py-1 rounded text-xs text-zinc-300 pointer-events-none">
                                                    {h.exchange}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono">{h.quantity.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </>
    )
}
