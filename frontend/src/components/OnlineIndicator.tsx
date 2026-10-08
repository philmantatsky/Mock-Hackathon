import { useOnlineStatus } from '../hooks/useOnlineStatus'

export function OnlineIndicator() {
  const online = useOnlineStatus()
  return (
    <span className={`status-pill ${online ? 'is-online' : 'is-offline'}`} role="status">
      {online ? 'Online' : 'Offline'}
    </span>
  )
}
