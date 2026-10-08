import { db, type QueuedVisit } from './db'

export type NewVisit = Omit<QueuedVisit, 'id' | 'visited_at'>

// crypto.randomUUID only exists in secure contexts (https, localhost). Fall back
// so testing on a phone over the LAN (http://192.168...) still works.
function newVisitId(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/** Save a visit on the device. Never touches the network; sync uploads it later. */
export async function enqueueVisit(visit: NewVisit): Promise<QueuedVisit> {
  const queued: QueuedVisit = {
    ...visit,
    id: newVisitId(),
    visited_at: new Date().toISOString(),
  }
  await db.outbox.add(queued)
  return queued
}

export function countPending() {
  return db.outbox.count()
}
