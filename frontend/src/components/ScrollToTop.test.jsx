import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { ScrollToTop } from './ScrollToTop';

beforeEach(() => {
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
  document.documentElement.style.scrollBehavior = '';
});

describe('ScrollToTop', () => {
  it('resets the document position when the route pathname changes', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/first']}>
        <ScrollToTop />
        <nav>
          <Link to="/second">Open second page</Link>
        </nav>
        <Routes>
          <Route path="/first" element={<h1>First page</h1>} />
          <Route path="/second" element={<h1>Second page</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    document.documentElement.scrollTop = 780;
    document.body.scrollTop = 780;
    await user.click(screen.getByRole('link', { name: /open second page/i }));

    expect(await screen.findByRole('heading', { name: /second page/i })).toBeVisible();
    await waitFor(() => {
      expect(document.documentElement.scrollTop).toBe(0);
      expect(document.body.scrollTop).toBe(0);
    });
  });

  it('restores the prior scroll-behavior style after resetting', () => {
    document.documentElement.style.scrollBehavior = 'smooth';
    render(
      <MemoryRouter initialEntries={['/first']}>
        <ScrollToTop />
        <Routes>
          <Route path="/first" element={<h1>First page</h1>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(document.documentElement.style.scrollBehavior).toBe('smooth');
  });
});
