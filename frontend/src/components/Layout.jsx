import { Outlet, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useTheme } from "../context/ThemeContext"

export default function Layout() {
  const { user, logout } = useAuth()
  const { dark, toggle } = useTheme()
  const nav = useNavigate()

  function handleLogout() { logout(); nav("/login") }

  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: "⬡" },
    { to: "/galaxy",    label: "Galakse",   icon: "✦" },
    { to: "/fleet",     label: "Flåte",     icon: "▲" },
  ]

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Sidebar */}
      <nav style={{
        width: 200, background: "var(--bg2)",
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
        <div style={{ flex: 1, padding: "12px 0" }}>
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

      {/* Main content */}
      <main style={{ flex: 1, overflow: "auto", padding: 24, background: "var(--bg)" }}>
        <Outlet />
      </main>
    </div>
  )
}
