import { Fragment } from 'react';
import { ArrowRight, CheckCircle2, ChevronRight, FileText, Link2, Sparkles } from 'lucide-react';

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
  // Match bold (**text** or __text__), code (`code`), citations ([WO-123]), and links ([text](url))
  const parts = text.split(
    /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\)|\[(?:WO-?\d+|Complaint\s*#?\d+|Record:[^\]]+)\])/g
  );

  return parts.map((part, index) => {
    if (!part) return null;

    // Bold (**text** or __text__)
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      const inner = part.slice(2, -2);
      return <strong key={index} className="font-semibold text-ink">{cleanRawMarkers(inner)}</strong>;
    }

    // Inline code (`code`)
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={index} className="rounded-xs bg-ink/5 px-1 font-mono text-[0.9em] text-ink">
          {part.slice(1, -1)}
        </code>
      );
    }

    // Markdown link [label](url)
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

    // Citation badge [WO-0042] or [Complaint #7]
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
 * Citation Chip Component
 */
export function CitationChip({ citation, onClick }) {
  const text = typeof citation === 'string' ? citation : citation?.label ?? citation?.title ?? '';
  return (
    <span className="inline-flex items-center gap-1 rounded-sm border border-line/80 bg-canvas px-2 py-0.5 text-[0.76rem] font-medium text-ink-soft">
      <FileText className="h-3 w-3 text-ink-muted" />
      <Inline>{text}</Inline>
    </span>
  );
}

/**
 * Recommended Next Action Card
 */
export function ActionCard({ action, onAct }) {
  if (!action) return null;
  return (
    <div className="rounded-md border border-brand/25 bg-brand-wash/30 p-3.5">
      <p className="flex items-center gap-1.5 text-[0.68rem] font-semibold tracking-wider text-brand-ink uppercase">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Recommended next action
      </p>
      <div className="mt-1.5 text-[0.85rem] leading-relaxed text-ink/80">
        <Inline>{action}</Inline>
      </div>
    </div>
  );
}

/**
 * Contextual Follow-up Prompts
 */
export function ContextualFollowUps({ followUps = [], onSelect }) {
  if (!followUps || followUps.length === 0) return null;
  return (
    <div className="pt-2">
      <p className="mb-1.5 flex items-center gap-1 text-[0.66rem] font-semibold tracking-wider text-ink/45 uppercase">
        <Sparkles className="h-3 w-3" />
        Suggested follow-up
      </p>
      <div className="flex flex-wrap gap-1.5">
        {followUps.slice(0, 3).map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect?.(prompt)}
            className="inline-flex items-center gap-1 rounded border border-line bg-surface px-2.5 py-1 text-left text-[0.76rem] font-medium text-ink/70 transition-all hover:border-brand-soft hover:bg-canvas hover:text-brand-ink"
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
 * Structured AI Answer Renderer.
 * Supports:
 * - Direct takeaway / key finding at top
 * - Evidence & record citations
 * - Recommended next action card
 * - Contextual follow-up chips
 * - Safe markdown formatting with ZERO raw markdown markers (**bold**, ###, etc.)
 */
export function AiAnswerRenderer({
  content,
  summary,
  evidence = [],
  recommendation,
  related = [],
  onFollowUp,
  className = '',
}) {
  // If content is an object (e.g. AskValoraResponse schema), extract its structured properties
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

  // Parse markdown lines for textual content
  const lines = rawText.replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }

    // Markdown tables
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

    // Headings (##, ###)
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

    // Blockquote
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

    // Lists (bullet and numbered)
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

    // Paragraph
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

  return (
    <div className={`space-y-3.5 text-[0.88rem] leading-relaxed text-ink/80 ${className}`}>
      {/* 1. Direct takeaway / Structured summary at top */}
      {structuredSummary ? (
        <div className="rounded-md border border-line/70 bg-canvas/60 p-3 font-medium text-ink">
          <Inline>{structuredSummary}</Inline>
        </div>
      ) : null}

      {/* Main rendered text blocks */}
      {blocks}

      {/* 2. Evidence / Record Citation Chips */}
      {structuredEvidence && structuredEvidence.length > 0 ? (
        <div className="pt-1">
          <p className="mb-1.5 flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-wider text-ink/45 uppercase">
            <FileText className="h-3 w-3" /> Evidence & Records
          </p>
          <div className="flex flex-wrap gap-1.5">
            {structuredEvidence.map((item, idx) => (
              <CitationChip key={idx} citation={item} />
            ))}
          </div>
        </div>
      ) : null}

      {/* 3. Recommended Next Action Card */}
      {structuredRecommendation ? (
        <ActionCard action={structuredRecommendation} />
      ) : null}

      {/* 4. Contextual Follow-up Chips */}
      {structuredRelated && structuredRelated.length > 0 ? (
        <ContextualFollowUps followUps={structuredRelated} onSelect={onFollowUp} />
      ) : null}
    </div>
  );
}
