import { useEffect, useMemo, useState } from 'react'

import MapPanel from './components/MapPanel'
import LoginPage from './components/LoginPage'
import { compactNumber, niceDate, percent } from './lib/format'
import { getJson } from './lib/api'
import { isAuthenticated, setToken, clearToken } from './lib/auth'

const sampleQuestions = [
  '¿Cuál intervención está más lejos de Cancún?',
  '¿Cuál intervención está más cerca de Monterrey?',
  'Más cercana a 20.701, -103.321',
  '¿Intervenciones en 5 km de 20.700,-103.320 en marzo 2026?',
  '¿Cuántas intervenciones están dentro de zone_c?',
  'Intervenciones validadas de proj_02 en zona central',
  'Reforestación por región',
]

const MONTH_OPTIONS = [
  { label: 'Todo el conjunto', month: null, year: null },
  { label: 'Enero 2026', month: 1, year: 2026 },
  { label: 'Febrero 2026', month: 2, year: 2026 },
  { label: 'Marzo 2026', month: 3, year: 2026 },
  { label: 'Abril 2026', month: 4, year: 2026 },
]

const INTENT_LABELS = {
  nearest: 'Más cercana',
  nearest_to_place: 'Más cercana a un lugar',
  farthest_from_place: 'Más lejana de un lugar',
  within_radius: 'Dentro de un radio',
  within_area: 'Dentro de un polígono',
  count_by_region: 'Conteo por región',
}

const RESULT_TYPE_LABELS = {
  single: 'Resultado único',
  collection: 'Colección',
  count: 'Conteo',
  aggregate: 'Agregado',
}

const STATUS_LABELS = {
  planned: 'Planeada',
  in_progress: 'En progreso',
  completed: 'Completada',
  validated: 'Validada',
}

function buildQuery(params) {
  const search = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  })

  const suffix = search.toString()
  return suffix ? `?${suffix}` : ''
}

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated())

  function handleLogin(token) {
    setToken(token)
    setAuthed(true)
  }

  function handleLogout() {
    clearToken()
    setAuthed(false)
  }

  if (!authed) {
    return <LoginPage onLogin={handleLogin} />
  }

  return <Dashboard onLogout={handleLogout} />
}

