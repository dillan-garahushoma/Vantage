import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { ProviderApply } from './ProviderApply';

const mocks = vi.hoisted(() => ({ list: vi.fn(), apply: vi.fn() }));
vi.mock('../lib/publicDirectory', () => ({ listPublicEstates: mocks.list }));
vi.mock('../lib/api', async (original) => ({
  ...await original(), api: { applyAsProvider: mocks.apply },
}));

beforeEach(() => {
  mocks.list.mockReset();
  mocks.apply.mockReset();
});

it('loads estates within the API limit and lets a provider apply to a later page', async () => {
  mocks.list.mockImplementation(async ({ page, page_size }) => {
    if (page_size > 50) throw new ApiError(422, 'Page size must be at most 50.');
    return { items: [{ estate_id: page, name: `Complex ${page}`, suburb: 'Musgrave', city: 'Durban' }], pages: 2 };
  });
  mocks.apply.mockResolvedValue({});
  const user = userEvent.setup();
  render(<MemoryRouter><ProviderApply /></MemoryRouter>);
  await screen.findByRole('option', { name: /Complex 2/ });
  await user.selectOptions(screen.getByRole('combobox', { name: /^Estate/ }), '2');
  await user.type(screen.getByLabelText('Full name'), 'QA Provider');
  await user.type(screen.getByLabelText('Email address'), 'provider@example.com');
  await user.type(screen.getByLabelText('Trade'), 'Plumbing');
  await user.type(screen.getByLabelText('Phone'), '0820000000');
  await user.click(screen.getByRole('button', { name: 'Submit application' }));
  expect(await screen.findByRole('heading', { name: 'Application sent' })).toBeVisible();
  expect(mocks.apply).toHaveBeenCalledWith(expect.objectContaining({ estate_id: 2, trade: 'Plumbing' }));
  expect(screen.getByRole('status')).toHaveTextContent('No account has been created yet');
});
