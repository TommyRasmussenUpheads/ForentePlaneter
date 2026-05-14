import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../api"

const SHIP_ICONS = {
  fighter: "▲", cruiser: "◆", bomber: "✦",
  planet_defense: "⬡", transport: "◫", expedition: "◉", diplomat: "♦"
}
const SHIP_COLORS = {
  fighter: "#3b82f6", cruiser: "#0891b2", bomber: "#e11d48",
  planet_defense: "#d97706", transport: "#059669",
  expedition: "#7c3aed", diplomat: "#ca8a04"
}

const SHIP_BUILD_COSTS = {
  fighter:        { ticks: 2, metal: 50,  energy: 20,  gas: 10  },
  cruiser:        { ticks: 4, metal: 120, energy: 30,  gas: 20  },
  bomber:         { ticks: 3, metal: 40,  energy: 150, gas: 20  },
  planet_defense: { ticks: 5, metal: 60,  energy: 20,  gas: 120 },
  transport:      { ticks: 4, metal: 200, energy: 40,  gas: 30  },
  expedition:     { ticks: 6, metal: 80,  energy: 100, gas: 60  },
  diplomat:       { ticks: 8, metal: 100, energy: 150, gas: 80  },
}

function ResourceRow({ label, value, prod, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <div style={{ flex: 1, fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>{label}</div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: "bold", color, minWidth: 80, textAlign: "right" }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: prod > 0 ? color : "var(--text3)", minWidth: 60, textAlign: "right", opacity: 0.7 }}>
        {prod > 0 ? `+${prod}/t` : "—"}
      </div>
    </div>
  )
}

