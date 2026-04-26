import {useEffect, useRef, useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {ChevronRight, FolderOpen, Plus, Trash2} from 'lucide-react'
import {createProject, deleteProject, getProjects} from '../api/client'
import type {Project} from '../api/types'

export function ProjectsPage() {
    const navigate = useNavigate()
    const [projects, setProjects] = useState<Project[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showForm, setShowForm] = useState(false)
    const [newName, setNewName] = useState('')
    const [newDesc, setNewDesc] = useState('')
    const [creating, setCreating] = useState(false)
    const nameRef = useRef<HTMLInputElement>(null)

    const load = async () => {
        setLoading(true);
        setError(null)
        try {
            setProjects(await getProjects())
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])
    useEffect(() => {
        if (showForm) nameRef.current?.focus()
    }, [showForm])

    const handleCreate = async () => {
        if (!newName.trim()) return
        setCreating(true)
        try {
            await createProject(newName.trim(), newDesc.trim())
            setNewName('');
            setNewDesc('');
            setShowForm(false)
            await load()
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
        } finally {
            setCreating(false)
        }
    }

    const handleDelete = async (e: React.MouseEvent, p: Project) => {
        e.stopPropagation()
        if (!confirm(`Удалить проект «${p.name}»?`)) return
        try {
            await deleteProject(p.id);
            await load()
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
        }
    }

    return (
        <main style={{maxWidth: 900, margin: '0 auto', padding: '24px 20px', width: '100%'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20}}>
                <h1 style={{fontSize: 18, fontWeight: 700, color: 'var(--text)'}}>Проекты</h1>
                <button className="btn-primary" onClick={() => setShowForm(v => !v)}>
                    <Plus size={13} style={{marginRight: 5}}/>Новый проект
                </button>
            </div>

            {error && <div className="error-box" style={{marginBottom: 12}}>{error}</div>}

            {showForm && (
                <div className="card" style={{marginBottom: 16}}>
                    <div style={{fontWeight: 600, marginBottom: 10, color: 'var(--text)'}}>Новый проект</div>
                    <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
                        <input ref={nameRef} placeholder="Название *" value={newName}
                               onChange={e => setNewName(e.target.value)}
                               onKeyDown={e => e.key === 'Enter' && handleCreate()}/>
                        <textarea placeholder="Описание" value={newDesc}
                                  onChange={e => setNewDesc(e.target.value)}
                                  style={{resize: 'vertical', minHeight: 56}}/>
                        <div style={{display: 'flex', gap: 8}}>
                            <button className="btn-primary" onClick={handleCreate}
                                    disabled={creating || !newName.trim()}>
                                {creating ? 'Создаю...' : 'Создать'}
                            </button>
                            <button className="btn-ghost" onClick={() => {
                                setShowForm(false);
                                setNewName('');
                                setNewDesc('')
                            }}>
                                Отмена
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {loading && <div style={{textAlign: 'center', padding: 40}}>
                <div className="spinner"/>
            </div>}

            {!loading && projects.length === 0 && (
                <div className="card" style={{textAlign: 'center', padding: 48, color: 'var(--muted)'}}>
                    <FolderOpen size={36} style={{marginBottom: 12, opacity: .4}}/>
                    <div style={{color: 'var(--text2)'}}>Нет проектов. Создайте первый.</div>
                </div>
            )}

            <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
                {projects.map(p => (
                    <div
                        key={p.id}
                        className="card"
                        onClick={() => navigate(`/projects/${p.id}`)}
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            cursor: 'pointer'
                        }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                    >
                        <div>
                            <div style={{fontWeight: 600, color: 'var(--text)', fontSize: 14}}>{p.name}</div>
                            {p.description &&
                                <div style={{color: 'var(--text2)', fontSize: 12, marginTop: 2}}>{p.description}</div>}
                            <div style={{fontSize: 11, color: 'var(--muted)', marginTop: 4}}>
                                {new Date(p.created_at).toLocaleDateString('ru')} · {p.snapshots_count} снапшотов
                            </div>
                        </div>
                        <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
                            <button className="btn-danger" onClick={e => handleDelete(e, p)}
                                    style={{padding: '5px 8px'}}>
                                <Trash2 size={13}/>
                            </button>
                            <ChevronRight size={16} color="var(--muted)"/>
                        </div>
                    </div>
                ))}
            </div>
        </main>
    )
}
