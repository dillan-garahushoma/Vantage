import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { TopBar } from './TopBar';

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: { role: 'hoa_admin', full_name: 'Test administrator' } }) }));
function Location() { return <output aria-label="Current route">{useLocation().pathname}</output>; }

it('lets a keyboard user activate a workspace search result', async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><TopBar /><Location /></MemoryRouter>);
  await user.type(screen.getByRole('textbox', { name: 'Search the estate workspace' }), 'work orders');
  await user.tab();
  await user.keyboard('{Enter}');
  expect(screen.getByLabelText('Current route')).toHaveTextContent('/app/work-orders');
});
