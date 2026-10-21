import { beforeEach, expect, it, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock('./api', () => ({ api: { post: mocks.post } }));
import { askValora } from './intelligence';

beforeEach(() => { mocks.post.mockReset(); });

it('propagates a denied estate without fabricated or external fallback', async () => {
    const denied = new Error('Estate access denied');
    mocks.post.mockRejectedValue(denied);
    const network = vi.spyOn(globalThis, 'fetch');
    await expect(askValora('Why did our score change?', { estateId: 2 })).rejects.toBe(denied);
    expect(network).not.toHaveBeenCalled();
    network.mockRestore();
});

it('requires an estate and uses only the authenticated backend', async () => {
    await expect(askValora('Show records', {})).rejects.toThrow(/estate/i);
    expect(mocks.post).not.toHaveBeenCalled();
});
