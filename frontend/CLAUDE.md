# Frontend: Pantry Sign-In PWA

Offline-first PWA (Vite + React + TypeScript) that volunteers use on phones to sign in pantry visitors at sites with patchy wifi. Backend is FastAPI in `../backend`, owned by a teammate; `../openapi.json` is the API contract.

## Checks (run all before committing)

```
npm run lint
npm run typecheck
npm test
npm run build
```

Other scripts: `npm run dev`, `npm run preview`, `npm run gen:api`, `npm run gen:icons`.

## Rules

- **Privacy:** never store, collect, or log a visitor's name or email. Visitors are identified only by phone number, first initial, and birth month/day. This applies to forms, IndexedDB, console logs, mocks, and test fixtures.
- **Must work offline.** Every screen must load and work with no network. Never make a user action depend on a request succeeding.
- **Form submits write to the Dexie outbox first. Never call `/api/sync` from a component.** Only the sync module talks to `/api/sync`.
- **Never hand-edit `src/api/schema.d.ts`.** Run `npm run gen:api` after `../openapi.json` changes.
- Call the API only through `src/api/client.ts` (typed `openapi-fetch` client).
- Only edit files in `frontend/`. Don't edit `../openapi.json` or `../backend/` without the backend owner.
- Never create or read real `.env` files; document variables in `.env.example`.
- Keep `package.json` scripts cross-platform (team is on Windows and Mac): `&&` is fine (works in cmd and sh), but no `rm`/`cp`, globs that need a shell, or inline `VAR=x`.
- No UI library; plain CSS in `src/index.css`. Keep components small.

## Mocks

Copy `.env.example` to `.env.local` to run with `VITE_USE_MOCKS=true`; MSW then serves the handlers in `src/mocks/handlers.ts` (typed from the generated schema). Tests use the same handlers via `msw/node`.

Gotcha: `openapi-fetch` captures `globalThis.fetch` when the client is created, so `src/test/setup.ts` calls `server.listen()` at import time, not in `beforeAll`.

## PWA

`vite-plugin-pwa` (Workbox `generateSW`) precaches the app shell; navigations fall back to `/index.html`. `/api/` requests are never cached. The service worker is disabled in dev; test offline behavior with `npm run build` then `npm run preview`.