function Dashboard({ onLogout }) {
  const [summary, setSummary] = useState(null)
  const [areas, setAreas] = useState([])
  const [interventions, setInterventions] = useState([])
  const [question, setQuestion] = useState(sampleQuestions[0])
  const [filters, setFilters] = useState({
    month: null,
    year: null,
    status: '',
    project_id: '',
    subtype: '',
  })
  const [askResult, setAskResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [querying, setQuerying] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadBase() {
      try {
        const [summaryData, areaData] = await Promise.all([
          getJson('/geospatial/summary'),
          getJson('/geospatial/areas'),
        ])
        setSummary(summaryData)
        setAreas(areaData)
      } catch (err) {
        setError(err.message)
      }
    }

    loadBase()
  }, [])

  useEffect(() => {
    async function loadInterventions() {
      setLoading(true)
      setError('')

      try {
        const query = buildQuery({
          limit: 2000,
          month: filters.month,
          year: filters.year,
          status: filters.status,
          project_id: filters.project_id,
          subtype: filters.subtype,
        })
        const data = await getJson(`/geospatial/interventions${query}`)
        setInterventions(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadInterventions()
  }, [filters])

  const highlightedIds = useMemo(() => {
    if (!askResult) {
      return []
    }

    if (askResult.result_type === 'single' && askResult.result?.intervention) {
      return [askResult.result.intervention.id]
    }

    if (askResult.result_type === 'collection') {
      return askResult.result.map((item) => item.intervention?.id).filter(Boolean)
    }

    if (askResult.result_type === 'count' && Array.isArray(askResult.result?.items)) {
      return askResult.result.items.map((item) => item.id)
    }

    return []
  }, [askResult])

  const visibleStats = useMemo(() => {
    const validated = interventions.filter((item) => item.status === 'validated').length
    const avgScore =
      interventions.reduce((sum, item) => sum + (item.quality_score ?? 0), 0) /
      Math.max(interventions.length, 1)

    const projects = interventions.reduce((acc, item) => {
      acc[item.project_id] = (acc[item.project_id] || 0) + 1
      return acc
    }, {})

    const topProject = Object.entries(projects).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Sin proyecto dominante'

    return {
      total: interventions.length,
      validatedRatio: interventions.length ? validated / interventions.length : 0,
      avgScore,
      topProject,
    }
  }, [interventions])

  async function handleAsk() {
    setQuerying(true)
    setError('')

    try {
      const data = await getJson('/geospatial/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      setAskResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setQuerying(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="noise" />
      <div className="glow glow-a" />
      <div className="glow glow-b" />

      <header className="topbar-slim">
        <div className="brand-inline">
          <div className="brand-mark-sm"><span /></div>
          <span className="brand-name">GeoAPI</span>
          <span className="brand-sep">·</span>
          <span className="brand-sub">Geospatial Intervention Platform</span>
        </div>
        <div className="brand-badge" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <strong>FastAPI · PostGIS · GPT-OSS-20B · React</strong>
          <button className="logout-btn" onClick={onLogout}>Cerrar sesión</button>
        </div>
      </header>

      <main className="page-grid">

        <section className="workspace-row">
          <section className="map-card">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Mapa operativo</p>
                <h3>Vista territorial en tiempo real</h3>
              </div>
              <div className="status-pill">
                {loading ? 'Actualizando…' : `${interventions.length} registros`}
              </div>
            </div>

            <div className="filter-row filter-row-quad">
              <label>
                <span>Periodo</span>
                <select
                  value={`${filters.year ?? 'all'}-${filters.month ?? 'all'}`}
                  onChange={(event) => {
                    const selected = MONTH_OPTIONS.find(
                      (option) =>
                        `${option.year ?? 'all'}-${option.month ?? 'all'}` === event.target.value,
                    )
                    setFilters((current) => ({
                      ...current,
                      month: selected?.month ?? null,
                      year: selected?.year ?? null,
                    }))
                  }}
                >
                  {MONTH_OPTIONS.map((option) => (
                    <option
                      key={`${option.year ?? 'all'}-${option.month ?? 'all'}`}
                      value={`${option.year ?? 'all'}-${option.month ?? 'all'}`}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>Estado</span>
                <select
                  value={filters.status}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, status: event.target.value }))
                  }
                >
                  <option value="">Todos</option>
                  <option value="planned">Planeada</option>
                  <option value="in_progress">En progreso</option>
                  <option value="completed">Completada</option>
                  <option value="validated">Validada</option>
                </select>
              </label>

              <label>
                <span>Subtipo</span>
                <select
                  value={filters.subtype}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, subtype: event.target.value }))
                  }
                >
                  <option value="">Todos</option>
                  <option value="gavion">Gavión</option>
                  <option value="zanja">Zanja</option>
                  <option value="reforestacion">Reforestación</option>
                  <option value="presa_filtrante">Presa filtrante</option>
                  <option value="muestreo_biodiversidad">Biodiversidad</option>
                  <option value="bordo">Bordo</option>
                  <option value="terraza">Terraza</option>
                  <option value="muestreo_suelo">Muestreo suelo</option>
                </select>
              </label>

              <label>
                <span>Proyecto</span>
                <select
                  value={filters.project_id}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, project_id: event.target.value }))
                  }
                >
                  <option value="">Todos</option>
                  {['proj_01','proj_02','proj_03','proj_04','proj_05','proj_06','proj_07'].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </label>
            </div>

            <MapPanel interventions={interventions} areas={areas} highlightedIds={highlightedIds} />

            <div className="info-grid">
              <article>
                <span>Intervenciones visibles</span>
                <strong>{visibleStats.total}</strong>
              </article>
              <article>
                <span>Puntaje promedio de calidad</span>
                <strong>{visibleStats.avgScore.toFixed(2)}</strong>
              </article>
              <article>
                <span>Proyecto dominante en vista</span>
                <strong>{visibleStats.topProject}</strong>
              </article>
            </div>

            {askResult ? (
              <div className="result-card">
                <div className="result-head">
                  <div>
                    <span className="eyebrow">Intención detectada</span>
                    <h4>{INTENT_LABELS[askResult.intent.intent] ?? askResult.intent.intent}</h4>
                  </div>
                  <span className="status-pill">
                    {RESULT_TYPE_LABELS[askResult.result_type] ?? askResult.result_type}
                  </span>
                </div>

                {askResult.intent.explanation ? (
                  <p className="intent-explanation">{askResult.intent.explanation}</p>
                ) : null}

                <div className="intent-params">
                  {askResult.intent.place ? (
                    <span className="intent-tag">📍 {askResult.intent.place.replace(/_/g, ' ')}</span>
                  ) : null}
                  {askResult.intent.radius_km ? (
                    <span className="intent-tag">⊙ {askResult.intent.radius_km} km</span>
                  ) : null}
                  {askResult.intent.area_id ? (
                    <span className="intent-tag">▭ {askResult.intent.area_id}</span>
                  ) : null}
                  {askResult.intent.subtype ? (
                    <span className="intent-tag">{askResult.intent.subtype}</span>
                  ) : null}
                  {askResult.intent.status ? (
                    <span className="intent-tag">{STATUS_LABELS[askResult.intent.status] ?? askResult.intent.status}</span>
                  ) : null}
                  {askResult.intent.project_id ? (
                    <span className="intent-tag">{askResult.intent.project_id}</span>
                  ) : null}
                  {askResult.intent.start_date ? (
                    <span className="intent-tag">desde {askResult.intent.start_date}</span>
                  ) : null}
                  {askResult.intent.end_date ? (
                    <span className="intent-tag">hasta {askResult.intent.end_date}</span>
                  ) : null}
                </div>

                <div className="result-body">
                  {askResult.result_type === 'single' && askResult.result?.intervention ? (
                    <article className="result-item">
                      <div className="result-item-head">
                        <strong>{askResult.result.intervention.id}</strong>
                        <span className="result-distance">{askResult.result.distance_km} km</span>
                      </div>
                      <span className="result-meta">
                        {askResult.result.intervention.subtype} ·{' '}
                        {STATUS_LABELS[askResult.result.intervention.status] ??
                          askResult.result.intervention.status} ·{' '}
                        {askResult.result.intervention.region}
                      </span>
                      <p>
                        {askResult.result.reference_place
                          ? `Desde ${askResult.result.reference_place.name} · `
                          : ''}
                        {niceDate(askResult.result.intervention.date)} · Calidad: {askResult.result.intervention.quality_score?.toFixed(1) ?? '—'}
                      </p>
                    </article>
                  ) : null}

                  {askResult.result_type === 'collection' && Array.isArray(askResult.result) ? (
                    <div className="result-list">
                      {askResult.result.slice(0, 8).map((item) => (
                        <article key={item.intervention.id} className="result-item">
                          <div className="result-item-head">
                            <strong>{item.intervention.id}</strong>
                            <span className="result-distance">{item.distance_km} km</span>
                          </div>
                          <span className="result-meta">
                            {item.intervention.subtype} ·{' '}
                            {STATUS_LABELS[item.intervention.status] ?? item.intervention.status} ·{' '}
                            {item.intervention.region}
                          </span>
                        </article>
                      ))}
                    </div>
                  ) : null}

                  {askResult.result_type === 'count' && askResult.result ? (
                    <article className="result-item">
                      <div className="result-item-head">
                        <strong>{askResult.result.area?.name ?? askResult.result.area_id ?? 'Área'}</strong>
                        <span className="result-distance">{askResult.result.count}</span>
                      </div>
                      <span className="result-meta">intervenciones dentro del polígono</span>
                    </article>
                  ) : null}

                  {askResult.result_type === 'aggregate' && Array.isArray(askResult.result) ? (
                    <div className="result-list">
                      {askResult.result.map((item) => (
                        <article key={item.region} className="result-item">
                          <div className="result-item-head">
                            <strong>{item.region}</strong>
                            <span className="result-distance">{item.count}</span>
                          </div>
                          <span className="result-meta">intervenciones</span>
                        </article>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </section>

          <section className="assistant-card">
            <div className="panel-head panel-head-stack">
              <div>
                <p className="eyebrow">Consulta asistida</p>
                <h3>Pregunta en lenguaje natural</h3>
              </div>
              <button className="primary-button" onClick={handleAsk} disabled={querying}>
                {querying ? 'Interpretando...' : 'Ejecutar consulta'}
              </button>
            </div>

            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />

            <div className="chip-row">
              {sampleQuestions.map((item) => (
                <button key={item} className="chip" onClick={() => setQuestion(item)}>
                  {item}
                </button>
              ))}
            </div>

            <div className="info-grid">
              <article>
                <span>Cómo funciona</span>
                <p>
                  El modelo interpreta la pregunta y la API ejecuta consultas PostGIS de forma
                  determinística.
                </p>
              </article>
              <article>
                <span>Capacidades disponibles</span>
                <p>Más cercana, más lejana por estado, radio, polígono y conteo por región.</p>
              </article>
            </div>

          </section>
        </section>

        <section className="detail-card">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Capacidades espaciales</p>
              <h3>Lo que la plataforma ya resuelve</h3>
            </div>
          </div>

          <div className="detail-grid">
            <article>
              <span>Más cercana</span>
              <p>Búsqueda geodésica de la intervención más cercana a cualquier coordenada.</p>
            </article>
            <article>
              <span>Referencias nacionales</span>
              <p>Comparación contra estados de México para detectar el punto más cercano o lejano.</p>
            </article>
            <article>
              <span>Consultas por radio</span>
              <p>Buffer de distancia con filtros por fecha, proyecto, subtipo y estado.</p>
            </article>
            <article>
              <span>Contención por polígono</span>
              <p>Inspección por área para intervenciones dentro de polígonos de referencia.</p>
            </article>
            <article>
              <span>Agregados regionales</span>
              <p>Conteos por región para seguimiento operativo y control de cobertura territorial.</p>
            </article>
          </div>
        </section>

        <section className="data-card">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Lectura actual</p>
              <h3>Intervenciones recientes en foco</h3>
            </div>
          </div>

          <div className="table-list">
            {interventions.slice(0, 8).map((item) => (
              <article key={item.id} className="table-row">
                <div>
                  <strong>{item.id}</strong>
                  <span>{item.subtype}</span>
                </div>
                <div>
                  <strong>{item.project_id}</strong>
                  <span>{item.region}</span>
                </div>
                <div>
                  <strong>{STATUS_LABELS[item.status] ?? item.status}</strong>
                  <span>{niceDate(item.date)}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="summary-card">
          <div className="summary-copy">
            <p className="eyebrow">Panorama operativo</p>
            <h2>Un solo frente para entender dónde actuar y qué revisar primero.</h2>
            <p className="lede">
              La plataforma cruza capas espaciales, filtros operativos y consultas asistidas para
              traducir registros dispersos en una lectura útil para operación, seguimiento y toma
              de decisiones.
            </p>
          </div>

          <div className="summary-metrics">
            <article>
              <span>Intervenciones registradas</span>
              <strong>{summary ? compactNumber(summary.total_interventions) : '...'}</strong>
            </article>
            <article>
              <span>Áreas disponibles</span>
              <strong>{summary ? summary.total_areas : '...'}</strong>
            </article>
            <article>
              <span>Región con mayor prioridad alta</span>
              <strong>{summary?.highest_priority_region ?? '...'}</strong>
            </article>
            <article>
              <span>Participación validada visible</span>
              <strong>{percent(visibleStats.validatedRatio)}</strong>
            </article>
          </div>
        </section>
      </main>

      {error ? <div className="error-banner">{error}</div> : null}
    </div>
  )
}
