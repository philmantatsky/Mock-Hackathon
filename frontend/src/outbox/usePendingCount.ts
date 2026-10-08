import { liveQuery } from 'dexie'
import { useEffect, useState } from 'react'
import { countPending } from './outbox'

/** Live count of visits waiting to sync; updates whenever the outbox changes. */
export function usePendingCount() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const subscription = liveQuery(countPending).subscribe({
      next: setCount,
      // IndexedDB can be unavailable (e.g. some private modes); keep showing 0.
      error: () => {},
    })
    return () => subscription.unsubscribe()
  }, [])

  return count
}
