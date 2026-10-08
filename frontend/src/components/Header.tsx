import { NavLink } from 'react-router'
import { HealthCheck } from './HealthCheck'
import { OnlineIndicator } from './OnlineIndicator'
import { PendingCount } from './PendingCount'

export function Header() {
  return (
    <header className="app-header">
      <div className="app-header-row">
        <span className="app-title">Pantry Sign-In</span>
        <OnlineIndicator />
      </div>
      <div className="app-header-row app-header-meta">
        <PendingCount />
        <HealthCheck />
      </div>
      <nav className="app-nav">
        <NavLink to="/sign-in">Sign in visitor</NavLink>
        <NavLink to="/login">Volunteer login</NavLink>
      </nav>
    </header>
  )
}
