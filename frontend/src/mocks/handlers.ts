import { http, HttpResponse } from 'msw'
import type { components } from '../api/schema'

type Schemas = components['schemas']

// `*` matches any origin, so handlers work whatever VITE_API_URL is.
export const handlers = [
  http.get<never, never, Schemas['Health']>('*/api/health', () =>
    HttpResponse.json({ status: 'ok' }),
  ),

  http.get<never, never, Schemas['Location'][]>('*/api/locations', () =>
    HttpResponse.json([
      { id: 'loc-1', name: 'Eastside Community Pantry', address: '120 Main St' },
      { id: 'loc-2', name: 'Riverside Church Pantry', address: null },
    ]),
  ),

  http.post<never, Schemas['SyncRequest'], Schemas['SyncResponse']>(
    '*/api/sync',
    async ({ request }) => {
      const { visits } = await request.json()
      return HttpResponse.json({
        results: visits.map((visit) => ({ id: visit.id, status: 'created' as const })),
      })
    },
  ),
]
