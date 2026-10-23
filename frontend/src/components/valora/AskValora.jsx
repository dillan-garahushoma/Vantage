import { Check, Copy, Maximize2, Minimize2, RotateCcw, Send, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { useAuth } from '../../context/AuthContext';
import { useEstateScope } from '../../context/EstateContext';
import { rolePrompts, streamAskValora } from '../../lib/intelligence';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { AiAnswerRenderer } from './AiAnswerRenderer';

const ROLE_FOLLOW_UPS = {
  hoa_admin: [
    'Which open issues are driving this?',
    'Compare with last 30 days',
    'What should the HOA escalate first?',
  ],
  service_provider: [
    'Which work orders are highest priority?',
    'What are the contractor access hours?',
    'Check SLA deadlines for open jobs',
  ],
  resident: [
    'Which open issues are driving this?',
    'What is the expected resolution timeline?',
    'What are the estate quiet hours?',
  ],
};

function AnalysingState() {
  return (
    <div
      className="flex items-center gap-3 rounded-xl border border-line bg-canvas px-4 py-3"
      role="status"
      aria-live="polite"
    >
      <svg viewBox="0 0 120 24" className="h-5 w-[100px]" aria-hidden="true">
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
      <p className="text-[0.8rem] font-medium text-ink/65">Analysing estate operational signals…</p>
    </div>
  );
}

function ChatBody({
  messages,
  streaming,
  error,
  value,
  setValue,
  onAsk,
  onReset,
  role,
  suggestions,
  followUps,
}) {
  const bottomRef = useRef(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, streaming]);

  function copyAnswer(id, text) {
    if (!text) return;
    navigator.clipboard?.writeText?.(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <>
      <div className="scrollbar-slim flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="rounded-xl border border-line bg-canvas/70 p-5">
            <div className="flex items-center gap-2 text-brand">
              <Sparkles className="h-4 w-4" />
              <p className="text-xs font-bold tracking-wider text-brand-ink uppercase">
                Grounded Estate Intelligence
              </p>
            </div>
            <p className="mt-2 text-[0.85rem] leading-relaxed text-ink/70">
              {role === 'hoa_admin'
                ? 'Ask about current operational risks, overdue work orders, incident resolution, or Living Score health drivers.'
                : role === 'service_provider'
                ? 'Ask about assigned work orders, contractor access hours, gate requirements, or SLA deadlines.'
                : 'Ask about estate rules, your logged maintenance requests, or Living Score health.'}
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <p className="text-[0.72rem] font-semibold tracking-wider text-ink/40 uppercase">
                Suggested prompts
              </p>
              {suggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onAsk(prompt)}
                  className="rounded-lg border border-line bg-surface px-3.5 py-2.5 text-left text-[0.82rem] font-medium text-ink/80 transition-all duration-200 hover:border-brand-soft hover:bg-canvas hover:text-brand-ink"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((msg) =>
          msg.role === 'user' ? (
            <div key={msg.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-ink px-4 py-2.5 text-[0.86rem] leading-relaxed text-white">
                {msg.text}
              </p>
            </div>
          ) : (
            <div key={msg.id} className="space-y-2">
              <div className="rounded-xl border border-line bg-surface p-4.5 shadow-soft">
                <div className="flex items-center justify-between border-b border-line pb-2.5 mb-3">
                  <span className="flex items-center gap-1.5 text-[0.68rem] font-bold tracking-wider text-brand-ink uppercase">
                    <Sparkles className="h-3.5 w-3.5 text-brand" />
                    VALORA Intelligence
                  </span>
                  <div className="flex items-center gap-2">
                    {msg.text && !msg.streaming ? (
                      <button
                        type="button"
                        onClick={() => copyAnswer(msg.id, msg.text)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-[0.72rem] font-medium text-ink/50 hover:bg-canvas hover:text-ink transition-colors"
                        aria-label="Copy answer"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="h-3 w-3 text-mint-ink" />
                            <span className="text-mint-ink">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    ) : null}
                  </div>
                </div>

                <AiAnswerRenderer content={msg.text} />
                {msg.streaming ? (
                  <span className="inline-block h-3.5 w-1 bg-brand animate-pulse ml-0.5" />
                ) : null}
              </div>

              {!msg.streaming && followUps.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5 pt-1 pl-1">
                  <span className="text-[0.7rem] font-medium text-ink/40">Suggested follow-ups:</span>
                  {followUps.map((fu) => (
                    <button
                      key={fu}
                      type="button"
                      onClick={() => onAsk(fu)}
                      className="rounded-full border border-line bg-surface px-3 py-1 text-[0.76rem] font-medium text-ink/75 transition-colors hover:border-brand-soft hover:bg-canvas hover:text-brand-ink"
                    >
                      {fu}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          )
        )}

        {error ? (
          <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </div>
        ) : null}

        {streaming && messages.every((m) => !m.streaming) ? <AnalysingState /> : null}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-line/60 bg-surface px-5 py-3.5">
        <div className="flex items-center gap-2">
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                onAsk();
              }
            }}
            placeholder={
              role === 'hoa_admin'
                ? 'Ask about risks, work orders, complaints, or Living Score…'
                : role === 'service_provider'
                ? 'Ask about assigned work orders, SLA deadlines, or access hours…'
                : 'Ask about community rules, your logged repairs, or Living Score…'
            }
            aria-label="Ask VALORA a question"
            disabled={streaming}
            className="h-10 text-xs sm:text-sm"
          />
          <Button
            onClick={() => onAsk()}
            disabled={streaming || !value.trim()}
            variant="ink"
            size="icon"
            className="h-10 w-10 shrink-0"
            aria-label="Send question"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-2 flex items-center justify-between text-[0.7rem] text-ink/40">
          <span>VALORA Intelligence reads estate operational signals only — never private resident data.</span>
          {messages.length > 0 ? (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1 font-medium text-ink/50 hover:text-ink transition-colors"
            >
              <RotateCcw className="h-3 w-3" />
              New session
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
}

export function AskValora({ className }) {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();

  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState('');
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Role resolution
  const isHoaAdmin = user?.role === 'hoa_admin' && estate?.is_estate_admin === true;
  const isProvider = user?.role === 'service_provider' || estate?.is_estate_provider === true;
  const role = isHoaAdmin ? 'hoa_admin' : isProvider ? 'service_provider' : 'resident';

  const suggestions = rolePrompts[role] ?? rolePrompts.resident;
  const followUps = ROLE_FOLLOW_UPS[role] ?? ROLE_FOLLOW_UPS.resident;

  async function handleAsk(promptText) {
    const question = (promptText ?? value).trim();
    if (!question || streaming) return;

    if (!estateId) {
      setError('Please select an active estate first.');
      return;
    }

    // When starting a prompt, open the focused dialog so the conversation gets full attention
    setExpanded(true);
    setValue('');
    setError(null);
    setStreaming(true);

    const userMessageId = Date.now();
    const assistantMessageId = userMessageId + 1;

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: 'user', text: question },
      { id: assistantMessageId, role: 'assistant', text: '', streaming: true },
    ]);

    // Build multi-turn clean history for streaming
    const history = messages
      .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.text)
      .map((m) => ({ role: m.role, content: m.text }));

    try {
      await streamAskValora(
        question,
        { estateId, role },
        {
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, text: msg.text + token }
                  : msg
              )
            );
          },
          onDone: () => {
            setStreaming(false);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId ? { ...msg, streaming: false } : msg
              )
            );
          },
          onError: (err) => {
            setStreaming(false);
            setError(err.message || 'Unable to connect to VALORA Intelligence.');
            setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
          },
        },
        history
      );
    } catch (err) {
      setStreaming(false);
      setError(err instanceof Error ? err.message : 'Unable to connect to VALORA Intelligence.');
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
    }
  }

  function handleReset() {
    setMessages([]);
    setValue('');
    setError(null);
    setStreaming(false);
  }

  const chatBodyProps = {
    messages,
    streaming,
    error,
    value,
    setValue,
    onAsk: handleAsk,
    onReset: handleReset,
    role,
    suggestions,
    followUps,
  };

  return (
    <>
      {/* ---- Focused modal dialog ---- */}
      <DialogPrimitive.Root open={expanded} onOpenChange={setExpanded}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="vl-overlay fixed inset-0 z-50 bg-ink/50 backdrop-blur-sm" />
          <DialogPrimitive.Content
            className="vl-dialog fixed left-[50%] top-[50%] z-50 flex w-[calc(100vw-2rem)] h-[85vh] max-h-[800px] translate-x-[-50%] translate-y-[-50%] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-lift focus:outline-none sm:max-w-[760px]"
            role="dialog"
            aria-label="Ask VALORA Intelligence"
          >
            {/* Modal header */}
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-5 py-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-heading text-[0.98rem] font-bold text-ink">Ask VALORA</p>
                    <span className="rounded-full bg-canvas px-2.5 py-0.5 text-[10px] font-semibold text-ink/55 uppercase">
                      {role === 'hoa_admin' ? 'HOA Executive' : role === 'service_provider' ? 'Contractor' : 'Resident'}
                    </span>
                  </div>
                  <p className="text-[0.72rem] text-ink/45">Structured answers, every claim traceable</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
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
              {expanded ? <ChatBody {...chatBodyProps} /> : null}
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* ---- Inline card ---- */}
      <div
        className={cn(
          'flex flex-col h-full overflow-hidden rounded-2xl border border-line bg-surface shadow-soft',
          className
        )}
      >
        <div className="flex items-center justify-between gap-2 border-b border-line px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
              <Sparkles className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-heading text-[0.95rem] font-bold text-ink">Ask VALORA</p>
                <span className="rounded-full bg-canvas px-2 py-0.5 text-[9px] font-semibold text-ink/55 uppercase">
                  {role === 'hoa_admin' ? 'HOA' : role === 'service_provider' ? 'Contractor' : 'Resident'}
                </span>
              </div>
              <p className="truncate text-[0.72rem] text-ink/45">
                Operational intelligence, grounded in records
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="flex h-8 w-8 items-center justify-center rounded-full text-ink/40 transition-colors hover:bg-canvas hover:text-ink"
            aria-label="Expand chat"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
          {!expanded ? (
            <ChatBody {...chatBodyProps} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center p-6 text-center text-xs text-ink/45">
              <Sparkles className="h-5 w-5 text-brand/60 mb-2" />
              <p>Conversation active in focus window</p>
              <button
                type="button"
                onClick={() => setExpanded(true)}
                className="mt-2 text-brand-ink hover:underline font-medium"
              >
                Bring to front
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
