import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { server } from '../mocks/server'
import { client, setAuthToken } from './client'

describe('api client', () => {
  afterEach(() => setAuthToken(null))

  it('calls the health endpoint through the typed client', async () => {
    const { data, response } = await client.GET('/api/health')
    expect(response.status).toBe(200)
    expect(data).toEqual({ status: 'ok' })
  })

  it('adds a Bearer header only when a token is set', async () => {
    const seen: (string | null)[] = []
    server.use(
      http.get('*/api/health', ({ request }) => {
        seen.push(request.headers.get('Authorization'))
        return HttpResponse.json({ status: 'ok' })
      }),
    )

    await client.GET('/api/health')
    setAuthToken('test-token')
    await client.GET('/api/health')

    expect(seen).toEqual([null, 'Bearer test-token'])
  })
})
