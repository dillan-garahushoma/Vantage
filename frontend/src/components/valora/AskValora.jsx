import { FileText, Link2, ListChecks, Maximize2, Minimize2, Send, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { useEstateScope } from '../../context/EstateContext';
import { askValora, askValoraPrompts, intelligenceServiceConfigured } from '../../lib/intelligence';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

function AnalysingState() {
  return (
    <div
      className="flex items-center gap-3 rounded-2xl border border-line bg-canvas px-4 py-3.5"
      role="status"
      aria-live="polite"
    >
      <svg viewBox="0 0 120 24" className="h-6 w-[120px]" aria-hidden="true">
        <path
          d="M0 12 h18 l5 -8 l6 16 l6 -12 l5 6 h14 l5 -9 l6 17 l5 -8 h22"
          fill="none"
          stroke="currentColor"
          className="animate-signal-trace text-brand"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeDasharray="320"
        />
      </svg>
      <p className="text-[0.82rem] font-medium text-ink/60">Reading stored estate records…</p>
    </div>
  );
}

function AnswerCard({ answer, onRelated }) {
  return (
    <div className="animate-fade-in space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-soft">
      <div>
        <p className="text-[0.66rem] font-semibold tracking-[0.14em] text-brand-ink uppercase">
          Summary
        </p>
        <p className="mt-1.5 text-[0.88rem] leading-relaxed text-ink/75">{answer.summary}</p>
      </div>

      {answer.evidence.length > 0 ? (
        <div className="rounded-xl bg-canvas p-4">
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <FileText className="h-3.5 w-3.5" /> Evidence
          </p>
          <ul className="mt-2.5 space-y-2">
            {answer.evidence.map((item) => (
              <li key={item} className="flex gap-2.5 text-[0.82rem] leading-snug text-ink/70">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {answer.recommendation ? (
        <div className="rounded-xl border border-line p-4">
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <ListChecks className="h-3.5 w-3.5" /> Recommendation
          </p>
          <p className="mt-2 text-[0.86rem] leading-relaxed text-ink/75">
            {answer.recommendation}
          </p>
        </div>
      ) : null}

      {answer.related.length > 0 ? (
        <div>
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <Link2 className="h-3.5 w-3.5" /> Related records
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {answer.related.map((pill) => (
              <button
                key={pill}
                type="button"
                onClick={() => onRelated(pill)}
                className="rounded-full border border-line px-3 py-1.5 text-[0.76rem] font-medium text-ink/70 transition-colors duration-200 hover:border-brand-soft hover:bg-canvas hover:text-brand-ink"
              >
                {pill}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <p className="border-t border-line pt-3 text-[0.7rem] leading-relaxed text-ink/35">
        {answer.source === 'n8n'
          ? 'Answered by the VALORA intelligence service. Recommendation only — verify against the source records before acting.'
          : 'Recommendation only, answered from the estate’s stored records. Verify against the source records before acting.'}
      </p>
    </div>
  );
}

/**
 * The chat body — shared between the collapsed inline card and the expanded modal.
 */
function ChatBody({ messages, loading, error, value, setValue, onAsk, onRelated }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <>
      {/* Message feed */}
      <div className="scrollbar-slim flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="rounded-2xl bg-canvas p-5">
            <p className="text-[0.85rem] leading-relaxed text-ink/60">
              Ask about estate condition, spend, assets or service providers. Answers come back as a
              summary, the evidence behind it and a recommended next step.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {askValoraPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onAsk(prompt)}
                  className="rounded-full border border-line bg-surface px-3.5 py-2 text-left text-[0.78rem] font-medium text-ink/70 transition-all duration-200 hover:border-brand-soft hover:text-brand-ink"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) =>
          message.role === 'user' ? (
            <div key={message.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[0.85rem] leading-snug text-white">
                {message.text}
              </p>
            </div>
          ) : message.answer ? (
            <AnswerCard key={message.id} answer={message.answer} onRelated={onRelated} />
          ) : null,
        )}

        {error ? (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        ) : null}
        {loading ? <AnalysingState /> : null}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-line/50 px-5 py-4">
        <div className="flex items-center gap-2">
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onAsk();
            }}
            placeholder="Ask about estate condition, spend or providers"
            aria-label="Ask VALORA a question"
            className="h-11"
          />
          <Button
            onClick={onAsk}
            disabled={loading}
            variant="ink"
            size="icon"
            className="h-11 w-11 shrink-0"
            aria-label="Send question"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mt-2.5 text-[0.7rem] text-ink/35">
          {intelligenceServiceConfigured
            ? 'VALORA Intelligence reads estate operational signals only — never private resident data.'
            : "Answers come from the estate's stored operational records. VALORA Intelligence reads operational signals only — never private resident data."}
        </p>
      </div>
    </>
  );
}

/**
 * "Ask VALORA"
 *
 * Renders as a compact inline card. When the user starts interacting (or clicks
 * expand), the chat moves into a centered modal with a blurred backdrop so the
 * conversation gets full focus. The modal can be dismissed back to inline.
 */
export function AskValora({ className }) {
  const { estateId, estate } = useEstateScope();
  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [nextId, setNextId] = useState(1);
  const [expanded, setExpanded] = useState(false);

  async function ask(prompt) {
    const question = (prompt ?? value).trim();
    if (!question || loading) return;
    // Auto-expand when the user asks the first question
    if (messages.length === 0) setExpanded(true);
    setValue('');
    setMessages((current) => [...current, { id: nextId, role: 'user', text: question }]);
    setNextId((current) => current + 1);
    setLoading(true);
    setError(null);
    try {
      const answer = await askValora(question, {
        estateId,
        estateName: estate?.estate_name ?? null,
      });
      setMessages((current) => [
        ...current,
        { id: nextId + 1, role: 'assistant', answer },
      ]);
      setNextId((current) => current + 2);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Intelligence is unavailable. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  }

  function handleRelated(pill) {
    void ask(pill);
  }

  const chatBodyProps = { messages, loading, error, value, setValue, onAsk: ask, onRelated: handleRelated };

  return (
    <>
      {/* ---- Expanded center modal ---- */}
      <DialogPrimitive.Root open={expanded} onOpenChange={setExpanded}>
        <DialogPrimitive.Portal>
          {/* Blurred backdrop */}
          <DialogPrimitive.Overlay className="vl-overlay fixed inset-0 z-50 bg-ink/50 backdrop-blur-md" />

          {/* Glass panel */}
          <DialogPrimitive.Content
            className="vl-dialog fixed left-[50%] top-[50%] z-50 flex w-[calc(100vw-2rem)] translate-x-[-50%] translate-y-[-50%] flex-col sm:max-w-[680px] max-h-[88vh] rounded-2xl border border-white/10 shadow-lift overflow-hidden focus:outline-none"
            style={{
              background: 'color-mix(in srgb, var(--color-surface) 84%, transparent)',
              backdropFilter: 'blur(24px) saturate(1.5)',
              WebkitBackdropFilter: 'blur(24px) saturate(1.5)',
            }}
            aria-label="Ask VALORA — estate intelligence"
          >
            {/* Modal header */}
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-5 py-4"
              style={{ background: 'color-mix(in srgb, var(--color-surface) 70%, transparent)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}
            >
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-heading text-[0.95rem] font-bold text-ink">Ask VALORA</p>
                  <p className="text-[0.72rem] text-ink/45">Structured answers, every claim traceable</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setExpanded(false)}
                  className="flex h-8 w-8 items-center justify-center rounded-full text-ink/40 transition-colors hover:bg-canvas hover:text-ink"
                  aria-label="Collapse to inline"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
                <DialogPrimitive.Close
                  className="flex h-8 w-8 items-center justify-center rounded-full text-ink/40 transition-colors hover:bg-canvas hover:text-ink"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </DialogPrimitive.Close>
              </div>
            </div>

            <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
              <ChatBody {...chatBodyProps} />
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* ---- Inline collapsed card ---- */}
      <div className={cn('flex flex-col rounded-2xl border border-line bg-surface shadow-soft overflow-hidden', className)}>
        <div className="flex items-center justify-between gap-2 border-b border-line px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
              <Sparkles className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="font-heading text-[0.95rem] font-bold text-ink">Ask VALORA</p>
              <p className="truncate text-[0.72rem] text-ink/45">
                Structured answers, every claim traceable
              </p>
            </div>
          </div>
          {messages.length > 0 ? (
            <button
              onClick={() => setExpanded(true)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-ink/40 transition-colors hover:bg-canvas hover:text-ink"
              aria-label="Expand chat"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {/* Collapsed: show prompts + input only when no messages, or a summary + expand prompt */}
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col overflow-hidden">
            <ChatBody {...chatBodyProps} />
          </div>
        ) : (
          <button
            onClick={() => setExpanded(true)}
            className="flex items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-canvas"
          >
            <div className="min-w-0">
              <p className="text-[0.82rem] font-medium text-ink">
                {messages.length} message{messages.length !== 1 ? 's' : ''} in this session
              </p>
              <p className="mt-0.5 text-[0.75rem] text-ink/50 truncate">
                {messages[messages.length - 1]?.role === 'user'
                  ? messages[messages.length - 1].text
                  : messages[messages.length - 2]?.text ?? 'Continue the conversation'}
              </p>
            </div>
            <Maximize2 className="h-4 w-4 shrink-0 text-ink/30" />
          </button>
        )}
      </div>
    </>
  );
}
