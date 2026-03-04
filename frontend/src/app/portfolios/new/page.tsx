'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import { apiCreatePortfolio, apiUploadCsv } from '@/lib/api'
import { UploadCloud, CheckCircle, AlertCircle } from 'lucide-react'

export default function NewPortfolio() {
    const { user, activeOrgId } = useAuth()
    const router = useRouter()
    const [name, setName] = useState('')
    const [file, setFile] = useState<File | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!name.trim()) return setError('Name is required')
        if (!file) return setError('CSV file is required')

        setLoading(true)
        setError('')
        try {
            // 1. Create Portfolio skeleton
            const p = await apiCreatePortfolio({ name, org_id: activeOrgId || undefined })

            // 2. Upload CSV content
            await apiUploadCsv(p.id, file)

            router.push(`/portfolios/${p.id}`)
        } catch (err: any) {
            setError(err.message)
            setLoading(false)
        }
    }

    if (!user) return null

    return (
        <>
            <Navbar />
            <div className="container mx-auto px-4 py-12 max-w-2xl">
                <div className="text-center mb-10">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Create Portfolio</h1>
                    <p className="text-muted-foreground">Upload your holdings to instantly price risk coverage.</p>
                </div>

                <div className="card p-8 bg-secondary/20">
                    <form onSubmit={handleCreate} className="space-y-6">
                        {error && (
                            <div className="flex items-center gap-2 text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20">
                                <AlertCircle className="h-4 w-4" /> {error}
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium mb-1">Portfolio Name</label>
                            <input
                                type="text" required
                                className="input-field" placeholder="e.g. Retirement Equities"
                                value={name} onChange={e => setName(e.target.value)}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">CSV Template Format</label>
                            <div className="text-xs text-muted-foreground mb-3 bg-card border border-border p-3 rounded font-mono">
                                symbol,exchange,quantity<br />
                                RELIANCE,NSE,50<br />
                                AAPL,NASDAQ,100
                            </div>

                            <div className="mt-2 flex justify-center rounded-lg border border-dashed border-border px-6 py-10 hover:border-primary/50 transition-colors bg-card">
                                <div className="text-center">
                                    <UploadCloud className="mx-auto h-12 w-12 text-muted-foreground" aria-hidden="true" />
                                    <div className="mt-4 flex text-sm leading-6 text-muted-foreground">
                                        <label className="relative cursor-pointer rounded-md font-semibold text-primary hover:text-blue-400">
                                            <span>Upload a file</span>
                                            <input type="file" className="sr-only" accept=".csv" onChange={e => {
                                                if (e.target.files && e.target.files.length > 0) {
                                                    setFile(e.target.files[0])
                                                }
                                            }} />
                                        </label>
                                        <p className="pl-1">or drag and drop</p>
                                    </div>
                                    <p className="text-xs leading-5 text-muted-foreground mt-1">CSV up to 10MB</p>

                                    {file && (
                                        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-green-500 bg-green-500/10 py-2 px-4 rounded-full border border-green-500/20">
                                            <CheckCircle className="h-4 w-4" />
                                            {file.name} selected
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <button type="submit" disabled={loading} className="btn-primary w-full py-3">
                            {loading ? 'Processing...' : 'Create and Upload'}
                        </button>
                    </form>
                </div>
            </div>
        </>
    )
}
