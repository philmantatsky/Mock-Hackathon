import { Navigate, Route, Routes } from 'react-router'
import { Header } from './components/Header'
import { LoginPage } from './pages/LoginPage'
import { SignInPage } from './pages/SignInPage'

export default function App() {
  return (
    <>
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/sign-in" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/sign-in" element={<SignInPage />} />
          <Route path="*" element={<Navigate to="/sign-in" replace />} />
        </Routes>
      </main>
    </>
  )
}
