import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Field } from './Field'
import {
  MONTH_NAMES,
  visitorSchema,
  type VisitorDetails,
  type VisitorFormValues,
} from './visitSchema'

type Props = {
  /** Called with validated details. Storage is the caller's job. */
  onSubmit: (details: VisitorDetails) => Promise<void>
}

const EMPTY: VisitorFormValues = { phone: '', first_initial: '', birth_month: '', birth_day: '' }
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1))

export function SignInForm({ onSubmit }: Props) {
  const [result, setResult] = useState<'saved' | 'failed' | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<VisitorFormValues, unknown, VisitorDetails>({
    resolver: zodResolver(visitorSchema),
    defaultValues: EMPTY,
    mode: 'onTouched',
  })

  const submit = handleSubmit(async (details) => {
    try {
      await onSubmit(details)
      reset(EMPTY)
      setResult('saved')
    } catch {
      setResult('failed') // keep the values so the volunteer can retry
    }
  })

  // Focus after the submit cycle finishes; setFocus inside the handler is a no-op.
  useEffect(() => {
    if (result === 'saved') setFocus('phone') // ready for the next visitor
  }, [result, setFocus])

  const a11y =(id: keyof VisitorFormValues) => ({
    id,
    'aria-invalid': errors[id] ? true : undefined,
    'aria-describedby': `${id}-msg`,
  })

  return (
    // autoComplete off: shared device, don't suggest the last visitor's details.
    // onInput: clear the last result once the volunteer starts the next visitor.
    <form
      className="sign-in-form"
      onSubmit={submit}
      onInput={() => setResult(null)}
      noValidate
      autoComplete="off"
    >
      <Field id="phone" label="Phone number" hint="Digits only is fine" error={errors.phone?.message}>
        <input type="tel" inputMode="tel" autoComplete="off" {...a11y('phone')} {...register('phone')} />
      </Field>

      <Field id="first_initial" label="First initial" error={errors.first_initial?.message}>
        <input
          type="text"
          maxLength={1}
          autoCapitalize="characters"
          autoComplete="off"
          className="input-initial"
          {...a11y('first_initial')}
          {...register('first_initial')}
        />
      </Field>

      <fieldset className="birthday">
        <legend>Birthday</legend>
        <Field id="birth_month" label="Month" error={errors.birth_month?.message}>
          <select {...a11y('birth_month')} {...register('birth_month')}>
            <option value="">Month</option>
            {MONTH_NAMES.map((name, i) => (
              <option key={name} value={String(i + 1)}>
                {name}
              </option>
            ))}
          </select>
        </Field>
        <Field id="birth_day" label="Day" error={errors.birth_day?.message}>
          <select {...a11y('birth_day')} {...register('birth_day')}>
            <option value="">Day</option>
            {DAYS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
      </fieldset>

      <button type="submit" className="btn-primary" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : 'Sign in visitor'}
      </button>

      <p className={`form-result ${result ?? ''}`} aria-live="polite">
        {result === 'saved' && '✓ Signed in. Ready for the next visitor.'}
        {result === 'failed' && "Couldn't save on this device. Try again."}
      </p>
    </form>
  )
}