function FlightBoard({ missions, planetId, planetName }) {
  const departing = missions.filter(m => m.origin_id === planetId && m.status === "in_flight")
  const arriving  = missions.filter(m => m.target_id === planetId && m.status === "in_flight")

  if (departing.length === 0 && arriving.length === 0) return (
    <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)", padding: "12px 0" }}>
      Ingen aktive oppdrag
    </div>
  )

  return (
    <div>
      {arriving.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--green)", letterSpacing: "0.1em", marginBottom: 8 }}>
            ↓ ANKOMSTER
          </div>
          {arriving.map(m => (
            <div key={m.id} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "8px 10px", marginBottom: 6,
              background: "rgba(5,150,105,0.06)", border: "1px solid rgba(5,150,105,0.2)",
              borderRadius: "var(--radius)"
            }}>
              <div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)", marginBottom: 3 }}>
                  Fra {m.origin}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(m.ships).map(([type, qty]) => (
                    <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 11, color: SHIP_COLORS[type] || "var(--text2)" }}>
                      {SHIP_ICONS[type]} {qty}× {type}
                    </span>
                  ))}
                  {m.cargo && (m.cargo.metal > 0 || m.cargo.energy > 0 || m.cargo.gas > 0) && (
                    <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)" }}>
                      [{m.cargo.metal}M {m.cargo.energy}E {m.cargo.gas}G]
                    </span>
                  )}
                </div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--green)", fontWeight: "bold" }}>
                  {m.ticks_remaining}t
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)" }}>
                  {m.type.toUpperCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {departing.length > 0 && (
        <div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--red)", letterSpacing: "0.1em", marginBottom: 8 }}>
            ↑ AVGANGER
          </div>
          {departing.map(m => (
            <div key={m.id} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "8px 10px", marginBottom: 6,
              background: "rgba(225,29,72,0.04)", border: "1px solid rgba(225,29,72,0.15)",
              borderRadius: "var(--radius)"
            }}>
              <div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)", marginBottom: 3 }}>
                  Til {m.target}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(m.ships).map(([type, qty]) => (
                    <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 11, color: SHIP_COLORS[type] || "var(--text2)" }}>
                      {SHIP_ICONS[type]} {qty}× {type}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--red)", fontWeight: "bold" }}>
                  {m.ticks_remaining}t
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)" }}>
                  {m.type.toUpperCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function BuildPanel({ planet, token, onBuilt }) {
  const [shipType, setShipType] = useState("fighter")
  const [qty, setQty] = useState(1)
  const [msg, setMsg] = useState("")
  const [err, setErr] = useState("")
  const [loading, setLoading] = useState(false)
  const [queue, setQueue] = useState([])

  useEffect(() => {
    apiFetch(`/fleet/build-queue/${planet.id}`, {}, token)
      .then(setQueue).catch(() => {})
  }, [planet.id, token, msg])

  const costs = SHIP_BUILD_COSTS[shipType]
  const totalCost = { metal: costs.metal * qty, energy: costs.energy * qty, gas: costs.gas * qty }
  const canAfford = planet.resources.metal >= totalCost.metal &&
                    planet.resources.energy >= totalCost.energy &&
                    planet.resources.gas >= totalCost.gas

  async function handleBuild(e) {
    e.preventDefault()
    setErr(""); setMsg(""); setLoading(true)
    try {
      const res = await apiFetch("/fleet/build", {
        method: "POST",
        body: JSON.stringify({ planet_id: planet.id, ship_type: shipType, quantity: parseInt(qty) })
      }, token)
      setMsg(res.message)
      onBuilt()
    } catch (err) { setErr(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div>
      {queue.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text2)", letterSpacing: "0.1em", marginBottom: 8 }}>
            BYGGEKØ
          </div>
          {queue.map((bq, i) => (
            <div key={bq.id} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "7px 10px", marginBottom: 5,
              background: i === 0 ? "var(--teal-dim)" : "var(--bg3)",
              border: `1px solid ${i === 0 ? "var(--teal)" : "var(--border)"}`,
              borderRadius: "var(--radius)"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: SHIP_COLORS[bq.ship_type], fontSize: 14 }}>{SHIP_ICONS[bq.ship_type]}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{bq.quantity}× {bq.ship_type}</span>
                {i === 0 && <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--teal)" }}>BYGGER</span>}
              </div>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: i === 0 ? "var(--teal)" : "var(--text2)" }}>
                {bq.ticks_remaining}t igjen
              </span>
            </div>
          ))}
        </div>
      )}

      {msg && <div style={{ background: "var(--teal-dim)", border: "1px solid var(--teal)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)", marginBottom: 12 }}>✓ {msg}</div>}
      {err && <div style={{ background: "var(--red-dim)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--red)", marginBottom: 12 }}>⚠ {err}</div>}

      <form onSubmit={handleBuild}>
        <div style={{ marginBottom: 10 }}>
          <div className="label" style={{ marginBottom: 6 }}>Skiptype</div>
          <select value={shipType} onChange={e => setShipType(e.target.value)}>
            {Object.entries(SHIP_BUILD_COSTS).map(([type, c]) => (
              <option key={type} value={type}>
                {SHIP_ICONS[type]} {type} — {c.ticks}t — {c.metal}M {c.energy}E {c.gas}G
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 12 }}>
          <div className="label" style={{ marginBottom: 6 }}>Antall</div>
          <input type="number" min="1" max="999" value={qty}
            onChange={e => setQty(e.target.value)} />
        </div>

        <div style={{
          padding: "10px 12px", borderRadius: "var(--radius)",
          background: canAfford ? "var(--teal-dim)" : "var(--red-dim)",
          border: `1px solid ${canAfford ? "var(--teal)" : "var(--red)"}`,
          fontFamily: "var(--mono)", fontSize: 11, marginBottom: 12
        }}>
          <div style={{ color: "var(--text2)", marginBottom: 4 }}>Kostnad totalt:</div>
          <div style={{ display: "flex", gap: 16 }}>
            {[["Metall", totalCost.metal, "#3b82f6"], ["Energi", totalCost.energy, "#d97706"], ["Gass", totalCost.gas, "#059669"]].map(([l, v, c]) => (
              <span key={l} style={{ color: c }}>{l[0]}: {v.toLocaleString()}</span>
            ))}
          </div>
          {!canAfford && <div style={{ color: "var(--red)", marginTop: 4, fontSize: 10 }}>⚠ Ikke nok ressurser</div>}
        </div>

        <button className="btn" type="submit" disabled={loading || !canAfford} style={{ width: "100%" }}>
          {loading ? "Bestiller..." : "→ Bestill bygging"}
        </button>
      </form>
    </div>
  )
}

function ShipsOnPlanet({ planetId, ships }) {
  const here = ships?.locations?.[planetId]?.ships || {}
  if (Object.keys(here).length === 0) return (
    <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>Ingen skip stasjonert her</div>
  )
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {Object.entries(here).map(([type, qty]) => (
        <div key={type} style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "6px 12px",
          background: "var(--bg3)",
          border: `1px solid ${SHIP_COLORS[type] || "var(--border)"}`,
          borderRadius: "var(--radius)"
        }}>
          <span style={{ color: SHIP_COLORS[type], fontSize: 14 }}>{SHIP_ICONS[type]}</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{qty}× {type}</span>
        </div>
      ))}
    </div>
  )
}

