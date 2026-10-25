import { beforeEach, expect, it, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock('./api', () => ({ api: { post: mocks.post } }));
import { askValora, parseRecommendations } from './intelligence';

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

it('preserves unavailable confidence and savings as unknown instead of rendering zero claims', () => {
    const [recommendation] = parseRecommendations({
        recommendations: [{
            id: 'overdue_work_order-12',
            title: 'Review overdue work order',
            confidence: 'High',
            confidenceValue: null,
            savingsZar: null,
        }],
    });

    expect(recommendation.confidenceValue).toBeNull();
    expect(recommendation.savingsZar).toBeNull();
});
