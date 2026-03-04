'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { apiMe } from './api'
import { useRouter, usePathname } from 'next/navigation'

type User = { id: string; email: string; tier: string; is_admin: boolean; created_at: string }

type AuthContextType = {
    user: User | null
    loading: boolean
    refreshCache: () => Promise<void>
    activeOrgId: string | null
    setActiveOrgId: (id: string | null) => void
}

const AuthContext = createContext<AuthContextType>({
    user: null, loading: true, refreshCache: async () => { }, activeOrgId: null, setActiveOrgId: () => { }
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null)
    const router = useRouter()
    const pathname = usePathname()

    const refreshCache = async () => {
        try {
            const u = await apiMe()
            setUser(u)
        } catch (e) {
            setUser(null)
            if (pathname !== '/login' && pathname !== '/signup') {
                router.push('/login')
            }
        } finally {
            setLoading(false)
        }
    }

    // Load activeOrgId from localStorage and fetch user ONCE on mount
    useEffect(() => {
        const saved = localStorage.getItem('pmri_active_org')
        if (saved) setActiveOrgIdState(saved)
        refreshCache()
    }, []) // ← empty deps: runs once only

    // Redirect to login if not authenticated and on a protected route
    useEffect(() => {
        if (!loading && !user && pathname !== '/login' && pathname !== '/signup') {
            router.push('/login')
        }
    }, [loading, user, pathname])

    const setActiveOrgId = (id: string | null) => {
        setActiveOrgIdState(id)
        if (id) localStorage.setItem('pmri_active_org', id)
        else localStorage.removeItem('pmri_active_org')
    }

    return (
        <AuthContext.Provider value={{ user, loading, refreshCache, activeOrgId, setActiveOrgId }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)
