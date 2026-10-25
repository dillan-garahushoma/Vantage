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

function AnalysingState({ role }) {
  const message = role === 'hoa_admin'
    ? 'Reviewing authorised estate records…'
    : role === 'service_provider'
      ? 'Reviewing work assigned to your account…'
      : 'Reviewing your requests and published estate information…';

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
      <p className="text-[0.8rem] font-medium text-ink/65">{message}</p>
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
  const messageViewportRef = useRef(null);
  const [copiedId, setCopiedId] = useState(null);
  const [copyError, setCopyError] = useState(null);

  const assistantTitle = role === 'hoa_admin'
    ? 'Estate operations intelligence'
    : role === 'service_provider'
      ? 'Assigned work assistant'
      : 'Personal estate assistant';

  useEffect(() => {
    const viewport = messageViewportRef.current;
    if (viewport) viewport.scrollTop = viewport.scrollHeight;
  }, [messages, streaming]);

  async function copyAnswer(id, text) {
    if (!text) return;
    setCopyError(null);
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard access is unavailable in this browser.');
      }
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      setCopyError('Could not copy this answer. Select and copy the text instead.');
    }
  }

  return (
    <>
      <div ref={messageViewportRef} className="scrollbar-slim flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="py-1">
            <h2 className="font-heading text-sm font-semibold text-ink">
              {assistantTitle}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink/70">
              {role === 'hoa_admin'
                ? 'Ask about current operational risks, work orders, complaints, incidents, or Living Score drivers.'
                : role === 'service_provider'
                ? 'Ask about work assigned to your provider account, recorded instructions, and due dates.'
                : 'Ask about your maintenance requests, their recorded updates, or published estate health information.'}
            </p>
            <div className="mt-5 flex flex-wrap gap-2" aria-label="Suggested questions">
              {suggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onAsk(prompt)}
                  className="min-h-11 max-w-full rounded-lg bg-canvas px-3.5 py-2.5 text-left text-[0.82rem] font-medium text-ink/80 transition-colors hover:bg-brand-wash hover:text-brand-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
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

                <div className="flex items-center justify-between gap-3 pb-1">
                  <span className="text-[0.68rem] font-semibold text-ink/45">
                    {msg.mode === 'stored_records' ? 'Stored-record answer' : 'AI-assisted answer'}
                  </span>
                  {msg.mode === 'ai_assisted' ? (
                    <span className="text-[0.68rem] text-ink/40">Interpretation grounded in authorized records</span>
                  ) : null}
                </div>
                <AiAnswerRenderer
                  content={msg.text}
                  evidence={msg.evidence ?? []}
                  related={msg.related ?? []}
                  role={role}
                  onFollowUp={onAsk}
                />
                {copyError ? <p role="alert" className="mt-2 text-xs text-rose-700">{copyError}</p> : null}
                {msg.streaming ? (
                  <span className="inline-block h-3.5 w-1 bg-brand animate-pulse ml-0.5" />
                ) : null}
              </div>

              {!msg.streaming && !msg.metadataReceived && followUps.length > 0 ? (
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

        {streaming && messages.every((m) => !m.streaming) ? <AnalysingState role={role} /> : null}
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
                ? 'Ask about estate operations, complaints, incidents, or work orders…'
                : role === 'service_provider'
                ? 'Ask about your assigned work, recorded instructions, or due dates…'
                : 'Ask about your requests or published estate information…'
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
          <span>
            {role === 'hoa_admin'
              ? 'Answers use authorised estate operational records.'
              : role === 'service_provider'
                ? 'Answers are limited to work assigned to your provider account.'
                : 'Answers are limited to your requests and published estate information.'}
          </span>
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

const fallbackSuggestions = {
  hoa_admin: [
    'What is the operational risk summary for this week?',
    'Which work orders are currently overdue?',
    'Summarise open complaints and contractor performance.',
  ],
  resident: [
    'What updates are recorded on my maintenance requests?',
    'Which of my requests is still open?',
    'Is a Living Score published for my estate?',
  ],
  service_provider: [
    'What work is assigned to my provider account?',
    'Which of my assigned jobs is due soon?',
    'What instructions are recorded for my assigned work?',
  ],
};

export function AskValora({ className, estateId: pageEstateId, role: pageRole }) {
  const { estateId: contextEstateId, estate } = useEstateScope();
  const { user } = useAuth();

  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState('');
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const messagesRef = useRef(messages);
  const streamingRef = useRef(false);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Role resolution
  const estateId = pageEstateId ?? contextEstateId;
  const fallbackRole = (
    user?.role === 'hoa_admin' && estate?.is_estate_admin === true
      ? 'hoa_admin'
      : user?.role === 'service_provider' && estate?.is_estate_provider === true
        ? 'service_provider'
        : 'resident'
  );
  const role = ['hoa_admin', 'service_provider', 'resident'].includes(pageRole)
    ? pageRole
    : fallbackRole;

  const roleSuggestions = Array.isArray(rolePrompts?.[role])
    ? rolePrompts[role]
    : fallbackSuggestions[role] ?? fallbackSuggestions.resident;
  const suggestions = roleSuggestions.length > 0 ? roleSuggestions : fallbackSuggestions.resident;
  const followUps = roleSuggestions.length > 0 ? roleSuggestions : fallbackSuggestions.resident;

  async function handleAsk(promptText) {
    const question = (promptText ?? value).trim();
    if (!question || streamingRef.current) return;

    if (!estateId) {
      setError('Please select an active estate first.');
      return;
    }

    setValue('');
    setError(null);
    setExpanded(true);
    streamingRef.current = true;
    setStreaming(true);

    const userMessageId = Date.now();
    const assistantMessageId = userMessageId + 1;

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: 'user', text: question },
      { id: assistantMessageId, role: 'assistant', text: '', evidence: [], related: [], mode: 'ai_assisted', streaming: true },
    ]);

    // Build multi-turn clean history for streaming from the latest state and
    // include the new user message after it's queued, ensuring follow-up clicks
    // carry the real request history rather than stale state from the previous render.
    const history = messagesRef.current
      .filter((m) => (m.role === 'user' || m.role === 'assistant') && (m.text || '').trim())
      .map((m) => ({ role: m.role, content: m.text.trim() }));

    const latestHistory = [...history, { role: 'user', content: question }];

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
          onMeta: (metadata) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      evidence: Array.isArray(metadata.evidence) ? metadata.evidence : [],
                      related: Array.isArray(metadata.related) ? metadata.related : [],
                      mode: metadata.mode === 'stored_records' ? 'stored_records' : 'ai_assisted',
                      metadataReceived: true,
                    }
                  : msg
              )
            );
          },
          onDone: () => {
            streamingRef.current = false;
            setStreaming(false);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId ? { ...msg, streaming: false } : msg
              )
            );
          },
          onError: (err) => {
            streamingRef.current = false;
            setStreaming(false);
            setError(err.message || 'Unable to connect to VALORA Intelligence.');
            setValue(question);
            setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
          },
        },
        latestHistory
      );
    } catch (err) {
      streamingRef.current = false;
      setStreaming(false);
      setError(err instanceof Error ? err.message : 'Unable to connect to VALORA Intelligence.');
      setValue(question);
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
    }
  }

  function handleReset() {
    setMessages([]);
    setValue('');
    setError(null);
    streamingRef.current = false;
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
            className="vl-dialog fixed left-[50%] top-[50%] z-50 flex w-[calc(100vw-2rem)] h-[85vh] max-h-[800px] translate-x-[-50%] translate-y-[-50%] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-lift focus:outline-none sm:max-w-[840px] md:max-w-[900px]"
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
                    {role === 'hoa_admin' ? 'HOA administrator' : role === 'service_provider' ? 'Service provider' : 'Resident'}
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
