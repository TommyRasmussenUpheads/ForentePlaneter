import { useState, useEffect, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { useIsMobile } from "../hooks/useMediaQuery"
import { apiFetch } from "../api"

function hexToPixel(q, r, size, cx, cy) {
  return {
    x: cx + size * (3 / 2 * q),
    y: cy + size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r)
  }
}

export default function Galaxy() {
  const { token } = useAuth()
  const isMobile = useIsMobile()
  const canvasRef = useRef(null)
  const [systems, setSystems] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch("/game/galaxy", {}, token)
      .then(d => { setSystems(d.systems); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  useEffect(() => {
    if (!systems.length || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    const W = canvas.width
    const H = canvas.height
    const cx = W / 2
    const cy = H / 2
    const size = isMobile ? 24 : 36

    ctx.clearRect(0, 0, W, H)

    // Bakgrunnsstjerner
    const rng = (() => {
      let s = 42
      return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 4294967296 }
    })()
    for (let i = 0; i < 150; i++) {
      ctx.beginPath()
      ctx.arc(rng() * W, rng() * H, rng() * 0.8 + 0.2, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255,255,255,${rng() * 0.3 + 0.05})`
      ctx.fill()
    }

    // Tegn ruter mellom nabosystemer
    const drawnRoutes = new Set()
    systems.forEach(sys => {
      const posA = hexToPixel(sys.hex_q, sys.hex_r, size, cx, cy)
      if (!sys.neighbors) return
      sys.neighbors.forEach(neighborId => {
        const neighbor = systems.find(s => s.id === neighborId)
        if (!neighbor) return
        const routeKey = [sys.id, neighbor.id].sort().join("-")
        if (drawnRoutes.has(routeKey)) return
        drawnRoutes.add(routeKey)
        const posB = hexToPixel(neighbor.hex_q, neighbor.hex_r, size, cx, cy)
        ctx.beginPath()
        ctx.moveTo(posA.x, posA.y)
        ctx.lineTo(posB.x, posB.y)
        ctx.strokeStyle = "rgba(100,150,200,0.15)"
        ctx.lineWidth = 1
        ctx.stroke()
      })
    })

    // Tegn systemer
    systems.forEach(sys => {
      const pos = hexToPixel(sys.hex_q, sys.hex_r, size, cx, cy)
      if (pos.x < -50 || pos.x > W + 50 || pos.y < -50 || pos.y > H + 50) return

      const isSelected = selected?.id === sys.id
      let color, r

      if (sys.is_elder_race)       { color = "#f0e68c"; r = 10 }
      else if (sys.is_unknown_region) { color = "#ff4455"; r = 8 }
      else if (sys.is_npc)         { color = "#3a5a7a"; r = 6 }
      else                         { color = "#00e5cc"; r = 10 }

      // Glow
      const grd = ctx.createRadialGradient(pos.x, pos.y, r * 0.2, pos.x, pos.y, r * 3)
      grd.addColorStop(0, color + "44")
      grd.addColorStop(1, color + "00")
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, r * 3, 0, Math.PI * 2)
      ctx.fillStyle = grd
      ctx.fill()

      // Planet
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()

      // Utvalgt ring
      if (isSelected) {
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, r + 5, 0, Math.PI * 2)
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      // Navn
      ctx.font = `${isMobile ? 9 : 10}px 'Share Tech Mono', monospace`
      ctx.fillStyle = sys.is_npc ? "#3a5a7a" : "#c8deff"
      ctx.textAlign = "center"
      const name = sys.name.length > 18 ? sys.name.substring(0, 16) + "…" : sys.name
      ctx.fillText(name, pos.x, pos.y + r + 14)
    })
  }, [systems, selected, isMobile])

  function handleClick(e) {
    if (!canvasRef.current || !systems.length) return
    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = canvasRef.current.width / rect.width
    const scaleY = canvasRef.current.height / rect.height
    const mx = (e.clientX - rect.left) * scaleX
    const my = (e.clientY - rect.top) * scaleY
    const W = canvasRef.current.width
    const H = canvasRef.current.height
    const cx = W / 2
    const cy = H / 2
    const size = isMobile ? 24 : 36

    for (const sys of systems) {
      const pos = hexToPixel(sys.hex_q, sys.hex_r, size, cx, cy)
      const r = sys.is_elder_race ? 10 : sys.is_npc ? 6 : 10
      if (Math.hypot(mx - pos.x, my - pos.y) <= r + 8) {
        setSelected(sys)
        return
      }
    }
    setSelected(null)
  }

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )

  if (!systems.length) return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: 14, color: "var(--text2)", marginBottom: 12 }}>
        ◌ Ingen systemer å vise
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
        Bygg et ekspedisjonsskip for å avsløre nabosystemene dine, eller vent på spillstart.
      </div>
    </div>
  )

  const playerSystems = systems.filter(s => !s.is_npc && !s.is_elder_race && !s.is_unknown_region)
  const npcSystems    = systems.filter(s => s.is_npc && !s.is_unknown_region)

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", letterSpacing: "0.15em", marginBottom: 6 }}>
          ◈ GALAKTISK OVERSIKT
        </div>
        <h1 style={{ fontWeight: 700, fontSize: isMobile ? 20 : 24 }}>Galaksekart</h1>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: isMobile ? "1fr" : "1fr 240px",
        gap: 16,
      }}>
        {/* Kart */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <canvas
            ref={canvasRef}
            width={isMobile ? 380 : 700}
            height={isMobile ? 340 : 500}
            style={{ width: "100%", cursor: "crosshair", display: "block" }}
            onClick={handleClick}
          />
        </div>

        {/* Sidepanel */}
        <div>
          {/* Forklaring */}
          <div className="card" style={{ marginBottom: 14 }}>
            <div className="label" style={{ marginBottom: 12 }}>Forklaring</div>
            {[
              { color: "#00e5cc", label: "Ditt system" },
              { color: "#3a5a7a", label: "NPC-system" },
              { color: "#ff4455", label: "Unknown Regions" },
              { color: "#f0e68c", label: "Elder Race" },
            ].map(l => (
              <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: l.color, flexShrink: 0 }} />
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>{l.label}</span>
              </div>
            ))}
          </div>

          {/* Statistikk */}
          <div className="card" style={{ marginBottom: 14 }}>
            <div className="label" style={{ marginBottom: 10 }}>Utforsket</div>
            {[
              { label: "Totalt sett",     value: systems.length },
              { label: "Spillersystemer", value: playerSystems.length },
              { label: "NPC-systemer",    value: npcSystems.length },
            ].map(s => (
              <div key={s.label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>{s.label}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)" }}>{s.value}</span>
              </div>
            ))}
            {systems.length <= 1 && (
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--amber)", marginTop: 8, padding: "6px 10px", background: "var(--amber-dim)", borderRadius: "var(--radius)" }}>
                Bygg et ekspedisjonsskip for å se nabosystemene!
              </div>
            )}
          </div>

          {/* Valgt system */}
          {selected && (
            <div className="card glow fade-in">
              <div className="label" style={{ marginBottom: 10 }}>Valgt system</div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{selected.name}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)" }}>
                <div>Koordinater: ({selected.hex_q}, {selected.hex_r})</div>
                <div style={{
                  marginTop: 4,
                  color: selected.is_elder_race ? "#f0e68c"
                       : selected.is_unknown_region ? "var(--red)"
                       : selected.is_npc ? "var(--text3)"
                       : "var(--teal)"
                }}>
                  {selected.is_elder_race ? "Elder Race"
                   : selected.is_unknown_region ? "Unknown Regions"
                   : selected.is_npc ? "NPC-system"
                   : "Spillersystem"}
                </div>
                {selected.owner_id && (
                  <div style={{ marginTop: 4, color: "var(--teal)" }}>Kontrollert</div>
                )}
                {selected.neighbors && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ color: "var(--text3)", marginBottom: 4 }}>
                      {selected.neighbors.length} nabosystem(er)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
