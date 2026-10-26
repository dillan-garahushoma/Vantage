/** All intelligence requests go through the authenticated estate-scoped API. */
import { api, API_BASE, session } from './api';

export const askValoraPrompts = [
  'What is the status of my maintenance requests?',
  'Are there any published estate notices?',
  'Is a Living Score published for my estate?',
];

export const rolePrompts = {
  hoa_admin: [
    'What is the operational risk summary for this week?',
    'Which work orders are currently overdue?',
    'Summarise open complaints and contractor performance.',
  ],
  resident: [
    'What is the status of my maintenance requests?',
    'How do I report a new maintenance issue?',
    'Are there any published estate notices?',
    'Is a Living Score published for my estate?',
    'When can I expect my repair to be completed?',
  ],
  service_provider: [
    'What work is assigned to my provider account?',
    'Which of my assigned jobs is due soon?',
    'What instructions are recorded for my assigned work?',
  ],
};

export const intelligenceServiceConfigured = true;

export async function askValora(question, context) {
  if (!context.estateId) throw new Error('Select an estate before asking VALORA.');
  const response = await api.post('/api/v1/analytics/intelligence/ask', {
    question,
    estate_id: context.estateId,
  });
  if (!response || typeof response.summary !== 'string' || !response.summary.trim()) {
    throw new Error('Intelligence returned an invalid response. Please try again.');
  }
  return { ...response, evidence: response.evidence ?? [], related: response.related ?? [] };
}

/**
 * Real-time SSE streaming client for Ask VALORA.
 * Connects directly to POST /api/v1/analytics/intelligence/ask/stream with multi-turn history.
 */
export async function streamAskValora(question, context, { onToken, onDone, onError, onMeta }, history = []) {
  if (!context.estateId) {
    const err = new Error('Select an estate before asking VALORA.');
    if (onError) onError(err);
    throw err;
  }

  const token = session.token();
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const cleanHistory = (Array.isArray(history) ? history : [])
      .filter((m) => (m.role === 'user' || m.role === 'assistant') && (m.content || m.text))
      .map((m) => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: String(m.content || m.text || '').trim(),
      }));

    const response = await fetch(`${API_BASE}/api/v1/analytics/intelligence/ask/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        question,
        estate_id: context.estateId,
        history: cleanHistory,
      }),
    });

    if (!response.ok) {
      let msg = `Request failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (typeof errorJson.detail === 'string') {
          msg = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          msg = errorJson.detail.map((d) => d.msg || d.message || JSON.stringify(d)).join('; ');
        } else if (errorJson.detail && typeof errorJson.detail === 'object') {
          msg = errorJson.detail.message || errorJson.detail.code || JSON.stringify(errorJson.detail);
        } else if (errorJson.message) {
          msg = errorJson.message;
        }
      } catch {
        // ignore parse error
      }
      const err = new Error(msg);
      if (onError) onError(err);
      return;
    }

    if (!response.body) {
      const err = new Error('Streaming response body is unavailable.');
      if (onError) onError(err);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;

        const payloadStr = trimmed.replace(/^data:\s*/, '');
        if (payloadStr === '[DONE]') {
          if (onDone) onDone();
          return;
        }

        try {
          const parsed = JSON.parse(payloadStr);
          if (parsed.error) {
            if (onError) onError(new Error(parsed.error));
            return;
          }
          if (parsed.metadata && onMeta) {
            onMeta(parsed.metadata);
          }
          if (parsed.delta && onToken) {
            onToken(parsed.delta);
          }
        } catch {
          // If plain token
          if (onToken) onToken(payloadStr);
        }
      }
    }

    if (onDone) onDone();
  } catch (err) {
    if (onError) onError(err);
  }
}

/* -------------------------------------------- tolerance for live payloads */
function toEvidence(value) {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === 'string') return [{ label: item, detail: '', source: '' }];
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
 */
export function parseRecommendations(payload) {
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.recommendations)
    ? payload.recommendations ?? []
    : [];
  return list.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const row = item;
    if (!row.id || !row.title) return [];
    return [
      {
        id: String(row.id),
        kind: row.kind ?? 'PREVENTIVE MAINTENANCE',
        title: String(row.title),
        summary: String(row.summary ?? ''),
        evidence: toEvidence(row.evidence),
        confidence: row.confidence ?? 'Medium',
        confidenceValue: row.confidenceValue == null ? null : Number(row.confidenceValue),
        impact: String(row.impact ?? ''),
        savingsZar: row.savingsZar == null ? null : Number(row.savingsZar),
        suggestedAction: String(row.suggestedAction ?? ''),
        workOrderDefaults: row.workOrderDefaults ?? { title: String(row.title), priority: 'medium' },
      },
    ];
  });
}
