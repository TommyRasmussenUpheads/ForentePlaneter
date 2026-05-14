import { useState, useEffect, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../api"

function hexToPixel(q, r, size, cx, cy) {
  return {
    x: cx + size * (3 / 2 * q),
    y: cy + size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r)
  }
}

export default function Galaxy() {
  const { token } = useAuth()
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
    const W = canvas.width, H = canvas.height
    const cx = W / 2, cy = H / 2
    const size = 36

    ctx.clearRect(0, 0, W, H)

    // Background stars
    const rng = (() => { let s = 42; return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 4294967296 } })()
    for (let i = 0; i < 150; i++) {
      ctx.beginPath()
      ctx.arc(rng() * W, rng() * H, rng() * 0.8 + 0.2, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255,255,255,${rng() * 0.3 + 0.05})`
      ctx.fill()
    }

    // Draw systems
    systems.forEach(sys => {
      const pos = hexToPixel(sys.hex_q, sys.hex_r, size, cx, cy)
      if (pos.x < -50 || pos.x > W + 50 || pos.y < -50 || pos.y > H + 50) return

      const isSelected = selected?.id === sys.id
      let color, r

      if (sys.is_elder_race) { color = "#f0e68c"; r = 10 }
      else if (sys.is_unknown_region) { color = "#ff4455"; r = 8 }
      else if (sys.is_npc) { color = "#3a5a7a"; r = 6 }
      else { color = "#00e5cc"; r = 10 }

      // Glow
      const grd = ctx.createRadialGradient(pos.x, pos.y, r * 0.2, pos.x, pos.y, r * 3)
      grd.addColorStop(0, color + "44")
      grd.addColorStop(1, color + "00")
      ctx.beginPath(); ctx.arc(pos.x, pos.y, r * 3, 0, Math.PI * 2)
      ctx.fillStyle = grd; ctx.fill()

      // Planet circle
      ctx.beginPath(); ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2)
      ctx.fillStyle = color; ctx.fill()

      if (isSelected) {
        ctx.beginPath(); ctx.arc(pos.x, pos.y, r + 5, 0, Math.PI * 2)
        ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke()
      }

      // Label
      ctx.font = "10px 'Share Tech Mono', monospace"
      ctx.fillStyle = sys.is_npc ? "#3a5a7a" : "#c8deff"
      ctx.textAlign = "center"
      const name = sys.name.length > 18 ? sys.name.substring(0, 16) + "…" : sys.name
      ctx.fillText(name, pos.x, pos.y + r + 14)
    })
  }, [systems, selected])

  function handleClick(e) {
    if (!canvasRef.current || !systems.length) return
    const rect = canvasRef.current.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvasRef.current.width, H = canvasRef.current.height
    const cx = W / 2, cy = H / 2
    const size = 36

    for (const sys of systems) {
      const pos = hexToPixel(sys.hex_q, sys.hex_r, size, cx, cy)
      const r = sys.is_elder_race ? 10 : sys.is_npc ? 6 : 10
      if (Math.hypot(mx - pos.x, my - pos.y) <= r + 8) {
        setSelected(sys); return
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
    <div style={{ padding: 40, textAlign: "center", fontFamily: "var(--mono)", color: "var(--text3)" }}>
      Galaksen er ikke generert ennå — venter på spillstart
    </div>
  )

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", letterSpacing: "0.15em", marginBottom: 6 }}>
          ◈ GALAKTISK OVERSIKT
        </div>
        <h1 style={{ fontWeight: 700, fontSize: 24 }}>Galaksekart</h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 16 }}>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <canvas
            ref={canvasRef} width={700} height={500}
            style={{ width: "100%", cursor: "crosshair", display: "block" }}
            onClick={handleClick}
          />
        </div>

        <div>
          {/* Legend */}
          <div className="card" style={{ marginBottom: 14 }}>
            <div className="label" style={{ marginBottom: 12 }}>Forklaring</div>
            {[
              { color: "#00e5cc", label: "Spillersystem" },
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

          {/* Stats */}
          <div className="card" style={{ marginBottom: 14 }}>
            <div className="label" style={{ marginBottom: 10 }}>Statistikk</div>
            {[
              { label: "Totale systemer", value: systems.length },
              { label: "Spillersystemer", value: systems.filter(s => !s.is_npc && !s.is_elder_race).length },
              { label: "NPC-systemer", value: systems.filter(s => s.is_npc && !s.is_unknown_region).length },
            ].map(s => (
              <div key={s.label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text2)" }}>{s.label}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--teal)" }}>{s.value}</span>
              </div>
            ))}
          </div>

          {/* Selected system info */}
          {selected && (
            <div className="card glow fade-in">
              <div className="label" style={{ marginBottom: 10 }}>Valgt system</div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{selected.name}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)" }}>
                <div>Koordinater: ({selected.hex_q}, {selected.hex_r})</div>
                <div style={{ marginTop: 4, color: selected.is_elder_race ? "#f0e68c" : selected.is_unknown_region ? "var(--red)" : selected.is_npc ? "var(--text3)" : "var(--teal)" }}>
                  {selected.is_elder_race ? "Elder Race" : selected.is_unknown_region ? "Unknown Regions" : selected.is_npc ? "NPC-system" : "Spillersystem"}
                </div>
                {selected.owner_id && (
                  <div style={{ marginTop: 4, color: "var(--teal)" }}>Kontrollert</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
