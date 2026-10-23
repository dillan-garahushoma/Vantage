import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';

const directory = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
}));

vi.mock('./lib/publicDirectory', async (loadActual) => ({
  ...(await loadActual()),
  listPublicEstates: directory.list,
  getPublicEstate: directory.get,
}));

const ESTATE = {
  estate_id: 7,
  name: 'Highveld Ridge',
  suburb: 'Waterkloof',
  city: 'Tshwane',
  province: 'Gauteng',
  description: 'A published profile.',
  unit_count: 24,
  cover_photo_public_id: null,
};

function renderRoute(path) {
  directory.list.mockResolvedValue({ items: [ESTATE], total: 1, page: 1, size: 12, pages: 1 });
  directory.get.mockResolvedValue({ ...ESTATE, photos: [], living_score: null });
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

describe('public discovery routes', () => {
  it('renders the published-estates directory through the application router', async () => {
    renderRoute('/estates');
    expect(await screen.findByRole('heading', { name: 'Find a complex' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Highveld Ridge' })).toHaveAttribute('href', '/estates/7');
  });

  it('renders a published estate profile through the application router', async () => {
    renderRoute('/estates/7');
    expect(await screen.findByRole('heading', { name: 'Highveld Ridge' })).toBeVisible();
  });
});
