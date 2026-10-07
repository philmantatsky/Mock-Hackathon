import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach } from 'vitest'
import { server } from '../mocks/server'

// Listen at import time, not in beforeAll: openapi-fetch captures
// globalThis.fetch when client.ts is first imported, so MSW must have
// patched fetch before any test file loads the client.
server.listen({ onUnhandledRequest: 'error' })

afterEach(() => {
  cleanup()
  server.resetHandlers()
})

afterAll(() => server.close())
