import { z } from 'zod'
import type { components } from '../../api/schema'

// Privacy: a visitor is only phone, first initial, and birth month/day.
// Never add name or email fields here.

/** Strip formatting; drop a leading US country code "1" on 11-digit numbers. */
export function normalizePhone(raw: string) {
  const cleaned = raw.replace(/[\s().-]/g, '')
  return /^1\d{10}$/.test(cleaned) ? cleaned.slice(1) : cleaned
}

const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] // Feb allows 29

export const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

const selectNumber = (message: string, max: number) =>
  z
    .string()
    .regex(/^\d{1,2}$/, message)
    .transform(Number)
    .pipe(z.number().int().min(1, message).max(max, message))

export const visitorSchema = z
  .object({
    phone: z
      .string()
      .trim()
      .min(1, 'Enter a phone number')
      .transform(normalizePhone)
      .refine((v) => /^\d{10}$/.test(v) || /^\+\d{10,15}$/.test(v), {
        message: 'Enter a 10-digit phone number, or + and the country code',
      }),
    first_initial: z
      .string()
      .trim()
      .regex(/^[A-Za-z]$/, 'Enter one letter')
      .transform((v) => v.toUpperCase()),
    birth_month: selectNumber('Choose a month', 12),
    birth_day: selectNumber('Choose a day', 31),
  })
  .superRefine((v, ctx) => {
    const max = DAYS_IN_MONTH[v.birth_month - 1]
    if (v.birth_day > max) {
      ctx.addIssue({
        code: 'custom',
        path: ['birth_day'],
        message: `${MONTH_NAMES[v.birth_month - 1]} has only ${max} days`,
      })
    }
  })

/** What the form fields hold (strings from inputs and selects). */
export type VisitorFormValues = z.input<typeof visitorSchema>
/** Validated, normalized visitor details. */
export type VisitorDetails = z.output<typeof visitorSchema>

// Compile-time guard: the form's output must match the API contract's VisitIn
// fields. If the backend renames or retypes one, this line stops compiling.
type VisitIn = components['schemas']['VisitIn']
true satisfies VisitorDetails extends Pick<VisitIn, keyof VisitorDetails> ? true : false
