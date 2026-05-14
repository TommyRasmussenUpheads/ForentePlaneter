import { useState } from "react"
import { useNavigate, Link, useSearchParams } from "react-router-dom"
import { apiFetch } from "../api"

export default function Register() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({
    username: "", email: "", password: "",
    invite_token: params.get("invite") || ""
  })
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)

  function update(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      })
      setSuccess(data.message)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (success) return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", padding: 20
    }}>
      <div style={{ maxWidth: 380, textAlign: "center" }} className="fade-in">
        <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
        <h2 style={{ color: "var(--teal)", marginBottom: 12 }}>Konto opprettet!</h2>
        <p style={{ color: "var(--text2)", fontFamily: "var(--mono)", fontSize: 13, marginBottom: 24 }}>
          {success}
        </p>
        <Link to="/login" className="btn" style={{ textDecoration: "none", display: "inline-block" }}>
          → Gå til innlogging
        </Link>
      </div>
    </div>
  )

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", padding: 20,
      background: "var(--bg)"
    }}>
      <div style={{ width: "100%", maxWidth: 400 }} className="fade-in">
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.3em",
            color: "var(--teal)", textTransform: "uppercase", marginBottom: 8
          }}>◈ Ny Kommandør ◈</div>
          <h1 style={{ fontFamily: "var(--sans)", fontWeight: 700, fontSize: 28 }}>
            REGISTRER DEG
          </h1>
        </div>

        <div className="card glow" style={{ padding: 28 }}>
          {error && (
            <div style={{
              background: "var(--red-dim)", border: "1px solid var(--red)",
              borderRadius: "var(--radius)", padding: "10px 14px",
              color: "var(--red)", fontFamily: "var(--mono)", fontSize: 12, marginBottom: 16
            }}>⚠ {error}</div>
          )}

          <form onSubmit={handleSubmit}>
            {[
              { key: "invite_token", label: "Invite-kode", type: "text", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" },
              { key: "username", label: "Kommandørnavn", type: "text", placeholder: "StarLord" },
              { key: "email", label: "E-post", type: "email", placeholder: "din@epost.no" },
              { key: "password", label: "Passord", type: "password", placeholder: "min. 8 tegn" },
            ].map(f => (
              <div key={f.key} style={{ marginBottom: 14 }}>
                <div className="label" style={{ marginBottom: 6 }}>{f.label}</div>
                <input
                  type={f.type} value={form[f.key]} placeholder={f.placeholder}
                  onChange={e => update(f.key, e.target.value)} required
                />
              </div>
            ))}
            <button className="btn" type="submit" disabled={loading}
              style={{ width: "100%", display: "flex", justifyContent: "center", gap: 8, alignItems: "center", marginTop: 8 }}>
              {loading ? <><div className="spinner" style={{width:14,height:14}} /> Registrerer...</> : "→ Opprett konto"}
            </button>
          </form>
        </div>

        <div style={{
          textAlign: "center", marginTop: 20,
          fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)"
        }}>
          Har du konto?{" "}
          <Link to="/login" style={{ color: "var(--teal)", textDecoration: "none" }}>Logg inn</Link>
        </div>
      </div>
    </div>
  )
}
