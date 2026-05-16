import { useState, useEffect } from "react"
import { useIsMobile } from "../hooks/useMediaQuery"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../api"

const SHIP_ICONS = {
  fighter: "▲", cruiser: "◆", bomber: "✦",
  planet_defense: "⬡", transport: "◫", expedition: "◉", diplomat: "♦"
}

const SHIP_COLORS = {
  fighter: "#7ab8f5", cruiser: "var(--teal)", bomber: "var(--red)",
  planet_defense: "var(--amber)", transport: "#7de88a",
  expedition: "#c084fc", diplomat: "#f0e68c"
}

const MISSION_TYPES = [
  { value: "attack",     label: "Angrep" },
  { value: "transport",  label: "Transport" },
  { value: "expedition", label: "Ekspedisjon" },
]

export default function Fleet() {
  const { token } = useAuth()
  const isMobile = useIsMobile()
  const [ships, setShips] = useState(null)
  const [missions, setMissions] = useState([])
  const [stats, setStats] = useState(null)
  const [system, setSystem] = useState(null)
  const [targetPlanets, setTargetPlanets] = useState([])
  const [loading, setLoading] = useState(true)

  const [buildForm, setBuildForm] = useState({ planet_id: "", ship_type: "fighter", quantity: 1 })
  const [buildMsg, setBuildMsg] = useState("")
  const [buildErr, setBuildErr] = useState("")

  const [sendForm, setSendForm] = useState({ origin: "", target: "", type: "attack", ships: {} })
  const [sendMsg, setSendMsg] = useState("")
  const [sendErr, setSendErr] = useState("")

  async function load() {
    try {
      const [s, m, st, sys, tp] = await Promise.all([
        apiFetch("/fleet/my-ships", {}, token),
        apiFetch("/fleet/my-missions", {}, token),
        apiFetch("/fleet/ship-stats", {}, token),
        apiFetch("/game/my-system", {}, token),
        apiFetch("/game/galaxy/target-planets", {}, token),
      ])
      setShips(s)
      setMissions(m)
      setStats(st)
      setSystem(sys)
      setTargetPlanets(tp.planets || [])

      if (sys?.planets?.length > 0 && !buildForm.planet_id) {
        const homeId = sys.planets[0].id
        setBuildForm(f => ({ ...f, planet_id: homeId }))
        setSendForm(f => ({ ...f, origin: homeId }))
      }
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token])

  async function handleBuild(e) {
    e.preventDefault()
    setBuildErr(""); setBuildMsg("")
    try {
      const res = await apiFetch("/fleet/build", {
        method: "POST",
        body: JSON.stringify({
          planet_id: buildForm.planet_id,
          ship_type: buildForm.ship_type,
          quantity: parseInt(buildForm.quantity),
        })
      }, token)
      setBuildMsg(res.message)
      load()
    } catch (err) { setBuildErr(err.message) }
  }

  async function handleSend(e) {
    e.preventDefault()
    setSendErr(""); setSendMsg("")
    const shipPayload = {}
    Object.entries(sendForm.ships).forEach(([k, v]) => {
      if (parseInt(v) > 0) shipPayload[k] = parseInt(v)
    })
    if (Object.keys(shipPayload).length === 0) {
      setSendErr("Velg minst ett skip å sende"); return
    }
    if (!sendForm.target) {
      setSendErr("Velg en målplanet"); return
    }
    try {
      const res = await apiFetch("/fleet/send", {
        method: "POST",
        body: JSON.stringify({
          origin_planet_id: sendForm.origin,
          target_planet_id: sendForm.target,
          mission_type: sendForm.type,
          ships: shipPayload,
        })
      }, token)
      setSendMsg(res.message)
      load()
    } catch (err) { setSendErr(err.message) }
  }

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )

  const myPlanets = system?.planets || []
  const shipsAtOrigin = ships?.locations?.[sendForm.origin]?.ships || {}

  // Grupper målplaneter per system
  const targetsBySystem = targetPlanets.reduce((acc, p) => {
    if (!acc[p.system_name]) acc[p.system_name] = []
    acc[p.system_name].push(p)
    return acc
  }, {})

  const availableTargets = targetPlanets.filter(p => p.id !== sendForm.origin)

  // Beregn reisetid
  const selectedTarget = targetPlanets.find(p => p.id === sendForm.target)
  const originPlanetInfo = myPlanets.find(p => p.id === sendForm.origin)
  let travelTicks = "?"
  if (selectedTarget && originPlanetInfo) {
    const originTP = targetPlanets.find(p => p.id === sendForm.origin)
    const sameSystem = originTP?.system_id === selectedTarget.system_id
    if (sameSystem) {
      travelTicks = selectedTarget.travel_ticks || 1
    } else {
      const expQty = parseInt(sendForm.ships["expedition"] || 0)
      const onlyExp = Object.entries(sendForm.ships).every(([t, q]) => t === "expedition" || parseInt(q) === 0)
      travelTicks = expQty > 0 && onlyExp ? 3 : 6
    }
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", letterSpacing: "0.15em", marginBottom: 6 }}>
          ◈ FLÅTEKOMMANDO
        </div>
        <h1 style={{ fontWeight: 700, fontSize: isMobile ? 20 : 24 }}>Flåte & Skip</h1>
      </div>

      {/* Mine skip + aktive oppdrag */}
      <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 16, marginBottom: 16 }}>

        <div className="card">
          <div className="label" style={{ marginBottom: 14 }}>Mine skip</div>
          {!ships || Object.keys(ships.locations).length === 0 ? (
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>Ingen skip bygget ennå</div>
          ) : Object.entries(ships.locations).map(([pid, loc]) => (
            <div key={pid} style={{ marginBottom: 16 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", marginBottom: 8 }}>
                {loc.planet_name.toUpperCase()}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {Object.entries(loc.ships).map(([type, qty]) => (
                  <div key={type} style={{
                    background: "var(--bg3)", border: `1px solid ${SHIP_COLORS[type] || "var(--border)"}`,
                    borderRadius: "var(--radius)", padding: "6px 12px",
                    display: "flex", alignItems: "center", gap: 6,
                  }}>
                    <span style={{ color: SHIP_COLORS[type], fontSize: 14 }}>{SHIP_ICONS[type]}</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{qty}× {type}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="label" style={{ marginBottom: 14 }}>Aktive oppdrag</div>
          {missions.length === 0 ? (
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>Ingen aktive oppdrag</div>
          ) : missions.map(m => (
            <div key={m.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12, marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{
                  fontFamily: "var(--mono)", fontSize: 11, padding: "2px 8px",
                  borderRadius: "var(--radius)", border: "1px solid",
                  borderColor: m.type === "attack" ? "var(--red)" : m.type === "expedition" ? "#c084fc" : "var(--teal)",
                  color: m.type === "attack" ? "var(--red)" : m.type === "expedition" ? "#c084fc" : "var(--teal)",
                }}>
                  {m.type.toUpperCase()}
                </span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--amber)" }}>
                  {m.ticks_remaining}t igjen
                </span>
              </div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>
                {m.origin} → {m.target}
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                {Object.entries(m.ships).map(([type, qty]) => (
                  <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 11, color: SHIP_COLORS[type] || "var(--text2)" }}>
                    {SHIP_ICONS[type]} {qty}× {type}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bygg skip + Send flåte */}
      <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 16 }}>

        {/* Bygg skip */}
        <div className="card">
          <div className="label" style={{ marginBottom: 14 }}>Bygg skip</div>
          {buildMsg && <div style={{ background: "var(--teal-dim)", border: "1px solid var(--teal)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)", marginBottom: 12 }}>✓ {buildMsg}</div>}
          {buildErr && <div style={{ background: "var(--red-dim)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--red)", marginBottom: 12 }}>⚠ {buildErr}</div>}
          <form onSubmit={handleBuild}>
            <div style={{ marginBottom: 12 }}>
              <div className="label" style={{ marginBottom: 6 }}>Planet</div>
              <select value={buildForm.planet_id} onChange={e => setBuildForm(f => ({ ...f, planet_id: e.target.value }))}>
                {myPlanets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div className="label" style={{ marginBottom: 6 }}>Skiptype</div>
              <select value={buildForm.ship_type} onChange={e => setBuildForm(f => ({ ...f, ship_type: e.target.value }))}>
                {stats && Object.entries(stats).map(([type, s]) => (
                  <option key={type} value={type}>
                    {SHIP_ICONS[type]} {type} — {s.cost_metal}M {s.cost_energy}E {s.cost_gas}G ({s.build_ticks}t)
                  </option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div className="label" style={{ marginBottom: 6 }}>Antall</div>
              <input type="number" min="1" max="100" value={buildForm.quantity}
                onChange={e => setBuildForm(f => ({ ...f, quantity: e.target.value }))} />
            </div>
            {stats && buildForm.ship_type && (
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)", marginBottom: 12, padding: "8px 12px", background: "var(--bg3)", borderRadius: "var(--radius)" }}>
                Total: {stats[buildForm.ship_type].cost_metal * buildForm.quantity}M {stats[buildForm.ship_type].cost_energy * buildForm.quantity}E {stats[buildForm.ship_type].cost_gas * buildForm.quantity}G
              </div>
            )}
            <button className="btn" type="submit" style={{ width: "100%" }}>→ Start bygging</button>
          </form>
        </div>

        {/* Send flåte */}
        <div className="card">
          <div className="label" style={{ marginBottom: 14 }}>Send flåte</div>
          {sendMsg && <div style={{ background: "var(--teal-dim)", border: "1px solid var(--teal)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)", marginBottom: 12 }}>✓ {sendMsg}</div>}
          {sendErr && <div style={{ background: "var(--red-dim)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "8px 12px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--red)", marginBottom: 12 }}>⚠ {sendErr}</div>}
          <form onSubmit={handleSend}>

            <div style={{ marginBottom: 12 }}>
              <div className="label" style={{ marginBottom: 6 }}>Fra planet</div>
              <select value={sendForm.origin} onChange={e => setSendForm(f => ({ ...f, origin: e.target.value, ships: {}, target: "" }))}>
                {myPlanets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div className="label" style={{ marginBottom: 6 }}>Til planet</div>
              {availableTargets.length === 0 ? (
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--amber)", padding: "10px 12px", background: "var(--amber-dim)", borderRadius: "var(--radius)", border: "1px solid var(--amber)" }}>
                  ◉ Bygg et ekspedisjonsskip for å utforske nabosystemer
                </div>
              ) : (
                <select value={sendForm.target} onChange={e => setSendForm(f => ({ ...f, target: e.target.value }))}>
                  <option value="">— Velg planet —</option>
                  {Object.entries(targetsBySystem).map(([sysName, planets]) => (
                    <optgroup key={sysName} label={`⬡ ${sysName}`}>
                      {planets.filter(p => p.id !== sendForm.origin).map(p => (
                        <option key={p.id} value={p.id}>
                          {p.name}{p.is_own ? " ★" : ""} · {p.planet_type}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              )}
            </div>

            {sendForm.target && (
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, marginBottom: 12, padding: "8px 12px", background: "var(--bg3)", borderRadius: "var(--radius)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text2)" }}>Estimert reisetid</span>
                <span style={{ color: "var(--teal)" }}>{travelTicks} tick(s)</span>
              </div>
            )}

            <div style={{ marginBottom: 12 }}>
              <div className="label" style={{ marginBottom: 6 }}>Oppdragstype</div>
              <select value={sendForm.type} onChange={e => setSendForm(f => ({ ...f, type: e.target.value }))}>
                {MISSION_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div className="label" style={{ marginBottom: 8 }}>Skip å sende</div>
              {Object.keys(shipsAtOrigin).length === 0 ? (
                <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
                  Ingen skip på denne planeten
                </div>
              ) : Object.entries(shipsAtOrigin).map(([type, available]) => (
                <div key={type} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <span style={{ color: SHIP_COLORS[type], width: 20, fontSize: 14 }}>{SHIP_ICONS[type]}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 12, flex: 1, color: "var(--text2)" }}>
                    {type} <span style={{ color: "var(--text3)" }}>({available})</span>
                  </span>
                  <input
                    type="number" min="0" max={available}
                    value={sendForm.ships[type] || 0}
                    onChange={e => setSendForm(f => ({ ...f, ships: { ...f.ships, [type]: e.target.value } }))}
                    style={{ width: 70 }}
                  />
                </div>
              ))}
            </div>

            <button className="btn" type="submit"
              disabled={!sendForm.target || availableTargets.length === 0}
              style={{ width: "100%" }}>
              → Send flåte
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
