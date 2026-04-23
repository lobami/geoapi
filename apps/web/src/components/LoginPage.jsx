import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const form = new URLSearchParams()
      form.set('username', username)
      form.set('password', password)

      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      })

      if (!res.ok) {
        setError('Usuario o contraseña incorrectos.')
        return
      }

      const { access_token } = await res.json()
      onLogin(access_token)
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="glow glow-a" />
      <div className="glow glow-b" />
      <div className="login-card">
        <div className="brand-inline" style={{ marginBottom: '28px' }}>
          <div className="brand-mark-sm"><span /></div>
          <span className="brand-name">Toroto</span>
          <span className="brand-sep">·</span>
          <span className="brand-sub">Un futuro compatible con la vida</span>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="login-field">
            <label>
              <span>Usuario</span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </label>
          </div>
          <div className="login-field">
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
          </div>
          {error ? <p className="login-error">{error}</p> : null}
          <button className="primary-button login-submit" type="submit" disabled={loading}>
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  )
}
