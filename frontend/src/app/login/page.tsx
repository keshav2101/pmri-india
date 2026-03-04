'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ShieldAlert } from 'lucide-react'
import { apiLogin, setToken } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const router = useRouter()
    const { refreshCache } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await apiLogin({ email, password })
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
                    Sign in to PMRI
                </h2>
                <p className="mt-2 text-center text-sm text-muted-foreground">
                    Portfolio Market Risk Insurance Global
                </p>
            </div>

            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-card py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-border">
                    <form className="space-y-6" onSubmit={handleSubmit}>
                        {error && <div className="text-red-500 text-sm bg-red-500/10 p-3 rounded-md border border-red-500/20">{error}</div>}

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Email address</label>
                            <input
                                type="email" required
                                className="input-field"
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
                            {loading ? 'Signing in...' : 'Sign in'}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm">
                        <span className="text-muted-foreground">New to PMRI? </span>
                        <Link href="/signup" className="font-medium text-primary hover:text-blue-400 transition-colors">
                            Create an account
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
