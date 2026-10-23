import { AlertCircle, Command, Copy, CornerDownLeft, Sparkles, X, Check, ArrowRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useEstateScope } from '../../context/EstateContext';
import { rolePrompts, streamAskValora } from '../../lib/intelligence';
import { Button } from '../ui/button';
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

export function AskValoraSpotlight({ open, onOpenChange }) {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  const [query, setQuery] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [response, setResponse] = useState('');
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Resolve user role: 'hoa_admin' | 'service_provider' | 'resident'
  const isHoaAdmin = user?.role === 'hoa_admin' && estate?.is_estate_admin === true;
  const isProvider = user?.role === 'service_provider' || estate?.is_estate_provider === true;
  const role = isHoaAdmin ? 'hoa_admin' : isProvider ? 'service_provider' : 'resident';

  const initialSuggestions = rolePrompts[role] ?? rolePrompts.resident;
  const followUps = ROLE_FOLLOW_UPS[role] ?? ROLE_FOLLOW_UPS.resident;

  // Global Cmd+K / Ctrl+K keyboard shortcut
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenChange((prev) => !prev);
      } else if (e.key === 'Escape' && open) {
        onOpenChange(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  // Autofocus input when modal opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setStreaming(false);
      setResponse('');
      setError(null);
    }
  }, [open]);

  // Auto-scroll response as tokens arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [response]);

  function handleSend(textToSend) {
    const q = (textToSend ?? query).trim();
    if (!q || streaming) return;

    if (!estateId) {
      setError('Please select an active estate first.');
      return;
    }

    setQuery(q);
    setStreaming(true);
    setResponse('');
    setError(null);

    streamAskValora(
      q,
      { estateId, role },
      {
        onToken: (token) => {
          setResponse((prev) => prev + token);
        },
        onDone: () => {
          setStreaming(false);
        },
        onError: (err) => {
          setStreaming(false);
          setError(err.message || 'Unable to connect to VALORA Intelligence.');
        },
      }
    );
  }

  function handleCopy() {
    if (!response) return;
    navigator.clipboard.writeText(response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[10vh] sm:p-6 sm:pt-[12vh] animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label="Ask VALORA Spotlight"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/40 transition-opacity"
        onClick={() => onOpenChange(false)}
      />

      {/* Spotlight Window */}
      <div className="relative w-full max-w-2xl overflow-hidden rounded-lg border border-line bg-surface p-0 shadow-lift transition-all">
        {/* Header bar */}
        <div className="flex items-center justify-between border-b border-line/70 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-xs bg-brand-wash text-brand-ink">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span className="text-xs font-semibold tracking-wider text-ink uppercase">
              VALORA Intelligence
            </span>
            <span className="rounded bg-line/60 px-2 py-0.5 text-[10px] font-medium text-ink-muted">
              {role === 'hoa_admin'
                ? 'HOA Executive'
                : role === 'service_provider'
                ? 'Contractor'
                : 'Resident'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-line bg-canvas px-1.5 py-0.5 text-[10px] font-medium text-ink/50">
              <Command className="h-2.5 w-2.5" /> K
            </kbd>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-xs p-1 text-ink/40 hover:bg-canvas hover:text-ink transition-colors"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Input box */}
        <div className="relative flex items-center px-4 py-3.5">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              role === 'hoa_admin'
                ? 'Ask about risks, work orders, complaints, or Living Score…'
                : role === 'service_provider'
                ? 'Ask about assigned work orders, SLA deadlines, or access hours…'
                : 'Ask about community rules, your logged repairs, or Living Score…'
            }
            className="w-full bg-transparent text-[0.95rem] text-ink placeholder:text-ink/35 focus:outline-none"
            disabled={streaming}
          />
          <Button
            size="sm"
            variant="ink"
            className="ml-2 h-8 rounded-md px-3 gap-1 shrink-0"
            disabled={!query.trim() || streaming}
            onClick={() => handleSend()}
          >
            <span className="text-xs">Ask</span>
            <CornerDownLeft className="h-3 w-3" />
          </Button>
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 border-t border-rose-200/60 bg-rose-50/70 px-4 py-2.5 text-xs text-rose-700">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Response Area */}
        {(response || streaming) && (
          <div
            ref={scrollRef}
            className="max-h-[380px] overflow-y-auto border-t border-line/60 bg-canvas p-4 text-sm leading-relaxed text-ink/80"
          >
            <div className="font-sans text-[0.9rem] text-ink/90">
              <AiAnswerRenderer content={response} onFollowUp={handleSend} />
              {streaming && (
                <span className="inline-block h-3.5 w-1.5 translate-y-0.5 bg-brand animate-pulse ml-0.5" />
              )}
            </div>

            {/* Contextual Follow-up Chips when finished */}
            {!streaming && response && (
              <div className="mt-4 border-t border-line/50 pt-3">
                <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-ink/45 uppercase">
                  <Sparkles className="h-3 w-3" />
                  Suggested follow-up
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {followUps.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleSend(prompt)}
                      className="inline-flex items-center gap-1 rounded-sm border border-line bg-surface px-2.5 py-1 text-left text-xs text-ink/75 transition-all hover:border-brand-soft hover:bg-canvas hover:text-brand-ink"
                    >
                      <span>{prompt}</span>
                      <ArrowRight className="h-2.5 w-2.5 text-ink/40" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!streaming && response && (
              <div className="mt-3.5 flex items-center justify-between border-t border-line/40 pt-2.5 text-xs text-ink/45">
                <span>Verified against authorized estate records</span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1 text-xs text-brand hover:underline"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 text-mint-ink" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" /> Copy
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Initial Prompt Suggestions */}
        {!response && !streaming && (
          <div className="border-t border-line/60 bg-canvas/30 px-4 py-3">
            <p className="mb-2 text-[10px] font-medium tracking-wider text-ink/40 uppercase">
              Suggested questions for your role
            </p>
            <div className="flex flex-wrap gap-1.5">
              {initialSuggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSend(prompt)}
                  className="rounded-sm border border-line bg-surface px-3 py-1 text-left text-xs text-ink/70 transition-all hover:border-brand-soft hover:bg-brand-wash hover:text-brand-ink"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
