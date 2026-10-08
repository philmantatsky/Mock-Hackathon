import { describe, expect, it } from 'vitest'
import { normalizePhone, visitorSchema } from './visitSchema'

const valid = { phone: '3125550100', first_initial: 'k', birth_month: '2', birth_day: '29' }

function errorsFor(input: Partial<typeof valid>) {
  const result = visitorSchema.safeParse({ ...valid, ...input })
  return result.success ? {} : Object.fromEntries(result.error.issues.map((i) => [i.path[0], i.message]))
}

describe('normalizePhone', () => {
  it.each([
    ['(312) 555-0100', '3125550100'],
    ['312.555.0100', '3125550100'],
    ['1 312 555 0100', '3125550100'],
    ['+44 20 7946 0958', '+442079460958'],
  ])('%s -> %s', (raw, expected) => {
    expect(normalizePhone(raw)).toBe(expected)
  })
})

describe('visitorSchema', () => {
  it('normalizes a valid visitor into the contract shape', () => {
    expect(visitorSchema.parse({ ...valid, phone: ' (312) 555-0100 ' })).toEqual({
      phone: '3125550100',
      first_initial: 'K',
      birth_month: 2,
      birth_day: 29,
    })
  })

  it.each(['', '555-0100', '312555010', '31255501000', '+1234', 'call me'])(
    'rejects phone %j',
    (phone) => {
      expect(errorsFor({ phone })).toHaveProperty('phone')
    },
  )

  it('accepts an international number with +', () => {
    expect(errorsFor({ phone: '+44 20 7946 0958' })).toEqual({})
  })

  it.each(['', 'ab', '1', '-'])('rejects first initial %j', (first_initial) => {
    expect(errorsFor({ first_initial })).toHaveProperty('first_initial', 'Enter one letter')
  })

  it('requires month and day', () => {
    expect(errorsFor({ birth_month: '', birth_day: '' })).toEqual({
      birth_month: 'Choose a month',
      birth_day: 'Choose a day',
    })
  })

  it('rejects days that do not exist in the month', () => {
    expect(errorsFor({ birth_month: '2', birth_day: '30' })).toEqual({
      birth_day: 'February has only 29 days',
    })
    expect(errorsFor({ birth_month: '4', birth_day: '31' })).toEqual({
      birth_day: 'April has only 30 days',
    })
    expect(errorsFor({ birth_month: '12', birth_day: '31' })).toEqual({})
  })
})
