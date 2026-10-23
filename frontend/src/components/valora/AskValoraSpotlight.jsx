import {
  AlertCircle,
  Check,
  Command,
  Copy,
  CornerDownLeft,
  RotateCcw,
  Sparkles,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useEstateScope } from '../../context/EstateContext';
import { useValoraChat } from '../../context/ValoraChatContext';
import { rolePrompts } from '../../lib/intelligence';
import { Button } from '../ui/button';
import { FormattedMarkdown } from './FormattedMarkdown';

export function AskValoraSpotlight() {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();
  const {
    messages,
    streaming,
    error,
    setError,
    spotlightOpen,
    setSpotlightOpen,
    sendQuestion,
    clearMessages,
  } = useValoraChat();

  const [inputVal, setInputVal] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  // Resolve user role
  const isHoaAdmin = user?.role === 'hoa_admin' && estate?.is_estate_admin === true;
  const isProvider = user?.role === 'service_provider' || estate?.is_estate_provider === true;
  const role = isHoaAdmin ? 'hoa_admin' : isProvider ? 'service_provider' : 'resident';
  const roleLabel = isHoaAdmin
    ? 'HOA Executive'
    : isProvider
    ? 'Contractor'
    : 'Resident';

  const suggestions = rolePrompts[role] ?? rolePrompts.resident;

  // Autofocus input when modal opens
  useEffect(() => {
    if (spotlightOpen) {
      setTimeout(() => inputRef.current?.focus(), 60);
    } else {
      setError(null);
    }
  }, [spotlightOpen, setError]);

  // Auto-scroll response as tokens arrive or new messages appear
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming]);

  function handleSend(customText) {
    const text = (customText ?? inputVal).trim();
    if (!text || streaming) return;

    if (text.length < 3) {
      setError('Please enter a question with at least 3 characters.');
      return;
    }

    setInputVal('');
    sendQuestion(text, { estateId, role });
  }

  function handleCopy(id, text) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  if (!spotlightOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center p-3 pt-[8vh] sm:p-6 sm:pt-[10vh] animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label="Ask VALORA Intelligence"
    >
      {/* Blurred transparent backdrop */}
      <div
        className="fixed inset-0 bg-ink/40 backdrop-blur-md transition-opacity"
        onClick={() => setSpotlightOpen(false)}
      />

      {/* Floating Center-Stage Modal Card */}
      <div className="relative flex flex-col w-full max-w-3xl h-[80vh] max-h-[760px] overflow-hidden rounded-2xl border border-line bg-surface/98 shadow-2xl backdrop-blur-2xl transition-all">
        {/* Header bar */}
        <div className="flex shrink-0 items-center justify-between border-b border-line/70 px-5 py-3.5 bg-canvas/40">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-wash text-brand-ink">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="text-xs font-bold tracking-wider text-ink uppercase">
              VALORA Intelligence
            </span>
            <span className="rounded-full bg-brand-soft/20 px-2.5 py-0.5 text-[10px] font-semibold text-brand-ink">
              {roleLabel}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && !streaming && (
              <button
                type="button"
                onClick={clearMessages}
                className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-ink-muted hover:bg-canvas hover:text-ink transition-colors"
                title="Start a new conversation thread"
              >
                <RotateCcw className="h-3 w-3" />
                <span>New thread</span>
              </button>
            )}
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-line bg-surface px-1.5 py-0.5 text-[10px] font-medium text-ink/40">
              <Command className="h-2.5 w-2.5" /> K
            </kbd>
            <button
              type="button"
              onClick={() => setSpotlightOpen(false)}
              className="rounded-lg p-1 text-ink/40 hover:bg-canvas hover:text-ink transition-colors"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Conversation Message Feed */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-5 py-5 space-y-5 scrollbar-slim"
        >
          {messages.length === 0 ? (
            /* Empty State: Inviting Prompts */
            <div className="flex flex-col items-center justify-center text-center h-full max-w-lg mx-auto py-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-wash text-brand-ink mb-4 shadow-sm">
                <Sparkles className="h-6 w-6" />
              </div>
              <h3 className="font-heading text-lg font-bold text-ink">
                How can VALORA assist you today?
              </h3>
              <p className="mt-1.5 text-xs text-ink-muted leading-relaxed max-w-md">
                Grounded two-way intelligence powered by verified estate records, maintenance orders,
                and measured operational signals.
              </p>

              <div className="mt-6 w-full space-y-2">
                <p className="text-[10px] font-bold tracking-wider text-ink/40 uppercase text-left">
                  Suggested for {roleLabel}
                </p>
                <div className="flex flex-col gap-1.5">
                  {suggestions.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleSend(prompt)}
                      className="group flex items-center justify-between rounded-xl border border-line bg-canvas/60 px-3.5 py-2.5 text-left text-xs font-medium text-ink/80 hover:border-brand-soft hover:bg-brand-wash/40 hover:text-brand-ink transition-all"
                    >
                      <span>{prompt}</span>
                      <CornerDownLeft className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-brand-ink" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Message turns */
            messages.map((msg) =>
              msg.role === 'user' ? (
                <div key={msg.id} className="flex justify-end animate-in fade-in">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-ink px-4 py-2.5 text-[0.88rem] leading-relaxed text-white shadow-sm">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div key={msg.id} className="flex gap-3 animate-in fade-in">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-wash text-brand-ink mt-1">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0 rounded-2xl border border-line bg-canvas/60 p-4 text-ink shadow-soft">
                    <FormattedMarkdown content={msg.content} />
                    {msg.streaming && (
                      <span className="inline-block h-4 w-1.5 translate-y-0.5 bg-brand animate-pulse ml-1" />
                    )}

                    {!msg.streaming && msg.content && (
                      <div className="mt-3.5 flex items-center justify-between border-t border-line/50 pt-2 text-[11px] text-ink/45">
                        <span>Verified against authorized estate records</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(msg.id, msg.content)}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-brand hover:underline"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check className="h-3 w-3 text-mint-ink" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" /> Copy answer
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )
            )
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 border-t border-rose-200/60 bg-rose-50/80 px-5 py-2.5 text-xs text-rose-700">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {/* Persistent Bottom Input Bar */}
        <div className="shrink-0 border-t border-line/70 bg-surface p-4">
          <div className="flex items-center gap-2 rounded-xl border border-line bg-canvas px-3 py-2 focus-within:border-brand-soft focus-within:ring-2 focus-within:ring-brand/10 transition-all">
            <input
              ref={inputRef}
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={
                messages.length > 0
                  ? 'Ask a follow-up question…'
                  : role === 'hoa_admin'
                  ? 'Ask about risks, work orders, complaints, or Living Score…'
                  : role === 'service_provider'
                  ? 'Ask about assigned work orders, SLA deadlines, or access hours…'
                  : 'Ask about community rules, your logged repairs, or Living Score…'
              }
              className="w-full bg-transparent text-[0.92rem] text-ink placeholder:text-ink/35 focus:outline-none"
              disabled={streaming}
            />
            <Button
              size="sm"
              variant="ink"
              className="h-8 rounded-lg px-3 gap-1 shrink-0"
              disabled={!inputVal.trim() || streaming}
              onClick={() => handleSend()}
            >
              <span className="text-xs">Send</span>
              <CornerDownLeft className="h-3 w-3" />
            </Button>
          </div>
          <p className="mt-2 text-[10px] text-ink/40 text-center">
            VALORA Intelligence reads estate operational signals only — never private resident data.
          </p>
        </div>
      </div>
    </div>
  );
}
