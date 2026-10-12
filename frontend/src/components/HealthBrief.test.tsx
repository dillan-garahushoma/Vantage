/**
 * Health Brief panel — label rules, states, and "format, never compute".
 *
 * The API is mocked: these tests pin exactly what the client is allowed to say
 * and show, and nothing else. Every rule here is a rule from BATCH AI-5, so a
 * regression in wording or state handling fails loudly.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import { generateHealthBrief, readHealthBrief, sendHealthBriefFeedback } from '../lib/ai'
import type { HealthBrief as HealthBriefPayload } from '../lib/ai'
import { HealthBrief } from './HealthBrief'

vi.mock('../lib/ai', () => ({
  readHealthBrief: vi.fn(),
  generateHealthBrief: vi.fn(),
  sendHealthBriefFeedback: vi.fn(),
}))

function brief(overrides: Partial<HealthBriefPayload> = {}): HealthBriefPayload {
  return {
    source: 'ai',
    insight_id: 7,
    ai_unavailable_reason: null,
    data_origin: 'live',
    snapshot_id: 3,
    as_of: '2026-10-01T06:30:00Z',
    generated_at: '2026-10-01T07:00:00Z',
    provider: 'fake',
    model: 'fake-model',
    prompt_version: 'brief-v1',
    facts: {
      engine_version: 'v1',
      as_of: '2026-10-01T06:30:00Z',
      measured_weight: '80',
      window_days: 90,
      compared_days: [30, 90],
      score_min: 0,
      score_max: 100,
      overall: {
        score: '72.5',
        status: 'scored',
        delta_30d: '+1.5',
        delta_30d_abs: '1.0',
        delta_90d: '-4.0',
        delta_90d_abs: '-2.5',
      },
      components: [
        {
          key: 'resolution',
          weight_pct: '35',
          status: 'measured',
          score: '81.2',
          delta_30d: '+2.0',
          delta_30d_abs: '1.4',
          delta_90d: null,
          delta_90d_abs: null,
          inputs: { median_hours: 18, resolved: 12 },
        },
      ],
    },
    output: {
      headline: 'Resolution is strong, security is slipping',
      summary: 'The estate resolves complaints quickly, but perimeter incidents rose.',
      drivers: [{ component: 'security', direction: 'declining', statement: 'Incidents up 3 in 30 days.' }],
      actions: [{ component: 'security', action: 'Ask the guard contractor for a night-shift review.' }],
    },
    ...overrides,
  } as HealthBriefPayload
}

function renderPanel(props: Partial<{ canGenerate: boolean }> = {}) {
  return render(
    <MemoryRouter>
      <HealthBrief estateId={1} canGenerate={props.canGenerate ?? false} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.mocked(readHealthBrief).mockResolvedValue(brief())
  vi.mocked(generateHealthBrief).mockResolvedValue(brief())
  vi.mocked(sendHealthBriefFeedback).mockResolvedValue({
    id: 1,
    insight_id: 7,
    estate_id: 1,
    user_id: 1,
    helpful: true,
    comment: null,
    created_at: null,
  })
})

describe('Health Brief — labels come from API fields', () => {
  it('says an AI brief was written by AI, and shows no AI wording for the template', async () => {
    const { unmount } = renderPanel()
    expect(await screen.findByText('Written by AI from the figures below')).toBeVisible()
    unmount()

    vi.mocked(readHealthBrief).mockResolvedValue(
      brief({ source: 'template', insight_id: null, provider: null, model: null, prompt_version: null }),
    )
    renderPanel()

    expect(await screen.findByText('Automatic summary')).toBeVisible()
    expect(screen.queryByText(/written by ai/i)).toBeNull()
    expect(screen.queryByText(/provider|prompt version|model/i)).toBeNull()
  })

  it('shows a persistent demo badge only for demo data, and always shows as_of', async () => {
    vi.mocked(readHealthBrief).mockResolvedValue(brief({ data_origin: 'demo' }))
    const { unmount } = renderPanel()
    expect(await screen.findByText('Demo data')).toBeVisible()
    expect(screen.getByText(/as at/i)).toBeVisible()
    unmount()

    vi.mocked(readHealthBrief).mockResolvedValue(brief({ data_origin: 'live' }))
    renderPanel()
    expect(await screen.findByText(/as at/i)).toBeVisible()
    expect(screen.queryByText('Demo data')).toBeNull()
  })

  it('renders headline, summary, drivers and actions from the payload', async () => {
    renderPanel()

    expect(await screen.findByText('Resolution is strong, security is slipping')).toBeVisible()
    expect(screen.getByText(/perimeter incidents rose/i)).toBeVisible()
    expect(screen.getByText('Incidents up 3 in 30 days.')).toBeVisible()
    expect(screen.getByText('Declining')).toBeVisible()
    expect(screen.getByText('Ask the guard contractor for a night-shift review.')).toBeVisible()
  })

  it('notes an unavailable AI layer quietly, without an error', async () => {
    vi.mocked(readHealthBrief).mockResolvedValue(
      brief({ source: 'template', insight_id: null, ai_unavailable_reason: 'provider_error' }),
    )
    renderPanel()

    expect(await screen.findByText('Showing the automatic summary.')).toBeVisible()
    expect(screen.queryByText('That request was rejected')).toBeNull()
    expect(screen.queryByText(/provider_error/)).toBeNull()
  })
})

describe('Health Brief — the figures', () => {
  it('shows the facts exactly as returned, including an inconsistent delta', async () => {
    vi.mocked(readHealthBrief).mockResolvedValue(
      brief({
        facts: {
          ...brief().facts,
          overall: {
            score: '72.5',
            status: 'scored',
            delta_30d: '+1.5',
            delta_30d_abs: '9.9',
            delta_90d: null,
            delta_90d_abs: null,
          },
        },
      }),
    )
    const user = userEvent.setup()
    renderPanel()

    const expander = await screen.findByRole('button', { name: /show the figures/i })
    expect(expander).toHaveAttribute('aria-expanded', 'false')
    await user.click(expander)
    expect(expander).toHaveAttribute('aria-expanded', 'true')

    const table = screen.getByRole('table')
    // Both the percentage move and the absolute move are rendered verbatim: the
    // client does not recompute or reconcile them.
    expect(within(table).getByText('+1.5')).toBeVisible()
    expect(within(table).getByText('9.9')).toBeVisible()
    expect(within(table).getByText('72.5')).toBeVisible()
    expect(within(table).getByText('35')).toBeVisible()
    expect(within(table).getByText('81.2')).toBeVisible()
    expect(within(table).getByText(/median_hours/)).toBeVisible()
  })

  it('collapses again when the expander is toggled', async () => {
    const user = userEvent.setup()
    renderPanel()

    const expander = await screen.findByRole('button', { name: /show the figures/i })
    await user.click(expander)
    expect(expander).toHaveAttribute('aria-expanded', 'true')
    await user.click(expander)
    expect(expander).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('table')).toBeNull()
  })
})

describe('Health Brief — generate', () => {
  it('offers the generate button to admins only', async () => {
    const { unmount } = renderPanel({ canGenerate: false })
    await screen.findByText('Written by AI from the figures below')
    expect(screen.queryByRole('button', { name: /generate ai summary/i })).toBeNull()
    unmount()

    renderPanel({ canGenerate: true })
    expect(await screen.findByRole('button', { name: /generate ai summary/i })).toBeEnabled()
  })

  it('disables the button while pending and updates the panel in place', async () => {
    let release: (value: HealthBriefPayload) => void = () => {}
    vi.mocked(generateHealthBrief).mockImplementation(
      () => new Promise((resolve) => { release = resolve }),
    )
    const user = userEvent.setup()
    renderPanel({ canGenerate: true })

    const button = await screen.findByRole('button', { name: /generate ai summary/i })
    await user.click(button)

    expect(button).toBeDisabled()
    expect(generateHealthBrief).toHaveBeenCalledTimes(1)

    release(brief({ output: { headline: 'Fresh AI summary', summary: 'Regenerated.', drivers: [], actions: [] } }))
    expect(await screen.findByText('Fresh AI summary')).toBeVisible()
    await waitFor(() => expect(button).toBeEnabled())
    // No reload of the read endpoint: the response is used as-is.
    expect(readHealthBrief).toHaveBeenCalledTimes(1)
  })

  it('reports a rejected generate request with its reference, without losing the brief', async () => {
    vi.mocked(generateHealthBrief).mockRejectedValue(
      new ApiError(422, 'estate_id must be a valid integer.', 'VALIDATION_ERROR', 'req-422'),
    )
    const user = userEvent.setup()
    renderPanel({ canGenerate: true })
    await screen.findByText('Written by AI from the figures below')

    await user.click(screen.getByRole('button', { name: /generate ai summary/i }))

    expect(await screen.findByText(/must be a valid integer/i)).toBeVisible()
    expect(screen.getByText(/req-422/)).toBeVisible()
    // The brief that was already on screen is untouched.
    expect(screen.getByText('Written by AI from the figures below')).toBeVisible()
  })

  it('keeps the response id for support when generation fails unexpectedly', async () => {
    vi.mocked(generateHealthBrief).mockRejectedValue(
      new ApiError(500, 'An unexpected server error occurred.', 'INTERNAL_ERROR', 'req-gen-1'),
    )
    const user = userEvent.setup()
    renderPanel({ canGenerate: true })

    await user.click(await screen.findByRole('button', { name: /generate ai summary/i }))

    expect(await screen.findByText(/req-gen-1/)).toBeVisible()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('Health Brief — feedback', () => {
  it('offers feedback only for an AI brief and counts the comment', async () => {
    const { unmount } = renderPanel()
    await screen.findByText('Written by AI from the figures below')
    expect(screen.getByRole('button', { name: 'Helpful' })).toBeVisible()
    unmount()

    vi.mocked(readHealthBrief).mockResolvedValue(brief({ source: 'template', insight_id: null }))
    renderPanel()
    await screen.findByText('Automatic summary')
    expect(screen.queryByRole('button', { name: 'Helpful' })).toBeNull()
  })

  it('submits a verdict with an optional comment, capped at 500 characters', async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Helpful' }))
    const comment = screen.getByLabelText(/comment/i)
    expect(comment).toHaveAttribute('maxlength', '500')
    await user.type(comment, 'Useful')
    expect(screen.getByText('6/500')).toBeVisible()

    await user.click(screen.getByRole('button', { name: /send feedback/i }))

    expect(await screen.findByText('0/500')).toBeVisible() // form reset after success
    expect(sendHealthBriefFeedback).toHaveBeenCalledWith(1, 7, { helpful: true, comment: 'Useful' })
  })

  it('reports an already-submitted verdict as such', async () => {
    vi.mocked(sendHealthBriefFeedback).mockRejectedValue(
      new ApiError(409, 'You have already given feedback on this brief.', 'CONFLICT', 'req-409'),
    )
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Not helpful' }))
    await user.click(screen.getByRole('button', { name: /send feedback/i }))

    expect(await screen.findByText('Already submitted')).toBeVisible()
  })
})

describe('Health Brief — states', () => {
  it('shows a loading state, then the brief', async () => {
    renderPanel()
    expect(screen.getByText(/loading/i)).toBeVisible()
    expect(await screen.findByText('Written by AI from the figures below')).toBeVisible()
  })

  it('explains a missing brief instead of showing an error', async () => {
    vi.mocked(readHealthBrief).mockRejectedValue(
      new ApiError(404, 'No Living Score has been calculated for this estate yet.', 'RESOURCE_NOT_FOUND'),
    )
    renderPanel({ canGenerate: true })

    expect(await screen.findByText(/no brief yet/i)).toBeVisible()
    expect(screen.getByText(/no living score has been calculated/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: /try again/i })).toBeNull()
  })

  it('shows a forbidden state without a retry', async () => {
    vi.mocked(readHealthBrief).mockRejectedValue(
      new ApiError(403, 'You are not a member of this estate.', 'FORBIDDEN'),
    )
    renderPanel()

    expect(await screen.findByText(/do not have access/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: /try again/i })).toBeNull()
  })

  it('offers a retry for a network failure and reloads', async () => {
    vi.mocked(readHealthBrief).mockRejectedValueOnce(new ApiError(0, 'Cannot reach the VALORA API.'))
    vi.mocked(readHealthBrief).mockResolvedValueOnce(brief({ output: { headline: 'Second attempt', summary: 'ok', drivers: [], actions: [] } }))
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole('button', { name: /try again/i }))

    expect(await screen.findByText('Second attempt')).toBeVisible()
    expect(readHealthBrief).toHaveBeenCalledTimes(2)
  })
})

describe('Health Brief — keyboard and focus order', () => {
  it('is operable by keyboard, in document order, with a working expander', async () => {
    const user = userEvent.setup()
    renderPanel({ canGenerate: true })
    const generateButton = await screen.findByRole('button', { name: /generate ai summary/i })
    const expander = screen.getByRole('button', { name: /show the figures/i })

    await user.tab()
    expect(generateButton).toHaveFocus()
    await user.tab()
    expect(expander).toHaveFocus()

    // The expander is a real button: Enter and Space both toggle it, and its
    // name and aria-expanded stay in step with what is on screen.
    await user.keyboard('{Enter}')
    expect(expander).toHaveAttribute('aria-expanded', 'true')
    expect(expander).toHaveAccessibleName(/hide the figures/i)
    expect(screen.getByRole('table')).toBeVisible()
    await user.keyboard(' ')
    expect(expander).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('table')).toBeNull()

    await user.tab()
    const helpful = screen.getByRole('button', { name: 'Helpful' })
    expect(helpful).toHaveFocus()
    const notHelpful = screen.getByRole('button', { name: 'Not helpful' })

    // A verdict is given with the keyboard alone, which is what makes the submit
    // button reachable: until then it is disabled and out of the tab order.
    const send = screen.getByRole('button', { name: /send feedback/i })
    expect(send).toBeDisabled()
    await user.keyboard('{Enter}')
    await user.tab()
    expect(notHelpful).toHaveFocus()
    await user.tab()
    expect(screen.getByLabelText(/comment/i)).toHaveFocus()
    await user.tab()
    expect(send).toBeEnabled()
    expect(send).toHaveFocus()

    await user.keyboard('{Enter}')
    expect(sendHealthBriefFeedback).toHaveBeenCalledWith(1, 7, { helpful: true, comment: null })
    expect(await screen.findByText(/thanks/i)).toBeVisible()
  })
})
