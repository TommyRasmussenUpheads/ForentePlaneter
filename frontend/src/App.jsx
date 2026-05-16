import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { useEffect } from "react"
import Login from "./pages/Login"
import Register from "./pages/Register"
import Dashboard from "./pages/Dashboard"
import Galaxy from "./pages/Galaxy"
import Fleet from "./pages/Fleet"
import Layout from "./components/Layout"
import { AuthProvider, useAuth } from "./context/AuthContext"
import { ThemeProvider } from "./context/ThemeContext"
import { setRefreshFn } from "./api"

function ProtectedRoute({ children }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return children
}

// Kobler AuthContext sin refresh-funksjon til apiFetch
function RefreshConnector() {
  const { refresh } = useAuth()
  useEffect(() => {
    setRefreshFn(refresh)
  }, [refresh])
  return null
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <RefreshConnector />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="galaxy" element={<Galaxy />} />
              <Route path="fleet" element={<Fleet />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
