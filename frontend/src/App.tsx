// src/App.tsx
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import IncidentPage from './pages/IncidentPage'
import Layout from './components/Layout'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"            element={<Dashboard />} />
        <Route path="/incidents/:id" element={<IncidentPage />} />
      </Routes>
    </Layout>
  )
}
