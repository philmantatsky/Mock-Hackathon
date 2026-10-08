import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SignInForm } from './SignInForm'

function setup(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  const user = userEvent.setup()
  render(<SignInForm onSubmit={onSubmit} />)
  const fields = {
    phone: screen.getByLabelText('Phone number'),
    initial: screen.getByLabelText('First initial'),
    month: screen.getByLabelText('Month'),
    day: screen.getByLabelText('Day'),
    submit: screen.getByRole('button', { name: 'Sign in visitor' }),
  }
  return { user, onSubmit, ...fields }
}

describe('SignInForm', () => {
  it('submits normalized details, then resets for the next visitor', async () => {
    const { user, onSubmit, phone, initial, month, day, submit } = setup()

    await user.type(phone, '(312) 555-0100')
    await user.type(initial, 'k')
    await user.selectOptions(month, 'February')
    await user.selectOptions(day, '29')
    await user.click(submit)

    expect(onSubmit).toHaveBeenCalledWith({
      phone: '3125550100',
      first_initial: 'K',
      birth_month: 2,
      birth_day: 29,
    })
    expect(await screen.findByText(/Signed in/)).toBeInTheDocument()
    expect(phone).toHaveValue('')
    expect(month).toHaveValue('')
    expect(phone).toHaveFocus()
  })

  it('shows errors and does not submit when fields are empty', async () => {
    const { user, onSubmit, phone, submit } = setup()

    await user.click(submit)

    expect(onSubmit).not.toHaveBeenCalled()
    expect(await screen.findByText('Enter a phone number')).toBeInTheDocument()
    expect(screen.getByText('Enter one letter')).toBeInTheDocument()
    expect(screen.getByText('Choose a month')).toBeInTheDocument()
    expect(phone).toHaveAttribute('aria-invalid', 'true')
  })

  it('rejects a day that does not exist in the chosen month', async () => {
    const { user, onSubmit, phone, initial, month, day, submit } = setup()

    await user.type(phone, '3125550100')
    await user.type(initial, 'k')
    await user.selectOptions(month, 'February')
    await user.selectOptions(day, '30')
    await user.click(submit)

    expect(onSubmit).not.toHaveBeenCalled()
    expect(await screen.findByText('February has only 29 days')).toBeInTheDocument()
  })

  it('keeps the values and shows an error when saving fails', async () => {
    const { user, phone, initial, month, day, submit } = setup(
      vi.fn().mockRejectedValue(new Error('IndexedDB unavailable')),
    )

    await user.type(phone, '3125550100')
    await user.type(initial, 'k')
    await user.selectOptions(month, 'March')
    await user.selectOptions(day, '3')
    await user.click(submit)

    expect(await screen.findByText(/Couldn't save/)).toBeInTheDocument()
    expect(phone).toHaveValue('3125550100')
  })

  it('never asks for a name or email (privacy rule)', () => {
    const { container } = render(<SignInForm onSubmit={vi.fn()} />)
    const controls = container.querySelectorAll('input, select, textarea')
    for (const el of controls) {
      const described = `${el.getAttribute('name')} ${el.id} ${el.getAttribute('type')}`
      expect(described).not.toMatch(/name|email/i)
    }
  })
})
