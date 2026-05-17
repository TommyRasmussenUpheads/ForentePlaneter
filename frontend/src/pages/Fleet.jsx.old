import { useState, useEffect } from "react"
import { useIsMobile } from "../hooks/useMediaQuery"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../api"

const SHIP_ICONS = {
  fighter: "▲", cruiser: "◆", bomber: "✦",
  planet_defense: "⬡", transport: "◫", expedition: "◉", diplomat: "♦"
}
const SHIP_COLORS = {
  fighter: "#7ab8f5", cruiser: "#00e5cc", bomber: "#ff4455",
  planet_defense: "#f0a500", transport: "#7de88a",
  expedition: "#c084fc", diplomat: "#f0e68c"
}
const SHIP_DESC = {
  fighter:        "Lett angrepsfly",
  cruiser:        "Tungt kampskip",
  bomber:         "Høy angrepsverdi",
  planet_defense: "Stasjonært forsvar",
  transport:      "Frakter ressurser",
  expedition:     "Utforsker systemer",
  diplomat:       "Diplomatisk skip",
}
const MILITARY_TYPES   = new Set(["fighter", "cruiser", "bomber", "planet_defense", "diplomat"])
const EXPEDITION_TYPES = new Set(["expedition"])
const TRANSPORT_TYPES  = new Set(["transport"])

function classifyFleet(ships) {
  const active = Object.entries(ships).filter(([, q]) => q > 0).map(([t]) => t)
  if (active.some(t => MILITARY_TYPES.has(t)))   return "military"
  if (active.some(t => TRANSPORT_TYPES.has(t)))  return "transport"
  return "expedition"
}

// ── Skipsvelger grid ──────────────────────────────────────────

function ShipGrid({ available, selected, onChange }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 8 }}>
      {Object.entries(available).map(([type, max]) => {
        const qty = selected[type] || 0
        const color = SHIP_COLORS[type] || "var(--teal)"
        const active = qty > 0
        return (
          <div key={type} style={{
            border: `1px solid ${active ? color : "var(--border)"}`,
            borderRadius: "var(--radius)",
            background: active ? `${color}18` : "var(--bg3)",
            padding: "10px 10px 8px",
            transition: "all 0.15s",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 20, color }}>{SHIP_ICONS[type]}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)" }}>{max} tilgj.</span>
            </div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: active ? color : "var(--text2)", marginBottom: 2 }}>{type}</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)", marginBottom: 8 }}>{SHIP_DESC[type]}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <button onClick={() => onChange(type, Math.max(0, qty - 1))} style={{
                width: 24, height: 24, border: "1px solid var(--border2)", borderRadius: "var(--radius)",
                background: "var(--bg)", color: "var(--text)", cursor: "pointer", fontSize: 14, lineHeight: 1,
              }}>−</button>
              <input
                type="number" min="0" max={max} value={qty}
                onChange={e => onChange(type, Math.min(max, Math.max(0, parseInt(e.target.value) || 0)))}
                style={{ width: 36, textAlign: "center", padding: "2px 4px", fontSize: 12 }}
              />
              <button onClick={() => onChange(type, Math.min(max, qty + 1))} style={{
                width: 24, height: 24, border: "1px solid var(--border2)", borderRadius: "var(--radius)",
                background: "var(--bg)", color: "var(--text)", cursor: "pointer", fontSize: 14, lineHeight: 1,
              }}>+</button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Steg-indikator ────────────────────────────────────────────

