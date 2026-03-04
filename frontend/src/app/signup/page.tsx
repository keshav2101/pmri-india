'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ShieldAlert, User, Building } from 'lucide-react'
import { apiRegister, setToken } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { cn } from '@/lib/utils'

export default function Signup() {
    const [type, setType] = useState<'RETAIL' | 'INSTITUTIONAL'>('RETAIL')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [orgName, setOrgName] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const router = useRouter()
    const { refreshCache } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const payload = { email, password, account_type: type, org_name: type === 'INSTITUTIONAL' ? orgName : undefined }
            const res = await apiRegister(payload)
            setToken(res.access_token)
            await refreshCache()
            router.push('/dashboard')
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md flex flex-col items-center">
                <ShieldAlert className="h-12 w-12 text-primary mb-4" />
                <h2 className="text-center text-3xl font-extrabold tracking-tight text-foreground">
                    Create an account
                </h2>
            </div>

            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-card py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-border">

                    <div className="flex gap-4 mb-8">
                        <button
                            type="button"
                            onClick={() => setType('RETAIL')}
                            className={`flex-1 py-3 px-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all ${type === 'RETAIL' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-zinc-700'
                                }`}
                        >
                            <User className="h-6 w-6" />
                            <span className="font-semibold text-sm">Retail</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setType('INSTITUTIONAL')}
                            className={`flex-1 py-3 px-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all ${type === 'INSTITUTIONAL' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-zinc-700'
                                }`}
                        >
                            <Building className="h-6 w-6" />
                            <span className="font-semibold text-sm">Institutional</span>
                        </button>
                    </div>

                    <form className="space-y-6" onSubmit={handleSubmit}>
                        {error && <div className="text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20">{error}</div>}

                        {type === 'INSTITUTIONAL' && (
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">Organisation Name</label>
                                <input
                                    type="text" required
                                    className="input-field" placeholder="e.g. Global Macro Fund"
                                    value={orgName} onChange={e => setOrgName(e.target.value)}
                                />
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Work Email</label>
                            <input
                                type="email" required
                                className="input-field" placeholder="you@example.com"
                                value={email} onChange={e => setEmail(e.target.value)}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Password</label>
                            <input
                                type="password" required
                                className="input-field"
                                value={password} onChange={e => setPassword(e.target.value)}
                            />
                        </div>

                        <button type="submit" disabled={loading} className="btn-primary w-full flex justify-center py-2.5">
                            {loading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm">
                        <span className="text-muted-foreground">Already have an account? </span>
                        <Link href="/login" className="font-medium text-primary hover:text-blue-400 transition-colors">
                            Sign in
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
