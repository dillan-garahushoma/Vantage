/** All intelligence requests go through the authenticated estate-scoped API. */
import { api } from './api';
export const askValoraPrompts = [
    'Why did our estate health score change?',
    'What is likely to need attention next month?',
    'Summarise infrastructure risks for the board.',
];
export const intelligenceServiceConfigured = true;
export async function askValora(question, context) {
    if (!context.estateId) throw new Error('Select an estate before asking VALORA.');
    const response = await api.post('/api/v1/analytics/intelligence/ask', {
        question, estate_id: context.estateId,
    });
    if (!response || typeof response.summary !== 'string' || !response.summary.trim()) {
        throw new Error('Intelligence returned an invalid response. Please try again.');
    }
    return { ...response, evidence: response.evidence ?? [], related: response.related ?? [] };
}
/* -------------------------------------------- tolerance for live payloads */
function toEvidence(value) {
    if (!Array.isArray(value))
        return [];
    return value.flatMap((item) => {
        // A live service may send evidence as plain strings; keep both shapes usable.
        if (typeof item === 'string')
            return [{ label: item, detail: '', source: '' }];
        if (item && typeof item === 'object') {
            const entry = item;
            return [
                {
                    label: String(entry.label ?? entry.title ?? ''),
                    detail: String(entry.detail ?? entry.description ?? ''),
                    source: String(entry.source ?? ''),
                },
            ];
        }
        return [];
    });
}
/**
 * Read a recommendations payload from the intelligence service.
 *
 * Tolerant by design: the service may return evidence as strings or objects, and
 * a finding that does not parse is dropped rather than rendered half-formed.
 */
export function parseRecommendations(payload) {
    const list = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.recommendations)
            ? (payload.recommendations ?? [])
            : [];
    return list.flatMap((item) => {
        if (!item || typeof item !== 'object')
            return [];
        const row = item;
        if (!row.id || !row.title)
            return [];
        return [
            {
                id: String(row.id),
                kind: row.kind ?? 'PREVENTIVE MAINTENANCE',
                title: String(row.title),
                summary: String(row.summary ?? ''),
                evidence: toEvidence(row.evidence),
                confidence: row.confidence ?? 'Medium',
                confidenceValue: Number(row.confidenceValue ?? 0),
                impact: String(row.impact ?? ''),
                savingsZar: Number(row.savingsZar ?? 0),
                suggestedAction: String(row.suggestedAction ?? ''),
                workOrderDefaults: row.workOrderDefaults ?? { title: String(row.title), priority: 'medium' },
            },
        ];
    });
}
