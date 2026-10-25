import { Fragment, useState } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  FileText,
  HelpCircle,
  Share2,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';
import { Link } from 'react-router-dom';

/**
 * Strips raw markdown syntax characters that shouldn't leak to users.
 */
function cleanRawMarkers(value) {
  return String(value ?? '')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/^#+\s*/g, '')
    .replace(/^\*+\s*/g, '');
}

/**
 * Formats inline text safely without raw Markdown syntax leaking to the DOM.
 */
function Inline({ children }) {
  const text = String(children ?? '');
  const parts = text.split(
    /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\)|\[(?:WO-?\d+|Complaint\s*#?\d+|Record:[^\]]+)\])/g
  );

  return parts.map((part, index) => {
    if (!part) return null;

    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      const inner = part.slice(2, -2);
      return <strong key={index} className="font-semibold text-ink">{cleanRawMarkers(inner)}</strong>;
    }

    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={index} className="rounded-xs bg-ink/5 px-1 font-mono text-[0.9em] text-ink">
          {part.slice(1, -1)}
        </code>
      );
    }

    const linkMatch = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(part);
    if (linkMatch) {
      return (
        <a
          key={index}
          href={linkMatch[2]}
          target="_blank"
          rel="noreferrer"
          className="text-brand-ink underline decoration-brand-soft underline-offset-2 hover:text-brand"
        >
          {cleanRawMarkers(linkMatch[1])}
        </a>
      );
    }

    const citeMatch = /^\[((?:WO-?\d+|Complaint\s*#?\d+|Record:[^\]]+))\]$/.exec(part);
    if (citeMatch) {
      return (
        <span
          key={index}
          className="inline-flex items-center rounded border border-line bg-canvas px-1.5 py-0.2 text-[0.78rem] font-medium text-ink-soft"
        >
          {citeMatch[1]}
        </span>
      );
    }

    return <Fragment key={index}>{cleanRawMarkers(part)}</Fragment>;
  });
}

function tableCells(line) {
  return line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
}

function isTableDivider(line) {
  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim());
}

/**
 * Citation Chip Component with role-based deep linking
 */
