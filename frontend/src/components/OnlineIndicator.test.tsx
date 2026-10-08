import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OnlineIndicator } from './OnlineIndicator'

function goOffline(offline: boolean) {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(!offline)
  act(() => {
    window.dispatchEvent(new Event(offline ? 'offline' : 'online'))
  })
}

describe('OnlineIndicator', () => {
  afterEach(() => vi.restoreAllMocks())

  it('flips between Online and Offline on browser events', () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
    render(<OnlineIndicator />)
    expect(screen.getByRole('status')).toHaveTextContent('Online')

    goOffline(true)
    expect(screen.getByRole('status')).toHaveTextContent('Offline')

    goOffline(false)
    expect(screen.getByRole('status')).toHaveTextContent('Online')
  })
})
