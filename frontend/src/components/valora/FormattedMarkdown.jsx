import React from 'react';

/**
 * Lightweight, zero-dependency Markdown parser designed for VALORA Intelligence responses.
 * Renders executive headings, bold text, numbered operational steps, bullet lists,
 * and key-value metadata with clean, restrained South African estate typography.
 */
function parseInline(text) {
  if (!text) return text;

  // Split on bold (**text**) and code (`text`)
  const parts = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold text-ink">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={match.index}
          className="rounded border border-line bg-canvas px-1 py-0.5 font-mono text-[0.8rem] text-ink/90"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

export function FormattedMarkdown({ content, className = '' }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let listKey = 0;

  function flushList() {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${listKey++}`} className="my-2.5 space-y-1.5 pl-1">
          {currentList}
        </ul>
      );
      currentList = [];
    }
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Empty line -> flush list and skip
    if (!trimmed) {
      flushList();
      return;
    }

    // 1. Markdown Headings (### or ## or #)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const text = headingMatch[2];
      if (level <= 2) {
        elements.push(
          <h4
            key={index}
            className="mt-4 mb-2 border-b border-line/60 pb-1 text-[0.78rem] font-bold tracking-[0.12em] text-brand-ink uppercase"
          >
            {parseInline(text)}
          </h4>
        );
      } else {
        elements.push(
          <h5
            key={index}
            className="mt-3 mb-1 text-[0.88rem] font-semibold tracking-tight text-ink"
          >
            {parseInline(text)}
          </h5>
        );
      }
      return;
    }

    // 2. Bold Section Titles, e.g. **OPERATIONAL ANALYSIS: ...**
    const boldHeaderMatch = trimmed.match(/^\*\*([A-Z0-9\s:—–\-_/]+)\*\*$/);
    if (boldHeaderMatch) {
      flushList();
      elements.push(
        <div
          key={index}
          className="mt-4 mb-2 flex items-center gap-2 border-b border-line/60 pb-1.5 text-[0.75rem] font-bold tracking-[0.14em] text-brand-ink uppercase"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-brand" />
          <span>{boldHeaderMatch[1]}</span>
        </div>
      );
      return;
    }

    // 3. Numbered Recommendations / Steps, e.g. **1. Erosion of the Living Score** or 1. Issue
    const numberedMatch = trimmed.match(/^(\*{0,2})(\d+)\.\s+([^*]+)(\*{0,2})(.*)/);
    if (numberedMatch && (numberedMatch[1] === '**' || trimmed.startsWith(numberedMatch[2] + '.'))) {
      flushList();
      const num = numberedMatch[2];
      const title = numberedMatch[3];
      const rest = numberedMatch[5] || '';
      elements.push(
        <div key={index} className="mt-3 mb-1.5 flex items-start gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-brand-wash text-[11px] font-bold font-mono text-brand-ink">
            {num}
          </span>
          <div className="text-[0.9rem] font-semibold text-ink leading-snug">
            {title}
            {rest && <span className="font-normal text-ink/80">{parseInline(rest)}</span>}
          </div>
        </div>
      );
      return;
    }

    // 4. Key-Value Metadata lines, e.g. **Estate:** Silverleaf | **Status:** ...
    if (trimmed.startsWith('**') && trimmed.includes(':**')) {
      flushList();
      elements.push(
        <div
          key={index}
          className="my-1.5 flex flex-wrap items-center gap-2 rounded-lg bg-canvas/70 px-3 py-1.5 text-xs text-ink/75"
        >
          {parseInline(trimmed)}
        </div>
      );
      return;
    }

    // 5. Bullet List Item (- or * )
    const bulletMatch = trimmed.match(/^[-*]\s+(.+)/);
    if (bulletMatch) {
      currentList.push(
        <li key={index} className="flex items-start gap-2 text-[0.875rem] leading-relaxed text-ink/80">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand/70" />
          <span>{parseInline(bulletMatch[1])}</span>
        </li>
      );
      return;
    }

    // Default: Regular Paragraph
    flushList();
    elements.push(
      <p key={index} className="my-2 text-[0.88rem] leading-relaxed text-ink/85">
        {parseInline(trimmed)}
      </p>
    );
  });

  flushList();

  return <div className={`formatted-ai-response ${className}`}>{elements}</div>;
}
