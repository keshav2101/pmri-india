import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/lib/auth'
import Navbar from '@/components/Navbar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'PMRI Global | Portfolio Market Risk Insurance',
    description: 'Manage downside risk for NSE and NASDAQ equities',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className}>
                <AuthProvider>
                    <div className="min-h-screen flex flex-col">
                        {/* Navbar will render conditionally inside its own component based on route/auth */}
                        <main className="flex-1">
                            {children}
                        </main>
                    </div>
                </AuthProvider>
            </body>
        </html>
    )
}
