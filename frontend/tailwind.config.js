/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                background: '#09090b', // zinc-950
                foreground: '#fafafa', // zinc-50
                card: '#18181b',       // zinc-900
                'card-foreground': '#fafafa',
                primary: '#3b82f6',    // blue-500
                'primary-foreground': '#ffffff',
                secondary: '#27272a',  // zinc-800
                'secondary-foreground': '#fafafa',
                muted: '#27272a',
                'muted-foreground': '#a1a1aa',
                accent: '#27272a',
                'accent-foreground': '#fafafa',
                border: '#27272a',     // zinc-800
                input: '#27272a',
                ring: '#3b82f6',
            },
            borderRadius: {
                lg: '0.5rem',
                md: '0.375rem',
                sm: '0.25rem',
            },
        },
    },
    plugins: [],
}
