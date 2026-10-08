import Dexie, { type EntityTable } from 'dexie'
import type { components } from '../api/schema'

/** A visit waiting to be uploaded; exactly the contract's VisitIn shape. */
export type QueuedVisit = components['schemas']['VisitIn']

export const db = new Dexie('pantry-sign-in') as Dexie & {
  outbox: EntityTable<QueuedVisit, 'id'>
}

db.version(1).stores({
  outbox: 'id, visited_at',
})
