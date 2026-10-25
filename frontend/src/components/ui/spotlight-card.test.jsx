import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SpotlightCard } from './spotlight-card';

/** jsdom reports every element as a zero-origin box, so pin the card's geometry. */
function pinGeometry(element) {
  element.getBoundingClientRect = () => ({
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 240,
    bottom: 320,
    width: 240,
    height: 320,
    toJSON: () => ({}),
  });
}

describe('SpotlightCard', () => {
  it('renders its own tag and keeps the caller class names', () => {
    render(
      <SpotlightCard as="li" className="rounded-2xl border" aria-label="Complex">
        Ridge Close
      </SpotlightCard>,
    );

    const card = screen.getByRole('listitem', { name: 'Complex' });
    expect(card.tagName).toBe('LI');
    expect(card.className).toContain('spotlight-card');
    expect(card.className).toContain('rounded-2xl');
    expect(card.querySelector('.spotlight-glow')).toHaveAttribute('aria-hidden', 'true');
  });

  it('follows a mouse into the card and dims when it leaves', async () => {
    const user = userEvent.setup();
    render(<SpotlightCard aria-label="Complex">Ridge Close</SpotlightCard>);
    const card = screen.getByLabelText('Complex');
    pinGeometry(card);

    await user.pointer({ target: card, coords: { clientX: 60, clientY: 90 } });
    expect(card.style.getPropertyValue('--spot-x')).toBe('60px');
    expect(card.style.getPropertyValue('--spot-y')).toBe('90px');
    expect(card.dataset.glowing).toBe('true');

    await user.unhover(card);
    expect(card.dataset.glowing).toBe('false');
  });

  it('leaves a touch card alone, so a tap cannot strand the glow', async () => {
    render(<SpotlightCard aria-label="Complex">Ridge Close</SpotlightCard>);
    const card = screen.getByLabelText('Complex');
    pinGeometry(card);

    card.dispatchEvent(
      new PointerEvent('pointermove', { pointerType: 'touch', clientX: 10, clientY: 10, bubbles: true }),
    );

    expect(card.dataset.glowing).toBeUndefined();
    expect(card.style.getPropertyValue('--spot-x')).toBe('');
  });
});
