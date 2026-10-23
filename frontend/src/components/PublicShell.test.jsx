import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { PublicShell } from './PublicShell';

describe('PublicShell navigation', () => {
  it('provides a visible Home action to return to the website landing page', () => {
    render(
      <MemoryRouter initialEntries={['/estates']}>
        <PublicShell><h1>Find a complex</h1></PublicShell>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login');
    expect(screen.getByRole('link', { name: /create account/i })).toHaveAttribute('href', '/register');
  });
});
