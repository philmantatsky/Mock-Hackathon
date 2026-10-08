import { SignInForm } from '../features/sign-in/SignInForm'
import type { VisitorDetails } from '../features/sign-in/visitSchema'
import { enqueueVisit } from '../outbox/outbox'

// Placeholder until the location picker ticket; matches the first mock location.
const CURRENT_LOCATION_ID = 'loc-1'

async function saveVisit(details: VisitorDetails) {
  await enqueueVisit({ ...details, location_id: CURRENT_LOCATION_ID })
}

export function SignInPage() {
  return (
    <section>
      <h1>Sign in a visitor</h1>
      <SignInForm onSubmit={saveVisit} />
    </section>
  )
}
