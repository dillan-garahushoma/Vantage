import { FileText, Link2, ListChecks, Send, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useEstateScope } from '../../context/EstateContext';
import { askValora, askValoraPrompts, intelligenceServiceConfigured, } from '../../lib/intelligence';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
function AnalysingState() {
    return (<div className="flex items-center gap-3 rounded-2xl border border-line bg-canvas px-4 py-3.5" role="status" aria-live="polite">
      <svg viewBox="0 0 120 24" className="h-6 w-[120px]" aria-hidden="true">
        <path d="M0 12 h18 l5 -8 l6 16 l6 -12 l5 6 h14 l5 -9 l6 17 l5 -8 h22" fill="none" stroke="currentColor" className="animate-signal-trace text-brand" strokeWidth="1.8" strokeLinecap="round" strokeDasharray="320"/>
      </svg>
      <p className="text-[0.82rem] font-medium text-ink/60">Reading stored estate records…</p>
    </div>);
}
function AnswerCard({ answer, onRelated }) {
    return (<div className="animate-fade-in space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-soft">
      <div>
        <p className="text-[0.66rem] font-semibold tracking-[0.14em] text-brand-ink uppercase">
          Summary
        </p>
        <p className="mt-1.5 text-[0.88rem] leading-relaxed text-ink/75">{answer.summary}</p>
      </div>

      {answer.evidence.length > 0 ? (<div className="rounded-xl bg-canvas p-4">
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <FileText className="h-3.5 w-3.5"/> Evidence
          </p>
          <ul className="mt-2.5 space-y-2">
            {answer.evidence.map((item) => (<li key={item} className="flex gap-2.5 text-[0.82rem] leading-snug text-ink/70">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft"/>
                {item}
              </li>))}
          </ul>
        </div>) : null}

      {answer.recommendation ? (<div className="rounded-xl border border-line p-4">
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <ListChecks className="h-3.5 w-3.5"/> Recommendation
          </p>
          <p className="mt-2 text-[0.86rem] leading-relaxed text-ink/75">{answer.recommendation}</p>
        </div>) : null}

      {answer.related.length > 0 ? (<div>
          <p className="flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/45 uppercase">
            <Link2 className="h-3.5 w-3.5"/> Related records
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {answer.related.map((pill) => (<button key={pill} type="button" onClick={() => onRelated(pill)} className="rounded-full border border-line px-3 py-1.5 text-[0.76rem] font-medium text-ink/70 transition-colors duration-200 hover:border-brand-soft hover:bg-canvas hover:text-brand-ink">
                {pill}
              </button>))}
          </div>
        </div>) : null}

      <p className="border-t border-line pt-3 text-[0.7rem] leading-relaxed text-ink/35">
        {answer.source === 'n8n'
            ? 'Answered by the VALORA intelligence service. Recommendation only — verify against the source records before acting.'
            : 'Recommendation only, answered from the estate’s stored records. Verify against the source records before acting.'}
      </p>
    </div>);
}
/**
 * “Ask VALORA”.
 *
 * The panel uses the authenticated backend only. Errors stay errors; the browser
 * cannot replace rejected estate requests with webhook or fictional answers.
 */
export function AskValora({ className }) {
    const { estateId, estate } = useEstateScope();
    const [messages, setMessages] = useState([]);
    const [value, setValue] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [nextId, setNextId] = useState(1);
    async function ask(prompt) {
        const question = (prompt ?? value).trim();
        if (!question || loading)
            return;
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
        }
        catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Intelligence is unavailable. Please try again.');
        }
        finally {
            setLoading(false);
        }
    }
    return (<div className={cn('flex h-full min-h-0 flex-col', className)}>
      <div className="flex items-center gap-2.5 border-b border-line px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-wash text-brand-ink">
          <Sparkles className="h-4 w-4"/>
        </span>
        <div className="min-w-0">
          <p className="font-heading text-[0.95rem] font-bold text-ink">Ask VALORA</p>
          <p className="truncate text-[0.72rem] text-ink/45">
            Structured answers, every claim traceable
          </p>
        </div>
      </div>

      <div className="scrollbar-slim flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (<div className="rounded-2xl bg-canvas p-5">
            <p className="text-[0.85rem] leading-relaxed text-ink/60">
              Ask about estate condition, spend, assets or service providers. Answers come back as a
              summary, the evidence behind it and a recommended next step.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {askValoraPrompts.map((prompt) => (<button key={prompt} type="button" onClick={() => void ask(prompt)} className="rounded-full border border-line bg-surface px-3.5 py-2 text-left text-[0.78rem] font-medium text-ink/70 transition-all duration-200 hover:border-brand-soft hover:text-brand-ink">
                  {prompt}
                </button>))}
            </div>
          </div>) : null}

        {messages.map((message) => message.role === 'user' ? (<div key={message.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[0.85rem] leading-snug text-white">
                {message.text}
              </p>
            </div>) : message.answer ? (<AnswerCard key={message.id} answer={message.answer} onRelated={(pill) => void ask(pill)}/>) : null)}

        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
        {loading ? <AnalysingState /> : null}
      </div>

      <div className="border-t border-line px-5 py-4">
        <div className="flex items-center gap-2">
          <Input value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => {
            if (event.key === 'Enter')
                void ask();
        }} placeholder="Ask about estate condition, spend or providers" aria-label="Ask VALORA a question" className="h-11"/>
          <Button onClick={() => void ask()} disabled={loading} variant="ink" size="icon" className="h-11 w-11 shrink-0" aria-label="Send question">
            <Send className="h-4 w-4"/>
          </Button>
        </div>
        <p className="mt-2.5 text-[0.7rem] text-ink/35">
          {intelligenceServiceConfigured
            ? 'VALORA Intelligence reads estate operational signals only — never private resident data.'
            : 'Answers come from the estate’s stored operational records. VALORA Intelligence reads operational signals only — never private resident data.'}
        </p>
      </div>
    </div>);
}
