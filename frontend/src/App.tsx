import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import WorldBuilding from './pages/WorldBuilding'
import Characters from './pages/Characters'
import Outline from './pages/Outline'
import Writing from './pages/Writing'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="world" element={<WorldBuilding />} />
        <Route path="characters" element={<Characters />} />
        <Route path="outline" element={<Outline />} />
        <Route path="writing" element={<Writing />} />
      </Route>
    </Routes>
  )
}

export default App
