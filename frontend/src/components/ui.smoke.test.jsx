/**
 * Toolchain smoke test: proves the Vitest runner, the jsdom environment, React 19
 * rendering and the jest-dom matchers are wired together before anyone relies on
 * them.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Chip } from './ui';
describe('test toolchain', () => {
    it('renders a component into jsdom with jest-dom matchers available', () => {
        render(<Chip tone="warn" glyph="↑">High</Chip>);
        const chip = screen.getByText('High');
        expect(chip).toBeInTheDocument();
        expect(chip).toHaveClass('inline-flex');
        expect(chip.tagName).toBe('SPAN');
    });
});
