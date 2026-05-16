import { useState } from "react"
import { Outlet, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useTheme } from "../context/ThemeContext"
import { useIsMobile } from "../hooks/useMediaQuery"
import { apiFetch } from "../api"

function AdminPanel({ token }) {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState("")
  const [err, setErr] = useState("")
  const [days, setDays] = useState(30)
  const [showReset, setShowReset] = useState(false)

  async function handleStart() {
    setLoading(true); setMsg(""); setErr("")
    try {
      const res = await apiFetch("/game/start", {
        method: "POST",
        body: JSON.stringify({ duration_days: parseInt(days) })
      }, token)
      setMsg(`✓ ${res.message}`)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function handleTick() {
    setLoading(true); setMsg(""); setErr("")
    try {
      const res = await apiFetch("/game/tick", { method: "POST" }, token)
      setMsg(`✓ ${res.message}`)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function handleReset() {
    setLoading(true); setMsg(""); setErr("")
    try {
      const res = await apiFetch("/game/reset", { method: "POST" }, token)
      setMsg(`✓ ${res.message}`)
      setShowReset(false)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div style={{
      margin: "12px 0", padding: "12px",
      background: "var(--amber-dim)", border: "1px solid var(--amber)",
      borderRadius: "var(--radius)",
    }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--amber)", letterSpacing: "0.1em", marginBottom: 10 }}>⚙ ADMIN</div>
      {msg && <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", marginBottom: 8 }}>{msg}</div>}
      {err && <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--red)", marginBottom: 8 }}>⚠ {err}</div>}
      <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
        <input type="number" min="1" max="90" value={days}
          onChange={e => setDays(e.target.value)}
          style={{ width: 46, padding: "4px 6px", fontSize: 11 }} title="Antall dager" />
        <button className="btn amber" onClick={handleStart} disabled={loading}
          style={{ flex: 1, fontSize: 11, padding: "5px 8px" }}>▶ Start</button>
      </div>
      <button className="btn ghost" onClick={handleTick} disabled={loading}
        style={{ width: "100%", fontSize: 11, padding: "5px 8px", marginBottom: 6 }}>⏱ Kjør tick</button>
      {!showReset ? (
        <button className="btn ghost" onClick={() => setShowReset(true)}
          style={{ width: "100%", fontSize: 11, padding: "5px 8px" }}>↺ Reset spill</button>
      ) : (
        <div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--red)", marginBottom: 6 }}>Er du sikker? All data slettes!</div>
          <div style={{ display: "flex", gap: 4 }}>
            <button className="btn danger" onClick={handleReset} disabled={loading}
              style={{ flex: 1, fontSize: 11, padding: "5px 8px" }}>Ja</button>
            <button className="btn ghost" onClick={() => setShowReset(false)}
              style={{ flex: 1, fontSize: 11, padding: "5px 8px" }}>Nei</button>
          </div>
        </div>
      )}
    </div>
  )
}

function NavContent({ user, token, dark, toggle, onLogout, onNav, isAdmin }) {
  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: "⬡" },
    { to: "/galaxy",    label: "Galakse",   icon: "✦" },
    { to: "/fleet",     label: "Flåte",     icon: "▲" },
  ]
  return (
    <>
      {user && (
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)", marginBottom: 4 }}>KOMMANDØR</div>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--teal)" }}>{user.username}</div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)", marginTop: 2 }}>{user.honor_rank}</div>
        </div>
      )}
      <div style={{ flex: 1, padding: "12px 0", overflowY: "auto" }}>
        {navItems.map(item => (
          <NavLink key={item.to} to={item.to} onClick={onNav} style={({ isActive }) => ({
            display: "flex", alignItems: "center", gap: 10,
            padding: "12px 20px", textDecoration: "none",
            fontFamily: "var(--sans)", fontWeight: 600,
            fontSize: 14, letterSpacing: "0.08em",
            color: isActive ? "var(--teal)" : "var(--text2)",
            background: isActive ? "var(--teal-dim)" : "transparent",
            borderLeft: isActive ? "2px solid var(--teal)" : "2px solid transparent",
            transition: "all 0.15s",
          })}>
            <span style={{ fontSize: 18 }}>{item.icon}</span>
            {item.label.toUpperCase()}
          </NavLink>
        ))}
        {isAdmin && (
          <div style={{ padding: "0 12px", marginTop: 8 }}>
            <AdminPanel token={token} />
          </div>
        )}
      </div>
      <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 8 }}>
        <button onClick={toggle} style={{
          width: "100%", padding: "8px 12px", borderRadius: "var(--radius)",
          border: "1px solid var(--border2)", background: "var(--bg3)",
          color: "var(--text2)", cursor: "pointer",
          fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.05em",
          display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          transition: "all 0.15s",
        }}>
          {dark ? "☀ Lyst tema" : "☾ Mørkt tema"}
        </button>
        <button className="btn ghost" onClick={onLogout} style={{ width: "100%", fontSize: 11 }}>← Logg ut</button>
      </div>
    </>
  )
}

