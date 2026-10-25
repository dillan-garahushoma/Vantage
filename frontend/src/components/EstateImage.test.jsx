import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { EstateImage } from './EstateImage';

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('../lib/api', () => ({ api: { get }, API_BASE: 'http://localhost:8000', ApiError: class extends Error {} }));
beforeEach(() => { get.mockReset(); });

it('uses the selected estate authorised photo metadata', async () => {
  get.mockResolvedValue([{ public_id: 'uploaded-cover', caption: 'Courtyard' }]);
  render(<EstateImage estate={{ estate_id: 9, estate_name: 'Test complex' }} />);
  expect(await screen.findByAltText('Courtyard — Test complex')).toHaveAttribute('src', expect.stringContaining('/public/photos/uploaded-cover'));
  expect(get).toHaveBeenCalledWith('/api/v1/estates/photos', { estate_id: 9 });
});

it('shows an honest empty state without stock property photography', async () => {
  get.mockResolvedValue([]);
  const { container } = render(<EstateImage estate={{ estate_id: 9, estate_name: 'Test complex' }} />);
  expect(await screen.findByText('Estate photo not added yet')).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
});

it('clears the previous estate photograph immediately when switching estates', async () => {
  get.mockResolvedValueOnce([{ public_id: 'estate-one', caption: 'First photo' }]);
  const { rerender } = render(<EstateImage estate={{ estate_id: 1, estate_name: 'First estate' }} />);
  await screen.findByAltText('First photo — First estate');
  get.mockReturnValue(new Promise(() => {}));
  rerender(<EstateImage estate={{ estate_id: 2, estate_name: 'Second estate' }} />);
  await waitFor(() => expect(screen.queryByAltText('First photo — First estate')).not.toBeInTheDocument());
  expect(screen.getByRole('status')).toHaveTextContent('Loading estate photo');
});
