import { useEffect, useState } from 'react'
import { client } from '../api/client'

type Health = 'checking' | 'ok' | 'unreachable'

const labels: Record<Health, string> = {
  checking: 'Checking API…',
  ok: 'API ok',
  unreachable: 'API unreachable',
}

export function HealthCheck() {
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    let cancelled = false
    // Patchy wifi can leave a request hanging; treat a slow API as unreachable.
    client
      .GET('/api/health', { signal: AbortSignal.timeout(5000) })
      .then(({ response }) => !cancelled && setHealth(response.ok ? 'ok' : 'unreachable'))
      .catch(() => !cancelled && setHealth('unreachable'))
    return () => {
      cancelled = true
    }
  }, [])

  return <span className={`health health-${health}`}>{labels[health]}</span>
}
