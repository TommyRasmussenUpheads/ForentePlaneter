import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../api"

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })
      login(data.access_token)
      nav("/dashboard")
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", padding: "20px",
      background: "var(--bg)"
    }}>
      <div style={{ width: "100%", maxWidth: 380 }} className="fade-in">

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{
            fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.3em",
            color: "var(--teal)", textTransform: "uppercase", marginBottom: 8
          }}>
            ◈ Galaktisk Kommando ◈
          </div>
          <h1 style={{
            fontFamily: "var(--sans)", fontWeight: 700, fontSize: 32,
            letterSpacing: "0.05em", color: "var(--text)"
          }}>
            FORENTE<br/>
            <span style={{ color: "var(--teal)" }}>PLANETER</span>
          </h1>
          <div style={{
            width: 60, height: 1, background: "var(--teal)",
            margin: "16px auto 0", opacity: 0.5
          }} />
        </div>

        {/* Form */}
        <div className="card glow" style={{ padding: 28 }}>
          <div className="label" style={{ marginBottom: 20 }}>
            Systemtilgang — Autentisering kreves
          </div>

          {error && (
            <div style={{
              background: "var(--red-dim)", border: "1px solid var(--red)",
              borderRadius: "var(--radius)", padding: "10px 14px",
              color: "var(--red)", fontFamily: "var(--mono)", fontSize: 12,
              marginBottom: 16
            }}>
              ⚠ {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 14 }}>
              <div className="label" style={{ marginBottom: 6 }}>E-post</div>
              <input
                type="email" value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="kommandor@planetsystem.no"
                required
              />
            </div>
            <div style={{ marginBottom: 24 }}>
              <div className="label" style={{ marginBottom: 6 }}>Passord</div>
              <input
                type="password" value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button className="btn" type="submit" disabled={loading}
              style={{ width: "100%", justifyContent: "center", display: "flex", gap: 8, alignItems: "center" }}>
              {loading ? <><div className="spinner" style={{width:14,height:14}} /> Kobler til...</> : "→ Logg inn"}
            </button>
          </form>
        </div>

        <div style={{
          textAlign: "center", marginTop: 20,
          fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)"
        }}>
          Ingen konto?{" "}
          <Link to="/register" style={{ color: "var(--teal)", textDecoration: "none" }}>
            Registrer med invite-kode
          </Link>
        </div>
      </div>
    </div>
  )
}
