'use client'

import { useAuth } from '@/lib/auth'
import { logout, apiListOrgs } from '@/lib/api'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ShieldAlert, LogOut, Building, User as UserIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function Navbar() {
    const { user, activeOrgId, setActiveOrgId } = useAuth()
    const pathname = usePathname()
    const [orgs, setOrgs] = useState<any[]>([])

    useEffect(() => {
        if (user && user.tier.startsWith('INSTITUTIONAL')) {
            apiListOrgs().then(setOrgs).catch(console.error)
        }
    }, [user])

    if (pathname === '/login' || pathname === '/signup') return null

    return (
        <nav className="border-b border-border bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 text-primary font-bold text-xl tracking-tight">
                    <ShieldAlert className="h-6 w-6" />
                    <span>PMRI<span className="text-foreground">Global</span></span>
                </Link>

                {user && (
                    <div className="flex items-center gap-6">
                        <Link href="/" className="text-sm font-medium hover:text-primary transition-colors">Dashboard</Link>
                        <Link href="/portfolios" className="text-sm font-medium hover:text-primary transition-colors">Portfolios</Link>
                        <Link href="/policies" className="text-sm font-medium hover:text-primary transition-colors">Policies</Link>
                        {user.is_admin && (
                            <Link href="/admin" className="text-sm font-medium hover:text-primary transition-colors">Admin Area</Link>
                        )}

                        <div className="h-6 w-px bg-border mx-2" />

                        {/* Org Switcher for Institutional */}
                        {user.tier.startsWith('INSTITUTIONAL') && orgs.length > 0 && (
                            <div className="flex items-center gap-2">
                                <Building className="h-4 w-4 text-muted-foreground" />
                                <select
                                    className="bg-transparent text-sm font-medium focus:outline-none cursor-pointer"
                                    value={activeOrgId || ''}
                                    onChange={(e) => setActiveOrgId(e.target.value || null)}
                                >
                                    <option value="" className="bg-card">Personal View</option>
                                    {orgs.map(o => (
                                        <option key={o.id} value={o.id} className="bg-card">{o.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="flex items-center gap-3 ml-2">
                            <div className="flex flex-col items-end">
                                <span className="text-xs font-semibold">{user.email}</span>
                                <span className="text-[10px] text-muted-foreground uppercase tracking-widest">{user.tier.replace('_', ' ')}</span>
                            </div>
                            <button
                                onClick={logout}
                                className="p-2 rounded-full hover:bg-secondary transition-colors"
                                title="Log out"
                            >
                                <LogOut className="h-4 w-4 text-muted-foreground hover:text-red-400" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </nav>
    )
}
