import {
  CornerDownLeft,
  Maximize2,
  MessageSquare,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useEstateScope } from '../../context/EstateContext';
import { useValoraChat } from '../../context/ValoraChatContext';
import { rolePrompts } from '../../lib/intelligence';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { FormattedMarkdown } from './FormattedMarkdown';

/**
 * Ask VALORA Panel (Intelligence Page Right Rail).
 *
 * Designed to seamlessly expand into center view whenever focused or clicked,
 * providing fluid two-way multi-turn conversation backed by real estate signals.
 */
export function AskValora({ className }) {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();
  const {
    messages,
    streaming,
    error,
    setSpotlightOpen,
    sendQuestion,
    clearMessages,
  } = useValoraChat();

  const [inputVal, setInputVal] = useState('');
  const inputRef = useRef(null);

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

  function handleFocusOrExpand() {
    // Automatically expand to center stage on entering/clicking the field
    setSpotlightOpen(true);
  }

  function handleSend(customText) {
    const text = (customText ?? inputVal).trim();
    if (!text || streaming) return;
    setInputVal('');
    // Open center view and submit
    setSpotlightOpen(true);
    sendQuestion(text, { estateId, role });
  }

  return (
    <div
      className={cn(
        'flex flex-col h-full rounded-2xl border border-line bg-surface shadow-soft overflow-hidden transition-all',
        className
      )}
    >
      {/* Panel Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-line px-5 py-4 bg-canvas/30">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
            <Sparkles className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-heading text-[0.95rem] font-bold text-ink">Ask VALORA</p>
              <span className="rounded-full bg-brand-soft/20 px-2 py-0.5 text-[10px] font-semibold text-brand-ink">
                {roleLabel}
              </span>
            </div>
            <p className="text-[0.72rem] text-ink/45 truncate">
              Two-way intelligence, every claim traceable
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearMessages}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-ink/40 hover:bg-canvas hover:text-ink transition-colors"
              title="Reset conversation"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={handleFocusOrExpand}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-ink/40 hover:bg-canvas hover:text-ink transition-colors"
            title="Expand to center view (⌘K)"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Message Feed / Suggestions */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 scrollbar-slim">
        {messages.length === 0 ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-line/70 bg-canvas/60 p-4">
              <p className="text-xs font-medium text-ink leading-relaxed">
                Ask about estate risks, active work orders, complaints, or Living Score trends.
              </p>
              <p className="mt-1 text-[11px] text-ink-muted">
                Entering this field expands into a full center-stage dialogue.
              </p>
            </div>

            <div>
              <p className="mb-2 text-[10px] font-bold tracking-wider text-ink/40 uppercase">
                Suggested prompts
              </p>
              <div className="flex flex-col gap-1.5">
                {suggestions.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    className="flex items-center justify-between rounded-xl border border-line/80 bg-surface px-3 py-2 text-left text-xs font-medium text-ink/75 hover:border-brand-soft hover:bg-brand-wash/30 hover:text-brand-ink transition-all"
                  >
                    <span className="line-clamp-2">{prompt}</span>
                    <CornerDownLeft className="h-3 w-3 shrink-0 ml-2 text-ink/30" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Active Thread Preview */
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-1 border-b border-line/50">
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink/60">
                <MessageSquare className="h-3.5 w-3.5 text-brand" />
                {messages.length} message{messages.length !== 1 ? 's' : ''} in thread
              </span>
              <button
                type="button"
                onClick={handleFocusOrExpand}
                className="text-xs font-semibold text-brand hover:underline inline-flex items-center gap-1"
              >
                Expand center view <Maximize2 className="h-3 w-3" />
              </button>
            </div>

            {messages.slice(-3).map((msg) =>
              msg.role === 'user' ? (
                <div key={msg.id} className="flex justify-end">
                  <p className="max-w-[90%] rounded-xl bg-ink px-3 py-1.5 text-xs text-white">
                    {msg.content}
                  </p>
                </div>
              ) : (
                <div key={msg.id} className="rounded-xl border border-line bg-canvas/60 p-3 text-xs">
                  <FormattedMarkdown content={msg.content.slice(0, 280) + (msg.content.length > 280 ? '…' : '')} />
                  {msg.streaming && (
                    <span className="inline-block h-3 w-1 bg-brand animate-pulse ml-1" />
                  )}
                </div>
              )
            )}
          </div>
        )}
      </div>

      {/* Input Field: Clicking or focusing triggers center expansion */}
      <div className="shrink-0 border-t border-line px-4 py-3 bg-canvas/30">
        <div
          onClick={handleFocusOrExpand}
          className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 cursor-pointer hover:border-brand-soft hover:ring-2 hover:ring-brand/10 transition-all shadow-sm"
        >
          <input
            ref={inputRef}
            type="text"
            value={inputVal}
            onFocus={handleFocusOrExpand}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Click to ask VALORA in center view…"
            className="w-full bg-transparent text-xs text-ink placeholder:text-ink/40 focus:outline-none cursor-pointer"
            readOnly
          />
          <Button
            size="sm"
            variant="ink"
            className="h-7 w-7 p-0 shrink-0 rounded-lg"
            onClick={handleFocusOrExpand}
            aria-label="Expand and ask"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="mt-1.5 text-[10px] text-ink/35 text-center">
          Press ⌘K anywhere to open center view
        </p>
      </div>
    </div>
  );
}