function PlanetPanel({ planet, missions, ships, token, onBuilt, onClose }) {
  const [tab, setTab] = useState("overview")
  const typeLabel = { home: "Hjemplanet", neighbor: "Naboplaner", npc: "NPC-planet", elder_race: "Elder Race" }
  const typeColor = { home: "var(--teal)", neighbor: "#3b82f6", npc: "var(--text3)", elder_race: "#ca8a04" }
  const color = typeColor[planet.type] || "var(--text2)"

  const tabs = [
    { id: "overview", label: "Oversikt" },
    { id: "flights",  label: "Trafikk" },
    { id: "build",    label: "Bygg" },
  ]

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100, padding: 20
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card fade-in" style={{
        width: "100%", maxWidth: 560,
        boxShadow: "0 8px 40px rgba(0,0,0,0.2)",
        borderTop: `3px solid ${color}`,
        maxHeight: "90vh", overflow: "auto"
      }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color, letterSpacing: "0.1em", marginBottom: 4 }}>
              {typeLabel[planet.type]?.toUpperCase()}
              {planet.travel_ticks > 0 && ` · ${planet.travel_ticks}t fra hjemplanet`}
            </div>
            <h2 style={{ fontWeight: 700, fontSize: 20 }}>{planet.name}</h2>
            {planet.blockade_status === "blockaded" && (
              <span style={{
                fontFamily: "var(--mono)", fontSize: 10, padding: "2px 8px",
                background: "var(--red-dim)", border: "1px solid var(--red)",
                borderRadius: "var(--radius)", color: "var(--red)", marginTop: 6, display: "inline-block"
              }}>⚠ UNDER BLOKADE</span>
            )}
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--text3)", fontSize: 20, lineHeight: 1, padding: 4
          }}>×</button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2, marginBottom: 20, borderBottom: "1px solid var(--border)", paddingBottom: 0 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              fontFamily: "var(--mono)", fontSize: 12, padding: "8px 16px",
              background: "none", border: "none", cursor: "pointer",
              borderBottom: `2px solid ${tab === t.id ? color : "transparent"}`,
              color: tab === t.id ? color : "var(--text2)",
              marginBottom: -1, transition: "all 0.15s"
            }}>{t.label.toUpperCase()}</button>
          ))}
        </div>

        {/* Tab: Overview */}
        {tab === "overview" && (
          <div>
            <div className="label" style={{ marginBottom: 10 }}>Ressurser</div>
            <ResourceRow label="Metall"  value={planet.resources.metal}  prod={planet.production_per_tick.metal}  color="#3b82f6" />
            <ResourceRow label="Energi"  value={planet.resources.energy} prod={planet.production_per_tick.energy} color="#d97706" />
            <ResourceRow label="Gass"    value={planet.resources.gas}    prod={planet.production_per_tick.gas}    color="#059669" />

            <div style={{ marginTop: 20 }}>
              <div className="label" style={{ marginBottom: 10 }}>Skip stasjonert</div>
              <ShipsOnPlanet planetId={planet.id} ships={ships} />
            </div>

            <div style={{
              marginTop: 20, padding: "10px 14px",
              background: "var(--bg3)", borderRadius: "var(--radius)",
              display: "flex", justifyContent: "space-between"
            }}>
              <span className="label">Score</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 14, color }}>
                {planet.score.toLocaleString()}
              </span>
            </div>
          </div>
        )}

        {/* Tab: Flights */}
        {tab === "flights" && (
          <FlightBoard missions={missions} planetId={planet.id} planetName={planet.name} />
        )}

        {/* Tab: Build */}
        {tab === "build" && (
          planet.blockade_status === "blockaded"
            ? <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--red)" }}>
                ⚠ Planeten er under blokade. Kun diplomatskip kan bygges.
              </div>
            : <BuildPanel planet={planet} token={token} onBuilt={onBuilt} />
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { token } = useAuth()
  const [system, setSystem] = useState(null)
  const [missions, setMissions] = useState([])
  const [ships, setShips] = useState(null)
  const [gameStatus, setGameStatus] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [sys, status, m, s] = await Promise.all([
        apiFetch("/game/my-system", {}, token),
        apiFetch("/game/status", {}, token),
        apiFetch("/fleet/my-missions", {}, token),
        apiFetch("/fleet/my-ships", {}, token),
      ])
      setSystem(sys)
      setGameStatus(status)
      // Enrich missions with planet IDs for flight board
      setMissions(m)
      setShips(s)
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [token])

  // Enrich missions with planet IDs from system
  const enrichedMissions = missions.map(m => {
    const planets = system?.planets || []
    const originPlanet = planets.find(p => p.name === m.origin)
    const targetPlanet = planets.find(p => p.name === m.target)
    return {
      ...m,
      origin_id: originPlanet?.id,
      target_id: targetPlanet?.id,
    }
  })

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )

  if (!system?.planets) return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div style={{ fontFamily: "var(--mono)", color: "var(--text2)", marginBottom: 12 }}>◌ Venter på spillstart...</div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>{system?.message}</div>
    </div>
  )

  const totalRes = system.planets.reduce((s, p) =>
    s + p.resources.metal + p.resources.energy + p.resources.gas, 0)
  const totalProd = system.total_production_per_tick.metal + system.total_production_per_tick.energy + system.total_production_per_tick.gas

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", letterSpacing: "0.15em", marginBottom: 6 }}>
          ◈ SOLSYSTEM — {system.system.name.replace("System-", "").toUpperCase()}
        </div>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-end", flexWrap: "wrap" }}>
          <h1 style={{ fontWeight: 700, fontSize: 24 }}>Planetsystem</h1>
          {gameStatus?.current_tick > 0 && (
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)", marginBottom: 4 }}>
              Tick {gameStatus.current_tick}
            </div>
          )}
        </div>
      </div>

      {/* Summary stats */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: 10, marginBottom: 24
      }}>
        {[
          { label: "Planeter",       value: system.planets.length,       color: "var(--teal)" },
          { label: "Totale res.",    value: totalRes.toLocaleString(),   color: "#3b82f6" },
          { label: "Prod./tick",     value: `+${totalProd.toLocaleString()}`, color: "#d97706" },
          { label: "Score",          value: (system.planets[0]?.score || 0).toLocaleString(), color: "var(--green)" },
        ].map(s => (
          <div key={s.label} className="card" style={{ textAlign: "center", padding: "12px 10px" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 18, fontWeight: "bold", color: s.color, marginBottom: 4 }}>{s.value}</div>
            <div className="label" style={{ fontSize: 10 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Planet cards — click to open */}
      <div className="label" style={{ marginBottom: 12 }}>
        Klikk på en planet for detaljer og bygging
      </div>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: 12
      }}>
        {system.planets.map(p => {
          const typeColor = { home: "var(--teal)", neighbor: "#3b82f6", npc: "var(--text3)" }
          const color = typeColor[p.type] || "var(--text2)"
          const hasIncoming = enrichedMissions.some(m => m.target_id === p.id && m.status === "in_flight")
          const hasOutgoing = enrichedMissions.some(m => m.origin_id === p.id && m.status === "in_flight")
          const shipsHere = ships?.locations?.[p.id]?.ships || {}
          const totalShips = Object.values(shipsHere).reduce((a, b) => a + b, 0)

          return (
            <button key={p.id} onClick={() => setSelected(p)} style={{
              background: "var(--bg2)", border: `1px solid var(--border)`,
              borderTop: `3px solid ${color}`,
              borderRadius: "var(--radius)", padding: 16,
              cursor: "pointer", textAlign: "left", width: "100%",
              boxShadow: "var(--shadow)", transition: "all 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = color; e.currentTarget.style.boxShadow = "var(--glow)" }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.boxShadow = "var(--shadow)" }}>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 9, color, letterSpacing: "0.1em", marginBottom: 3 }}>
                    {p.type.toUpperCase()}{p.travel_ticks > 0 ? ` · ${p.travel_ticks}t` : ""}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--text)" }}>{p.name}</div>
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  {hasIncoming && <span style={{ fontSize: 10, color: "var(--green)" }}>↓</span>}
                  {hasOutgoing && <span style={{ fontSize: 10, color: "var(--red)" }}>↑</span>}
                  {p.blockade_status === "blockaded" && <span style={{ fontSize: 10, color: "var(--red)" }}>⚠</span>}
                </div>
              </div>

              {/* Resource mini-bars */}
              <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                {[
                  { val: p.resources.metal,  prod: p.production_per_tick.metal,  color: "#3b82f6" },
                  { val: p.resources.energy, prod: p.production_per_tick.energy, color: "#d97706" },
                  { val: p.resources.gas,    prod: p.production_per_tick.gas,    color: "#059669" },
                ].map((r, i) => (
                  <div key={i} style={{ flex: 1 }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: r.color, fontWeight: "bold" }}>
                      {r.val.toLocaleString()}
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: r.prod > 0 ? r.color : "var(--text3)", opacity: 0.7 }}>
                      {r.prod > 0 ? `+${r.prod}` : "—"}
                    </div>
                  </div>
                ))}
              </div>

              {/* Ships */}
              {totalShips > 0 && (
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {Object.entries(shipsHere).map(([type, qty]) => (
                    <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 11, color: SHIP_COLORS[type] || "var(--text3)" }}>
                      {SHIP_ICONS[type]} {qty}
                    </span>
                  ))}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Planet detail panel */}
      {selected && (
        <PlanetPanel
          planet={selected}
          missions={enrichedMissions}
          ships={ships}
          token={token}
          onBuilt={load}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
