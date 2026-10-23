import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AskValoraSpotlight } from './AskValoraSpotlight';

const mocks = vi.hoisted(() => ({ stream: vi.fn() }));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'hoa_admin' } }),
}));
vi.mock('../../context/EstateContext', () => ({
  useEstateScope: () => ({ estateId: 9, estate: { is_estate_admin: true } }),
}));
vi.mock('../../lib/intelligence', () => ({
  rolePrompts: { hoa_admin: ['Which work orders are currently overdue?'], resident: [], service_provider: [] },
  streamAskValora: mocks.stream,
}));

describe('AskValoraSpotlight', () => {
  it('renders streamed markdown as reading structure and restores the input when complete', async () => {
    let callbacks;
    mocks.stream.mockImplementation((_, __, next) => {
      callbacks = next;
    });
    const user = userEvent.setup();
    render(<AskValoraSpotlight open onOpenChange={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await user.type(input, 'What needs attention?');
    await user.click(screen.getByRole('button', { name: /^ask$/i }));
    expect(input).toBeDisabled();
    callbacks.onToken('## Immediate action\n\n- Review gate repair');
    callbacks.onDone();
    expect(await screen.findByRole('heading', { name: 'Immediate action' })).toBeVisible();
    expect(input).not.toBeDisabled();
  });

  it('shows a streaming failure and lets the person try again', async () => {
    let callbacks;
    mocks.stream.mockImplementation((_, __, next) => {
      callbacks = next;
    });
    const user = userEvent.setup();
    render(<AskValoraSpotlight open onOpenChange={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await user.type(input, 'What needs attention?');
    await user.click(screen.getByRole('button', { name: /^ask$/i }));
    callbacks.onError(new Error('The intelligence service is unavailable.'));
    expect(await screen.findByText('The intelligence service is unavailable.')).toBeVisible();
    expect(input).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeEnabled();
  });

  it('renders contextual follow-up chips when streaming is complete and clicking one submits it', async () => {
    let callbacks;
    mocks.stream.mockImplementation((_, __, next) => {
      callbacks = next;
    });
    const user = userEvent.setup();
    render(<AskValoraSpotlight open onOpenChange={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await user.type(input, 'Summarise open issues');
    await user.click(screen.getByRole('button', { name: /^ask$/i }));
    callbacks.onToken('Three open complaints are driving the health score drop.');
    callbacks.onDone();

    expect(await screen.findByText('Three open complaints are driving the health score drop.')).toBeVisible();
    const followUpBtn = await screen.findByRole('button', { name: /Which open issues are driving this\?/i });
    expect(followUpBtn).toBeVisible();

    await user.click(followUpBtn);
    expect(mocks.stream).toHaveBeenCalledWith(
      'Which open issues are driving this?',
      expect.objectContaining({ estateId: 9, role: 'hoa_admin' }),
      expect.any(Object)
    );
  });
});
