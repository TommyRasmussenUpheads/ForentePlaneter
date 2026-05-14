import { useState } from "react"
import { Outlet, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useTheme } from "../context/ThemeContext"
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

  async function handleReset() {
    setLoading(true); setMsg(""); setErr("")
    try {
      const res = await apiFetch("/game/reset", { method: "POST" }, token)
      setMsg(`✓ ${res.message}`)
      setShowReset(false)
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

  return (
    <div style={{
      margin: "12px 0",
      padding: "12px",
      background: "var(--amber-dim)",
      border: "1px solid var(--amber)",
      borderRadius: "var(--radius)",
    }}>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 10,
        color: "var(--amber)", letterSpacing: "0.1em", marginBottom: 10
      }}>⚙ ADMIN</div>

      {msg && <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--teal)", marginBottom: 8 }}>{msg}</div>}
      {err && <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--red)", marginBottom: 8 }}>⚠ {err}</div>}

      {/* Start game */}
      <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
        <input
          type="number" min="1" max="90" value={days}
          onChange={e => setDays(e.target.value)}
          style={{ width: 46, padding: "4px 6px", fontSize: 11 }}
          title="Antall dager"
        />
        <button
          className="btn amber"
          onClick={handleStart}
          disabled={loading}
          style={{ flex: 1, fontSize: 11, padding: "5px 8px" }}
        >▶ Start</button>
      </div>

      {/* Tick */}
      <button
        className="btn ghost"
        onClick={handleTick}
        disabled={loading}
        style={{ width: "100%", fontSize: 11, padding: "5px 8px", marginBottom: 6 }}
      >⏱ Kjør tick</button>

      {/* Reset */}
      {!showReset ? (
        <button
          className="btn ghost"
          onClick={() => setShowReset(true)}
          style={{ width: "100%", fontSize: 11, padding: "5px 8px" }}
        >↺ Reset spill</button>
      ) : (
        <div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--red)", marginBottom: 6 }}>
            Er du sikker? All data slettes!
          </div>
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

export default function Layout() {
  const { user, logout, token } = useAuth()
  const { dark, toggle } = useTheme()
  const nav = useNavigate()

  function handleLogout() { logout(); nav("/login") }

  const isAdmin = user?.role === "admin" || user?.role === "superadmin"

  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: "⬡" },
    { to: "/galaxy",    label: "Galakse",   icon: "✦" },
    { to: "/fleet",     label: "Flåte",     icon: "▲" },
  ]

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav style={{
        width: 210, background: "var(--bg2)",
        borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column",
        padding: "20px 0", flexShrink: 0,
        boxShadow: "var(--shadow)",
      }}>
        {/* Logo */}
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid var(--border)" }}>
          <div style={{
            fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.2em",
            color: "var(--teal)", marginBottom: 4
          }}>◈ FORENTE</div>
          <div style={{
            fontFamily: "var(--sans)", fontWeight: 700, fontSize: 18,
            letterSpacing: "0.05em", color: "var(--text)"
          }}>PLANETER</div>
        </div>

        {/* Player info */}
        {user && (
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text3)", marginBottom: 4 }}>
              KOMMANDØR
            </div>
            <div style={{ fontWeight: 600, fontSize: 14, color: "var(--teal)" }}>
              {user.username}
            </div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
              {user.honor_rank}
            </div>
          </div>
        )}

        {/* Nav links */}
        <div style={{ flex: 1, padding: "12px 0", overflowY: "auto" }}>
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} style={({ isActive }) => ({
              display: "flex", alignItems: "center", gap: 10,
              padding: "10px 20px", textDecoration: "none",
              fontFamily: "var(--sans)", fontWeight: 600,
              fontSize: 13, letterSpacing: "0.08em",
              color: isActive ? "var(--teal)" : "var(--text2)",
              background: isActive ? "var(--teal-dim)" : "transparent",
              borderLeft: isActive ? "2px solid var(--teal)" : "2px solid transparent",
              transition: "all 0.15s",
            })}>
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label.toUpperCase()}
            </NavLink>
          ))}

          {/* Admin panel */}
          {isAdmin && (
            <div style={{ padding: "0 12px", marginTop: 8 }}>
              <AdminPanel token={token} />
            </div>
          )}
        </div>

        {/* Theme toggle + logout */}
        <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            onClick={toggle}
            style={{
              width: "100%", padding: "7px 12px",
              borderRadius: "var(--radius)",
              border: "1px solid var(--border2)",
              background: "var(--bg3)",
              color: "var(--text2)",
              cursor: "pointer",
              fontFamily: "var(--mono)", fontSize: 11,
              letterSpacing: "0.05em",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              transition: "all 0.15s",
            }}
          >
            {dark ? "☀ Lyst tema" : "☾ Mørkt tema"}
          </button>
          <button className="btn ghost" onClick={handleLogout}
            style={{ width: "100%", fontSize: 11 }}>
            ← Logg ut
          </button>
        </div>
      </nav>

      <main style={{ flex: 1, overflow: "auto", padding: 24, background: "var(--bg)" }}>
        <Outlet />
      </main>
    </div>
  )
}
