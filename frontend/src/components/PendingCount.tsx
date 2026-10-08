import { usePendingCount } from '../outbox/usePendingCount'

export function PendingCount() {
  const count = usePendingCount()
  return <span>Pending: {count}</span>
}