function Steps({ current, steps }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 20 }}>
      {steps.map((s, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{
            width: 24, height: 24, borderRadius: "50%",
            background: i < current ? "var(--teal)" : i === current ? "var(--teal-dim)" : "var(--bg3)",
            border: `1px solid ${i <= current ? "var(--teal)" : "var(--border)"}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "var(--mono)", fontSize: 11,
            color: i < current ? "var(--bg)" : i === current ? "var(--teal)" : "var(--text3)",
          }}>
            {i < current ? "✓" : i + 1}
          </div>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: i === current ? "var(--teal)" : "var(--text3)" }}>
            {s}
          </span>
          {i < steps.length - 1 && (
            <div style={{ width: 16, height: 1, background: i < current ? "var(--teal)" : "var(--border)", margin: "0 2px" }} />
          )}
        </div>
      ))}
    </div>
  )
}

// ── Send-flåte wizard ─────────────────────────────────────────

function SendWizard({ myPlanets, allShips, targetPlanets, token, onSent }) {
  const [step, setStep] = useState(0)  // 0=skip, 1=destinasjon, 2=hensikt, 3=bekreft
  const [originId, setOriginId] = useState(myPlanets[0]?.id || "")
  const [selectedShips, setSelectedShips] = useState({})
  const [targetSystemId, setTargetSystemId] = useState("")
  const [targetPlanetId, setTargetPlanetId] = useState("")
  const [missionType, setMissionType] = useState("")
  const [cargo, setCargo] = useState({ metal: 0, energy: 0, gas: 0 })
  const [sending, setSending] = useState(false)
  const [msg, setMsg] = useState("")
  const [err, setErr] = useState("")

  const originPlanet = myPlanets.find(p => p.id === originId)
  const shipsHere = allShips?.locations?.[originId]?.ships || {}
  const totalSelected = Object.values(selectedShips).reduce((a, b) => a + b, 0)
  const fleetClass = classifyFleet(selectedShips)

  // Grupper utforskede systemer
  const systemMap = {}
  targetPlanets.forEach(p => {
    if (!systemMap[p.system_id]) systemMap[p.system_id] = { name: p.system_name, planets: [] }
    systemMap[p.system_id].planets.push(p)
  })

  const targetSystem = systemMap[targetSystemId]
  const planetsInSystem = (targetSystem?.planets || []).filter(p => p.id !== originId)
  const targetPlanet = planetsInSystem.find(p => p.id === targetPlanetId)

  // Beregn reisetid
  const originTP = targetPlanets.find(p => p.id === originId)
  const sameSystem = originTP?.system_id === targetSystemId ||
    myPlanets.find(p => p.id === originId)?.system_id === targetSystemId
  let travelTicks = "?"
  if (targetPlanetId) {
    if (sameSystem) {
      travelTicks = targetPlanet?.travel_ticks || 1
    } else {
      const onlyExp = Object.entries(selectedShips).every(([t, q]) => q === 0 || EXPEDITION_TYPES.has(t))
      const onlyDiplomat = Object.keys(selectedShips).filter(t => selectedShips[t] > 0).join("") === "diplomat"
      travelTicks = onlyDiplomat ? 1 : onlyExp ? 3 : 6
    }
  }

  function updateShip(type, qty) {
    setSelectedShips(prev => ({ ...prev, [type]: qty }))
  }

  function reset() {
    setStep(0); setSelectedShips({}); setTargetSystemId("")
    setTargetPlanetId(""); setMissionType(""); setCargo({ metal: 0, energy: 0, gas: 0 })
    setMsg(""); setErr("")
  }

  async function handleSend() {
    setSending(true); setErr("")
    try {
      const res = await apiFetch("/fleet/send", {
        method: "POST",
        body: JSON.stringify({
          origin_planet_id: originId,
          target_planet_id: targetPlanetId,
          mission_type: missionType,
          ships: selectedShips,
          cargo_metal: cargo.metal,
          cargo_energy: cargo.energy,
          cargo_gas: cargo.gas,
        })
      }, token)
      setMsg(res.message)
      onSent()
      setTimeout(reset, 3000)
    } catch (e) { setErr(e.message) }
    finally { setSending(false) }
  }

  const STEPS = fleetClass === "transport"
    ? ["Skip", "Destinasjon", "Last", "Bekreft"]
    : ["Skip", "Destinasjon", "Hensikt", "Bekreft"]

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <div className="label" style={{ marginBottom: 6 }}>Fra planet</div>
        <select value={originId} onChange={e => { setOriginId(e.target.value); setSelectedShips({}); setStep(0) }}>
          {myPlanets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <Steps current={step} steps={STEPS} />

      {/* Steg 0: Velg skip */}
      {step === 0 && (
        <div>
          <div className="label" style={{ marginBottom: 10 }}>Velg skip å sende</div>
          {Object.keys(shipsHere).length === 0 ? (
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)", padding: 12, background: "var(--bg3)", borderRadius: "var(--radius)" }}>
              Ingen skip på denne planeten
            </div>
          ) : (
            <ShipGrid available={shipsHere} selected={selectedShips} onChange={updateShip} />
          )}
          {totalSelected > 0 && (
            <button className="btn primary" onClick={() => setStep(1)} style={{ width: "100%", marginTop: 14 }}>
              {totalSelected} skip valgt — Velg destinasjon →
            </button>
          )}
        </div>
      )}

      {/* Steg 1: Destinasjon */}
      {step === 1 && (
        <div>
          <div className="label" style={{ marginBottom: 10 }}>Velg system</div>
          {Object.keys(systemMap).length === 0 ? (
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--amber)", padding: "10px 12px", background: "var(--amber-dim)", borderRadius: "var(--radius)", border: "1px solid var(--amber)", marginBottom: 12 }}>
              ◉ Bygg et ekspedisjonsskip for å utforske nabosystemer
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8, marginBottom: 14 }}>
              {Object.entries(systemMap).map(([sid, sys]) => (
                <button key={sid} onClick={() => { setTargetSystemId(sid); setTargetPlanetId("") }} style={{
                  padding: "10px 12px", borderRadius: "var(--radius)", cursor: "pointer", textAlign: "left",
                  border: `1px solid ${targetSystemId === sid ? "var(--teal)" : "var(--border)"}`,
                  background: targetSystemId === sid ? "var(--teal-dim)" : "var(--bg3)",
                  color: targetSystemId === sid ? "var(--teal)" : "var(--text2)",
                  fontFamily: "var(--mono)", fontSize: 12,
                }}>
                  <div style={{ fontSize: 10, color: "var(--text3)", marginBottom: 3 }}>⬡ SYSTEM</div>
                  {sys.name}
                </button>
              ))}
            </div>
          )}

          {targetSystemId && (
            <>
              <div className="label" style={{ marginBottom: 10 }}>Velg planet</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8, marginBottom: 14 }}>
                {planetsInSystem.map(p => (
                  <button key={p.id} onClick={() => setTargetPlanetId(p.id)} style={{
                    padding: "10px 12px", borderRadius: "var(--radius)", cursor: "pointer", textAlign: "left",
                    border: `1px solid ${targetPlanetId === p.id ? "var(--teal)" : "var(--border)"}`,
                    background: targetPlanetId === p.id ? "var(--teal-dim)" : "var(--bg3)",
                    fontFamily: "var(--mono)", fontSize: 12,
                    color: targetPlanetId === p.id ? "var(--teal)" : "var(--text2)",
                  }}>
                    <div style={{ fontSize: 10, color: "var(--text3)", marginBottom: 3 }}>
                      {p.planet_type.toUpperCase()}{p.is_own ? " ★" : ""}
                    </div>
                    {p.name}
                  </button>
                ))}
              </div>
            </>
          )}

          {targetPlanetId && (
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn ghost" onClick={() => setStep(0)} style={{ flex: 1 }}>← Tilbake</button>
              <button className="btn" onClick={() => setStep(2)} style={{ flex: 2 }}>
                Velg {fleetClass === "transport" ? "last" : "hensikt"} →
              </button>
            </div>
          )}
          {!targetPlanetId && (
            <button className="btn ghost" onClick={() => setStep(0)} style={{ width: "100%" }}>← Tilbake</button>
          )}
        </div>
      )}

      {/* Steg 2: Hensikt eller Last */}
      {step === 2 && (
        <div>
          {/* Reisetid-info */}
          <div style={{ fontFamily: "var(--mono)", fontSize: 11, padding: "8px 12px", background: "var(--bg3)", borderRadius: "var(--radius)", marginBottom: 14, display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text2)" }}>Til: {targetPlanet?.name}</span>
            <span style={{ color: "var(--teal)" }}>{travelTicks} tick(s)</span>
          </div>

          {/* Militær: velg angrep / forsvar */}
          {fleetClass === "military" && (
            <div>
              <div className="label" style={{ marginBottom: 12 }}>Hva er oppdraget?</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
                <button onClick={() => setMissionType("attack")} style={{
                  padding: "20px 12px", borderRadius: "var(--radius)", cursor: "pointer",
                  border: `2px solid ${missionType === "attack" ? "var(--red)" : "var(--border)"}`,
                  background: missionType === "attack" ? "var(--red-dim)" : "var(--bg3)",
                  color: missionType === "attack" ? "var(--red)" : "var(--text2)",
                  fontFamily: "var(--mono)", fontSize: 13, textAlign: "center",
                }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>⚔</div>
                  <div style={{ fontWeight: 600 }}>ANGREP</div>
                  <div style={{ fontSize: 10, marginTop: 4, opacity: 0.7 }}>Ta over planeten</div>
                </button>
                <button onClick={() => setMissionType("defend")} style={{
                  padding: "20px 12px", borderRadius: "var(--radius)", cursor: "pointer",
                  border: `2px solid ${missionType === "defend" ? "var(--teal)" : "var(--border)"}`,
                  background: missionType === "defend" ? "var(--teal-dim)" : "var(--bg3)",
                  color: missionType === "defend" ? "var(--teal)" : "var(--text2)",
                  fontFamily: "var(--mono)", fontSize: 13, textAlign: "center",
                }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>🛡</div>
                  <div style={{ fontWeight: 600 }}>FORSVAR</div>
                  <div style={{ fontSize: 10, marginTop: 4, opacity: 0.7 }}>Forsvare planeten</div>
                </button>
              </div>
            </div>
          )}

          {/* Ekspedisjon: ingen valg */}
          {fleetClass === "expedition" && (
            <div style={{ padding: "20px", background: "rgba(192,132,252,0.1)", border: "1px solid #c084fc", borderRadius: "var(--radius)", textAlign: "center", marginBottom: 14 }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>◉</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "#c084fc", marginBottom: 4 }}>EKSPEDISJON</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)" }}>
                Skipene utforsker systemet og returnerer automatisk
              </div>
            </div>
          )}

          {/* Transport: velg last */}
          {fleetClass === "transport" && (
            <div>
              <div className="label" style={{ marginBottom: 12 }}>Velg last</div>
              {[
                { key: "metal", label: "Metall", color: "#7ab8f5", max: originPlanet?.resources?.metal || 0 },
                { key: "energy", label: "Energi", color: "#f0a500", max: originPlanet?.resources?.energy || 0 },
                { key: "gas",   label: "Gass",   color: "#7de88a", max: originPlanet?.resources?.gas || 0 },
              ].map(r => (
                <div key={r.key} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: r.color }}>{r.label}</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)" }}>maks {r.max.toLocaleString()}</span>
                  </div>
                  <input type="number" min="0" max={r.max} value={cargo[r.key]}
                    onChange={e => setCargo(c => ({ ...c, [r.key]: Math.min(r.max, Math.max(0, parseInt(e.target.value) || 0)) }))}
                  />
                </div>
              ))}
              {(() => {
                const maxCargo = (selectedShips["transport"] || 0) * 10000
                const total = cargo.metal + cargo.energy + cargo.gas
                return (
                  <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: total > maxCargo ? "var(--red)" : "var(--text3)", marginBottom: 14 }}>
                    Last: {total.toLocaleString()} / {maxCargo.toLocaleString()}
                    {total > maxCargo && " ⚠ For mye!"}
                  </div>
                )
              })()}
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn ghost" onClick={() => setStep(1)} style={{ flex: 1 }}>← Tilbake</button>
            <button className="btn" onClick={() => {
              if (fleetClass === "expedition") setMissionType("expedition")
              if (fleetClass === "transport") setMissionType("transport")
              setStep(3)
            }}
              disabled={fleetClass === "military" && !missionType}
              style={{ flex: 2 }}>
              Bekreft →
            </button>
          </div>
        </div>
      )}

      {/* Steg 3: Bekreft */}
      {step === 3 && (
        <div>
          <div style={{ background: "var(--bg3)", borderRadius: "var(--radius)", padding: 14, marginBottom: 14 }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)", marginBottom: 10 }}>OPPSUMMERING</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>Fra</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{originPlanet?.name}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>Til</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{targetPlanet?.name}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>Oppdrag</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color:
                missionType === "attack" ? "var(--red)" :
                missionType === "defend" ? "var(--teal)" :
                missionType === "expedition" ? "#c084fc" : "#7de88a"
              }}>{missionType?.toUpperCase()}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>Reisetid</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--amber)" }}>{travelTicks} tick(s)</span>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)", marginBottom: 6 }}>SKIP</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {Object.entries(selectedShips).filter(([, q]) => q > 0).map(([type, qty]) => (
                  <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 12, color: SHIP_COLORS[type] }}>
                    {SHIP_ICONS[type]} {qty}× {type}
                  </span>
                ))}
              </div>
            </div>
            {missionType === "transport" && (cargo.metal + cargo.energy + cargo.gas) > 0 && (
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 10 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)", marginBottom: 6 }}>LAST</div>
                <div style={{ display: "flex", gap: 12, fontFamily: "var(--mono)", fontSize: 12 }}>
                  {cargo.metal > 0 && <span style={{ color: "#7ab8f5" }}>M: {cargo.metal.toLocaleString()}</span>}
                  {cargo.energy > 0 && <span style={{ color: "#f0a500" }}>E: {cargo.energy.toLocaleString()}</span>}
                  {cargo.gas > 0 && <span style={{ color: "#7de88a" }}>G: {cargo.gas.toLocaleString()}</span>}
                </div>
              </div>
            )}
          </div>

          {msg && <div style={{ background: "var(--teal-dim)", border: "1px solid var(--teal)", borderRadius: "var(--radius)", padding: "10px 14px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)", marginBottom: 12 }}>✓ {msg}</div>}
          {err && <div style={{ background: "var(--red-dim)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "10px 14px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--red)", marginBottom: 12 }}>⚠ {err}</div>}

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn ghost" onClick={() => setStep(2)} style={{ flex: 1 }} disabled={sending}>← Tilbake</button>
            <button className="btn primary" onClick={handleSend} disabled={sending} style={{ flex: 2,
              borderColor: missionType === "attack" ? "var(--red)" : "var(--teal)",
              background: missionType === "attack" ? "var(--red-dim)" : "var(--teal-dim)",
              color: missionType === "attack" ? "var(--red)" : "var(--teal)",
            }}>
              {sending ? "Sender..." : `→ Send ${missionType?.toUpperCase()}`}
            </button>
          </div>
          <button className="btn ghost" onClick={reset} style={{ width: "100%", marginTop: 8, fontSize: 11 }}>↺ Start på nytt</button>
        </div>
      )}
    </div>
  )
}

// ── Hovedside ─────────────────────────────────────────────────

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

  async function load() {
    try {
      const [s, m, st, sys, tp] = await Promise.all([
        apiFetch("/fleet/my-ships", {}, token),
        apiFetch("/fleet/my-missions", {}, token),
        apiFetch("/fleet/ship-stats", {}, token),
        apiFetch("/game/my-system", {}, token),
        apiFetch("/game/galaxy/target-planets", {}, token),
      ])
      setShips(s); setMissions(m); setStats(st); setSystem(sys)
      setTargetPlanets(tp.planets || [])
      if (sys?.planets?.length > 0 && !buildForm.planet_id) {
        setBuildForm(f => ({ ...f, planet_id: sys.planets[0].id }))
      }
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token])

  async function handleBuild(e) {
    e.preventDefault(); setBuildErr(""); setBuildMsg("")
    try {
      const res = await apiFetch("/fleet/build", {
        method: "POST",
        body: JSON.stringify({
          planet_id: buildForm.planet_id,
          ship_type: buildForm.ship_type,
          quantity: parseInt(buildForm.quantity),
        })
      }, token)
      setBuildMsg(res.message); load()
    } catch (err) { setBuildErr(err.message) }
  }

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )

  const myPlanets = system?.planets || []

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", letterSpacing: "0.15em", marginBottom: 6 }}>◈ FLÅTEKOMMANDO</div>
        <h1 style={{ fontWeight: 700, fontSize: isMobile ? 20 : 24 }}>Flåte & Skip</h1>
      </div>

      {/* Aktive oppdrag */}
      {missions.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="label" style={{ marginBottom: 14 }}>Aktive oppdrag</div>
          <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
            {missions.map(m => (
              <div key={m.id} style={{
                padding: "10px 12px", borderRadius: "var(--radius)",
                border: `1px solid ${m.type === "attack" ? "rgba(255,68,85,0.3)" : m.type === "expedition" ? "rgba(192,132,252,0.3)" : "var(--border)"}`,
                background: m.type === "attack" ? "var(--red-dim)" : "var(--bg3)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{
                    fontFamily: "var(--mono)", fontSize: 10, padding: "2px 8px",
                    borderRadius: "var(--radius)", border: "1px solid",
                    borderColor: m.type === "attack" ? "var(--red)" : m.type === "expedition" ? "#c084fc" : m.type === "defend" ? "var(--teal)" : "#7de88a",
                    color: m.type === "attack" ? "var(--red)" : m.type === "expedition" ? "#c084fc" : m.type === "defend" ? "var(--teal)" : "#7de88a",
                  }}>{m.type.toUpperCase()}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--amber)" }}>{m.ticks_remaining}t</span>
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)", marginBottom: 6 }}>
                  {m.origin} → {m.target}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {Object.entries(m.ships).map(([type, qty]) => (
                    <span key={type} style={{ fontFamily: "var(--mono)", fontSize: 11, color: SHIP_COLORS[type] }}>
                      {SHIP_ICONS[type]} {qty}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
          {myPlanets.length === 0 ? (
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
              Ingen planeter — venter på spillstart
            </div>
          ) : (
            <SendWizard
              myPlanets={myPlanets}
              allShips={ships}
              targetPlanets={targetPlanets}
              token={token}
              onSent={load}
            />
          )}
        </div>
      </div>

      {/* Mine skip — grid view */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="label" style={{ marginBottom: 14 }}>Mine skip</div>
        {!ships || Object.keys(ships.locations).length === 0 ? (
          <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
            Ingen skip bygget ennå
          </div>
        ) : Object.entries(ships.locations).map(([pid, loc]) => (
          <div key={pid} style={{ marginBottom: 20 }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", marginBottom: 10 }}>
              {loc.system_name ? `${loc.system_name} · ` : ""}{loc.planet_name.toUpperCase()}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 8 }}>
              {Object.entries(loc.ships).map(([type, qty]) => {
                const color = SHIP_COLORS[type] || "var(--teal)"
                return (
                  <div key={type} style={{
                    border: `1px solid ${color}44`, borderRadius: "var(--radius)",
                    background: `${color}0d`, padding: "10px 10px 8px",
                    textAlign: "center",
                  }}>
                    <div style={{ fontSize: 24, color, marginBottom: 4 }}>{SHIP_ICONS[type]}</div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 20, fontWeight: 600, color, marginBottom: 2 }}>{qty}</div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)" }}>{type}</div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