export default function Layout() {
  const { user, logout, token } = useAuth()
  const { dark, toggle } = useTheme()
  const nav = useNavigate()
  const isMobile = useIsMobile()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() { logout(); nav("/login") }
  const isAdmin = ["admin", "superadmin", "elder_race"].includes(user?.role)

  return (
    <div style={{ display: "flex", minHeight: "100vh", position: "relative" }}>

      {/* ── Desktop sidebar ── */}
      {!isMobile && (
        <nav style={{
          width: 210, background: "var(--bg2)",
          borderRight: "1px solid var(--border)",
          display: "flex", flexDirection: "column",
          padding: "20px 0", flexShrink: 0,
          boxShadow: "var(--shadow)",
        }}>
          <div style={{ padding: "0 20px 24px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.2em", color: "var(--teal)", marginBottom: 4 }}>◈ FORENTE</div>
            <div style={{ fontFamily: "var(--sans)", fontWeight: 700, fontSize: 18, letterSpacing: "0.05em" }}>PLANETER</div>
          </div>
          <NavContent user={user} token={token} dark={dark} toggle={toggle}
            onLogout={handleLogout} onNav={() => {}} isAdmin={isAdmin} />
        </nav>
      )}

      {/* ── Mobile topbar ── */}
      {isMobile && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
          background: "var(--bg2)", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 16px", height: 52, boxShadow: "var(--shadow)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--teal)" }}>◈</span>
            <span style={{ fontFamily: "var(--sans)", fontWeight: 700, fontSize: 16 }}>FORENTE PLANETER</span>
          </div>
          <button onClick={() => setMenuOpen(o => !o)} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--text)", fontSize: 22, padding: "8px 4px", lineHeight: 1
          }}>
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      )}

      {/* ── Mobile drawer ── */}
      {isMobile && menuOpen && (
        <>
          {/* Backdrop */}
          <div onClick={() => setMenuOpen(false)} style={{
            position: "fixed", inset: 0, zIndex: 210,
            background: "rgba(0,0,0,0.4)"
          }} />
          {/* Drawer */}
          <nav style={{
            position: "fixed", top: 52, left: 0, bottom: 0, width: 260,
            zIndex: 220, background: "var(--bg2)",
            borderRight: "1px solid var(--border)",
            display: "flex", flexDirection: "column",
            overflowY: "auto",
            boxShadow: "4px 0 20px rgba(0,0,0,0.15)",
            animation: "slideIn 0.2s ease"
          }}>
            <NavContent user={user} token={token} dark={dark} toggle={toggle}
              onLogout={handleLogout} onNav={() => setMenuOpen(false)} isAdmin={isAdmin} />
          </nav>
        </>
      )}

      {/* ── Main content ── */}
      <main style={{
        flex: 1, overflow: "auto",
        padding: isMobile ? "68px 12px 20px" : "24px",
        background: "var(--bg)",
        minWidth: 0,
      }}>
        <Outlet />
      </main>

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(-100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
