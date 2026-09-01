import { Route, Routes } from 'react-router-dom'
import { AnalyzePage } from './pages/AnalyzePage'
import { LandingPage } from './pages/LandingPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/analyze" element={<AnalyzePage />} />
    </Routes>
  )
}

export default App
