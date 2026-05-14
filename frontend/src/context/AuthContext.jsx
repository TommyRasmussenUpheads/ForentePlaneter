import { createContext, useContext, useState, useEffect } from "react"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("fp_token"))
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (token) fetchMe()
  }, [token])

  async function fetchMe() {
    try {
      const res = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) { logout(); return }
      setUser(await res.json())
    } catch { logout() }
  }

  function login(newToken) {
    localStorage.setItem("fp_token", newToken)
    setToken(newToken)
  }

  function logout() {
    localStorage.removeItem("fp_token")
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
