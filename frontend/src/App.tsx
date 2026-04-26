import {BrowserRouter, Route, Routes, useLocation, useNavigate} from 'react-router-dom'
import {Activity, Moon, Sun} from 'lucide-react'
import {ThemeProvider, useTheme} from './hooks/useTheme'
import {ProjectsPage} from './pages/ProjectsPage'
import {ProjectDetailPage} from './pages/ProjectDetailPage'
import {AnalysisPage} from './pages/AnalysisPage'

function Header() {
    const {theme, toggle} = useTheme()
    const navigate = useNavigate()
    const location = useLocation()

    return (
        <header style={{
            background: 'var(--surface)',
            borderBottom: '1px solid var(--border)',
            height: 50, display: 'flex', alignItems: 'center',
            padding: '0 20px', gap: 8, flexShrink: 0,
            position: 'sticky', top: 0, zIndex: 100,
        }}>
            <button
                onClick={() => navigate('/')}
                style={{
                    background: 'none',
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    cursor: 'pointer',
                    padding: 0
                }}
            >
                <Activity size={16} color="var(--accent)"/>
                <span style={{fontWeight: 700, fontSize: 14, color: 'var(--text)'}}>MS Bottleneck Detector</span>
            </button>

            {/* Breadcrumb hint */}
            {location.pathname !== '/' && (
                <button
                    className="btn-ghost"
                    style={{marginLeft: 8, padding: '3px 10px', fontSize: 12}}
                    onClick={() => navigate(-1)}
                >
                    ← Назад
                </button>
            )}

            <button
                onClick={toggle}
                className="btn-ghost"
                style={{
                    marginLeft: 'auto',
                    padding: '4px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    fontSize: 12
                }}
            >
                {theme === 'light' ? <Moon size={13}/> : <Sun size={13}/>}
                {theme === 'light' ? 'Тёмная' : 'Светлая'}
            </button>
        </header>
    )
}

function AppRoutes() {
    return (
        <div style={{minHeight: '100vh', display: 'flex', flexDirection: 'column'}}>
            <Header/>
            <Routes>
                <Route path="/" element={<ProjectsPage/>}/>
                <Route path="/projects/:projectId" element={<ProjectDetailPage/>}/>
                <Route path="/projects/:projectId/analyse/*" element={<AnalysisPage/>}/>
            </Routes>
        </div>
    )
}

export default function App() {
    return (
        <BrowserRouter>
            <ThemeProvider>
                <AppRoutes/>
            </ThemeProvider>
        </BrowserRouter>
    )
}
