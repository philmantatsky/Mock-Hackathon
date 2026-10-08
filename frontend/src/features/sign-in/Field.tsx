import type { ReactNode } from 'react'

type Props = {
  id: string
  label: string
  hint?: string
  error?: string
  children: ReactNode
}

/** Label + control + hint/error. The control must set aria-describedby={`${id}-msg`}. */
export function Field({ id, label, hint, error, children }: Props) {
  return (
    <div className={`field ${error ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      <p id={`${id}-msg`} className={error ? 'field-error' : 'field-hint'}>
        {error ?? hint}
      </p>
    </div>
  )
}
