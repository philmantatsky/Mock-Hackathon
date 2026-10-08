import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

export function getAuthToken() {
  return authToken
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    if (authToken) {
      request.headers.set('Authorization', `Bearer ${authToken}`)
    }
    return request
  },
}

export const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL,
})

client.use(authMiddleware)