function sourceDestination(citation, role) {
  const text = typeof citation === 'string' ? citation : citation?.label ?? citation?.title ?? '';
  const workOrder = /\b(?:WO-?(\d+)|(?:assigned\s+)?work\s+order\s+#?(\d+))\b/i.exec(text);
  if (workOrder && (role === 'hoa_admin' || role === 'service_provider')) {
    const id = Number(workOrder[1] ?? workOrder[2]);
    if (Number.isSafeInteger(id) && id > 0) {
      return { to: '/app/work-orders', state: { focusWorkOrderId: id }, label: 'work order', id };
    }
  }

  const complaint = /\bcomplaint\s+#?(\d+)\b/i.exec(text);
  if (complaint && (role === 'hoa_admin' || role === 'resident')) {
    const id = Number(complaint[1]);
    if (Number.isSafeInteger(id) && id > 0) {
      return { to: '/app/complaints', state: { focusComplaintId: id }, label: 'complaint', id };
    }
  }
  return null;
}

export function CitationChip({ citation, role }) {
  const text = typeof citation === 'string' ? citation : citation?.label ?? citation?.title ?? '';
  const destination = sourceDestination(citation, role);
  const className = 'inline-flex items-center gap-1 rounded-sm border border-line bg-canvas px-2 py-1 text-[0.76rem] font-medium text-ink-soft';

  if (destination) {
    return (
      <Link
        to={destination.to}
        state={destination.state}
        aria-label={`Open ${destination.label} ${destination.id}`}
        className={`${className} transition-colors hover:border-brand-soft hover:text-brand-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand`}
      >
        <FileText className="h-3 w-3 text-ink-muted" />
        <Inline>{text}</Inline>
        <ChevronRight className="h-3 w-3 text-ink/45" />
      </Link>
    );
  }
  return (
    <span className={className}>
      <FileText className="h-3 w-3 text-ink-muted" />
      <Inline>{text}</Inline>
    </span>
  );
}

/**
 * Key Finding Callout Box
 */
export function KeyFindingCallout({ summary }) {
  if (!summary) return null;
  return (
    <div className="rounded-xl border border-rose-200/80 bg-rose-50/60 p-4 transition-all">
      <div className="flex items-start gap-2.5">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-700">
          <AlertTriangle className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0">
          <p className="text-[0.72rem] font-bold tracking-wider text-rose-900 uppercase">
            Key finding
          </p>
          <div className="mt-1 text-[0.9rem] font-medium leading-relaxed text-ink">
            <Inline>{summary}</Inline>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Recommended Next Action Card
 */
export function ActionCard({ action, onAct }) {
  if (!action) return null;
  return (
    <div className="rounded-xl border border-brand/25 bg-brand-wash/30 p-4">
      <p className="flex items-center gap-1.5 text-[0.7rem] font-bold tracking-wider text-brand-ink uppercase">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Recommended next action
      </p>
      <div className="mt-1.5 text-[0.88rem] leading-relaxed text-ink/85">
        <Inline>{action}</Inline>
      </div>
    </div>
  );
}

/**
 * Contextual Follow-up Chips ("Explore further")
 */
export function ContextualFollowUps({ followUps = [], onSelect }) {
  if (!followUps || followUps.length === 0) return null;
  return (
    <div className="pt-2">
      <p className="mb-2 flex items-center gap-1.5 text-[0.7rem] font-bold tracking-wider text-ink/45 uppercase">
        <HelpCircle className="h-3.5 w-3.5 text-brand" />
        Explore further
      </p>
      <div className="flex flex-wrap gap-2">
        {followUps.slice(0, 4).map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect?.(prompt)}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-left text-[0.78rem] font-medium text-ink/75 transition-all hover:border-brand-soft hover:bg-canvas hover:text-brand-ink hover:shadow-xs active:scale-98"
          >
            <span>{prompt}</span>
            <ChevronRight className="h-3 w-3 text-ink/40" />
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Action Toolbar: Feedback, Copy, Sources Accordion
 */
export function AnswerToolbar({ answerText, evidence = [], role }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null);

  async function handleCopy() {
    if (!navigator.clipboard?.writeText) return;
    try {
      await navigator.clipboard.writeText(answerText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  function handleFeedback(type) {
    setFeedback((prev) => (prev === type ? null : type));
  }

  return (
    <div className="mt-4 border-t border-line/60 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Left: Feedback buttons */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => handleFeedback('up')}
            aria-label="Mark answer as helpful"
            className={`flex h-7 w-7 items-center justify-center rounded-md border text-xs transition-colors ${
              feedback === 'up'
                ? 'border-brand bg-brand-wash text-brand-ink'
                : 'border-line/70 text-ink/45 hover:border-ink/30 hover:text-ink'
            }`}
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => handleFeedback('down')}
            aria-label="Mark answer as unhelpful"
            className={`flex h-7 w-7 items-center justify-center rounded-md border text-xs transition-colors ${
              feedback === 'down'
                ? 'border-rose-400 bg-rose-50 text-rose-700'
                : 'border-line/70 text-ink/45 hover:border-ink/30 hover:text-ink'
            }`}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
          {feedback ? (
            <span className="ml-1 text-[11px] font-medium text-mint-ink">
              Feedback received
            </span>
          ) : null}
        </div>

        {/* Right: Copy & Sources toggle */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1 rounded-md border border-line/70 bg-surface px-2.5 py-1 text-[0.74rem] font-medium text-ink/65 transition-colors hover:border-ink/30 hover:text-ink"
            aria-label="Copy answer text"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-mint-ink" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {evidence.length > 0 ? (
            <button
              type="button"
              onClick={() => setSourcesOpen((o) => !o)}
              className="inline-flex items-center gap-1 rounded-md border border-line/70 bg-surface px-2.5 py-1 text-[0.74rem] font-medium text-ink/65 transition-colors hover:border-ink/30 hover:text-ink"
              aria-label={`Toggle sources, ${evidence.length} citations available`}
              aria-expanded={sourcesOpen}
            >
              <FileText className="h-3.5 w-3.5 text-brand" />
              <span>Sources ({evidence.length})</span>
              <ChevronDown className={`h-3 w-3 transition-transform ${sourcesOpen ? 'rotate-180' : ''}`} />
            </button>
          ) : null}
        </div>
      </div>

      {/* Expandable Sources Accordion */}
      {sourcesOpen && evidence.length > 0 ? (
        <div className="mt-3 rounded-xl border border-line bg-canvas p-3.5">
          <p className="text-[0.68rem] font-bold tracking-wider text-ink/40 uppercase">
            Traceable Source Records
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {evidence.map((item, idx) => (
              <CitationChip key={idx} citation={item} role={role} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Structured AI Answer Renderer.
 */
export function AiAnswerRenderer({
  content,
  summary,
  evidence = [],
  recommendation,
  related = [],
  onFollowUp,
  role,
  className = '',
}) {
  let structuredSummary = summary;
  let structuredEvidence = evidence;
  let structuredRecommendation = recommendation;
  let structuredRelated = related;
  let rawText = '';

  if (content && typeof content === 'object') {
    structuredSummary = content.summary ?? structuredSummary;
    structuredEvidence = content.evidence ?? structuredEvidence;
    structuredRecommendation = content.recommendation ?? structuredRecommendation;
    structuredRelated = content.related ?? structuredRelated;
    rawText = '';
  } else {
    rawText = String(content ?? '');
  }

  const lines = rawText.replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }

    if (index + 1 < lines.length && line.includes('|') && isTableDivider(lines[index + 1])) {
      const headers = tableCells(line);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].trim().includes('|')) {
        rows.push(tableCells(lines[index]));
        index += 1;
      }
      blocks.push(
        <div key={`table-${index}`} className="my-2 overflow-x-auto border border-line">
          <table className="min-w-full text-left text-[0.82rem]">
            <thead className="bg-canvas text-ink/60">
              <tr>
                {headers.map((header, cellIndex) => (
                  <th key={cellIndex} scope="col" className="px-3 py-2 font-semibold">
                    <Inline>{header}</Inline>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-t border-line">
                  {headers.map((_, cellIndex) => (
                    <td key={cellIndex} className="px-3 py-2">
                      <Inline>{row[cellIndex] ?? ''}</Inline>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      const level = Math.min(4, heading[1].length + 1);
      const Tag = `h${level}`;
      const headingText = heading[2];

      blocks.push(
        <Tag
          key={`heading-${index}`}
          className="font-heading text-[0.98rem] font-semibold text-ink pt-1"
        >
          <Inline>{headingText}</Inline>
        </Tag>
      );
      index += 1;
      continue;
    }

    const quote = /^>\s?(.+)$/.exec(line);
    if (quote) {
      blocks.push(
        <blockquote
          key={`quote-${index}`}
          className="border-l-2 border-brand-soft pl-3 text-ink/65 italic"
        >
          <Inline>{quote[1]}</Inline>
        </blockquote>
      );
      index += 1;
      continue;
    }

    const bullet = /^[-*+]\s+(.+)$/.exec(line);
    const ordered = /^\d+[.)]\s+(.+)$/.exec(line);
    if (bullet || ordered) {
      const List = ordered ? 'ol' : 'ul';
      const items = [];
      while (index < lines.length) {
        const itemLine = lines[index].trim();
        const match = ordered
          ? /^\d+[.)]\s+(.+)$/.exec(itemLine)
          : /^[-*+]\s+(.+)$/.exec(itemLine);
        if (!match) break;
        items.push(
          <li key={index} className="leading-snug">
            <Inline>{match[1]}</Inline>
          </li>
        );
        index += 1;
      }
      blocks.push(
        <List
          key={`list-${index}`}
          className={ordered ? 'list-decimal space-y-1 pl-5' : 'list-disc space-y-1 pl-5'}
        >
          {items}
        </List>
      );
      continue;
    }

    const paragraph = [line];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+|^[-*+]\s+|^\d+[.)]\s+/.test(lines[index].trim())
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(
      <p key={`paragraph-${index}`} className="leading-relaxed">
        <Inline>{paragraph.join(' ')}</Inline>
      </p>
    );
  }

  const plainAnswerText = [
    structuredSummary,
    rawText,
    structuredRecommendation ? `Recommended action: ${structuredRecommendation}` : '',
  ]
    .filter(Boolean)
    .join('\n\n');

  return (
    <div className={`space-y-3.5 text-[0.88rem] leading-relaxed text-ink/80 ${className}`}>
      {/* 1. Key finding callout at top */}
      {structuredSummary ? (
        <KeyFindingCallout summary={structuredSummary} />
      ) : null}

      {/* Main rendered text blocks */}
      {blocks}

      {/* 2. Evidence citation chips */}
      {structuredEvidence && structuredEvidence.length > 0 ? (
        <div className="pt-1">
          <p className="mb-1.5 flex items-center gap-1.5 text-[0.68rem] font-bold tracking-wider text-ink/45 uppercase">
            <FileText className="h-3 w-3 text-brand" /> Evidence & Records
          </p>
          <div className="flex flex-wrap gap-1.5">
            {structuredEvidence.map((item, idx) => (
              <CitationChip key={idx} citation={item} role={role} />
            ))}
          </div>
        </div>
      ) : null}

      {/* 3. Recommended Next Action Card */}
      {structuredRecommendation ? (
        <ActionCard action={structuredRecommendation} />
      ) : null}

      {/* 4. Contextual Follow-up Chips ("Explore further") */}
      {structuredRelated && structuredRelated.length > 0 ? (
        <ContextualFollowUps followUps={structuredRelated} onSelect={onFollowUp} />
      ) : null}

      {/* 5. Interactive Action Toolbar (Feedback, Copy, Sources) */}
      <AnswerToolbar
        answerText={plainAnswerText}
        evidence={structuredEvidence ?? []}
        role={role}
      />
    </div>
  );
}
