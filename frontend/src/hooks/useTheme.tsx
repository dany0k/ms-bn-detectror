import {createContext, ReactNode, useContext, useEffect, useState} from 'react'

type Theme = 'light' | 'dark'

interface ThemeCtx {
    theme: Theme
    toggle: () => void
}

const Ctx = createContext<ThemeCtx>({
    theme: 'light', toggle: () => {
    }
})

export function ThemeProvider({children}: { children: ReactNode }) {
    const [theme, setTheme] = useState<Theme>(() =>
        (localStorage.getItem('theme') as Theme) ?? 'light'
    )

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme)
        localStorage.setItem('theme', theme)
    }, [theme])

    return (
        <Ctx.Provider value={{theme, toggle: () => setTheme(t => t === 'light' ? 'dark' : 'light')}}>
            {children}
        </Ctx.Provider>
    )
}

export const useTheme = () => useContext(Ctx)
