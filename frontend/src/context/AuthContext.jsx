import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("fp_token"))
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const refreshPromise = useRef(null)

  // Prøv å refreshe access token via httpOnly cookie
  const refresh = useCallback(async () => {
    // Hvis en refresh allerede pågår, vent på den samme
    if (refreshPromise.current) return refreshPromise.current

    refreshPromise.current = (async () => {
      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "include", // sender httpOnly cookie
        })
        if (!res.ok) return null
        const data = await res.json()
        const newToken = data.access_token
        localStorage.setItem("fp_token", newToken)
        setToken(newToken)
        return newToken
      } catch {
        return null
      } finally {
        refreshPromise.current = null
      }
    })()

    return refreshPromise.current
  }, [])

  const fetchMe = useCallback(async (accessToken) => {
    try {
      const res = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: "include",
      })
      if (res.status === 401) {
        // Access token utløpt — prøv refresh
        const newToken = await refresh()
        if (!newToken) { logout(); return }
        const res2 = await fetch("/api/users/me", {
          headers: { Authorization: `Bearer ${newToken}` },
          credentials: "include",
        })
        if (!res2.ok) { logout(); return }
        setUser(await res2.json())
      } else if (!res.ok) {
        logout()
      } else {
        setUser(await res.json())
      }
    } catch {
      logout()
    }
  }, [refresh])

  // Ved oppstart: prøv eksisterende token, eller refresh via cookie
  useEffect(() => {
    async function init() {
      let accessToken = localStorage.getItem("fp_token")
      if (!accessToken) {
        // Ingen token i storage — prøv å refreshe via cookie (persistent session)
        accessToken = await refresh()
      }
      if (accessToken) {
        await fetchMe(accessToken)
      }
      setReady(true)
    }
    init()
  }, [])

  function login(newToken) {
    localStorage.setItem("fp_token", newToken)
    setToken(newToken)
  }

  function logout() {
    localStorage.removeItem("fp_token")
    setToken(null)
    setUser(null)
    // Slett refresh token cookie
    fetch("/api/auth/logout", { method: "POST", credentials: "include" }).catch(() => {})
  }

  // Ikke render barn før vi vet om brukeren er innlogget
  if (!ready) return null

  return (
    <AuthContext.Provider value={{ token, user, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
