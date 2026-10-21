import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
/** jsdom does not unmount between tests; Testing Library's own cleanup does it. */
afterEach(() => {
    cleanup();
});
