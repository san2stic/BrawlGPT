/**
 * AI coaching insights component with Markdown rendering
 */

import type { ReactElement, ReactNode } from "react";
import type { AiAdviceProps } from "../types";

/**
 * Simple Markdown parser for common patterns
 * Converts basic Markdown to HTML-safe JSX
 */
function parseMarkdown(text: string): ReactElement[] {
  const lines = text.split("\n");
  const elements: ReactElement[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;
  let inCodeBlock = false;
  let codeContent: string[] = [];

  const flushList = () => {
    if (listItems.length > 0 && listType) {
      const ListTag = listType;
      elements.push(
        <ListTag
          key={`list-${elements.length}`}
          className={listType === "ul" ? "list-disc ml-6 my-2" : "list-decimal ml-6 my-2"}
        >
          {listItems.map((item, i) => (
            <li key={i} className="my-1">
              {formatInlineMarkdown(item)}
            </li>
          ))}
        </ListTag>
      );
      listItems = [];
      listType = null;
    }
  };

  const flushCode = () => {
    if (codeContent.length > 0) {
      elements.push(
        <pre
          key={`code-${elements.length}`}
          className="bg-slate-900 p-4 rounded-lg overflow-x-auto my-4 text-sm"
        >
          <code>{codeContent.join("\n")}</code>
        </pre>
      );
      codeContent = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Empty lines
    if (!line.trim()) {
      flushList();
      continue;
    }

    // Headers
    if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h4 key={`h4-${i}`} className="text-lg font-bold text-white mt-4 mb-2">
          {formatInlineMarkdown(line.slice(4))}
        </h4>
      );
      continue;
    }

    if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h3 key={`h3-${i}`} className="text-xl font-bold text-yellow-400 mt-6 mb-3">
          {formatInlineMarkdown(line.slice(3))}
        </h3>
      );
      continue;
    }

    if (line.startsWith("# ")) {
      flushList();
      elements.push(
        <h2 key={`h2-${i}`} className="text-2xl font-black text-white mt-6 mb-4">
          {formatInlineMarkdown(line.slice(2))}
        </h2>
      );
      continue;
    }

    // Horizontal rule
    if (line.match(/^-{3,}$/) || line.match(/^\*{3,}$/)) {
      flushList();
      elements.push(<hr key={`hr-${i}`} className="border-slate-600 my-4" />);
      continue;
    }

    // Unordered list items
    if (line.match(/^[\-\*]\s+/)) {
      if (listType === "ol") flushList();
      listType = "ul";
      listItems.push(line.replace(/^[\-\*]\s+/, ""));
      continue;
    }

    // Ordered list items
    if (line.match(/^\d+\.\s+/)) {
      if (listType === "ul") flushList();
      listType = "ol";
      listItems.push(line.replace(/^\d+\.\s+/, ""));
      continue;
    }

    // Regular paragraph
    flushList();
    elements.push(
      <p key={`p-${i}`} className="text-slate-300 my-2 leading-relaxed">
        {formatInlineMarkdown(line)}
      </p>
    );
  }

  flushList();
  flushCode();

  return elements;
}

/**
 * Format inline markdown (bold, italic, code, links)
 */
function formatInlineMarkdown(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining) {
    // Bold (**text** or __text__)
    let match = remaining.match(/^(.*?)\*\*(.+?)\*\*(.*)/s);
    if (!match) {
      match = remaining.match(/^(.*?)__(.+?)__(.*)/s);
    }
    if (match) {
      if (match[1]) parts.push(match[1]);
      parts.push(
        <strong key={`bold-${key++}`} className="text-yellow-400 font-bold">
          {match[2]}
        </strong>
      );
      remaining = match[3];
      continue;
    }

    // Italic (*text* or _text_)
    match = remaining.match(/^(.*?)\*(.+?)\*(.*)/s);
    if (!match) {
      match = remaining.match(/^(.*?)_(.+?)_(.*)/s);
    }
    if (match) {
      if (match[1]) parts.push(match[1]);
      parts.push(
        <em key={`italic-${key++}`} className="italic text-slate-200">
          {match[2]}
        </em>
      );
      remaining = match[3];
      continue;
    }

    // Inline code (`code`)
    match = remaining.match(/^(.*?)`(.+?)`(.*)/s);
    if (match) {
      if (match[1]) parts.push(match[1]);
      parts.push(
        <code
          key={`code-${key++}`}
          className="bg-slate-700 px-1.5 py-0.5 rounded text-sm font-mono text-pink-400"
        >
          {match[2]}
        </code>
      );
      remaining = match[3];
      continue;
    }

    // No more patterns, add remaining text
    parts.push(remaining);
    break;
  }

  return parts;
}

function AiAdvice({ insights }: AiAdviceProps): ReactElement | null {
  if (!insights) {
    return null;
  }

  return (
    <div className="w-full max-w-4xl mx-auto p-4 mt-8 animate-slide-up">
      <div className="bg-slate-800/80 backdrop-blur-sm rounded-2xl p-6 border border-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.15)] relative overflow-hidden">
        {/* Decorative background element */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2" />

        <h3 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-6 flex items-center gap-2 relative z-10">
          <span>✨</span> AI Coach Insights
        </h3>

        <div className="relative z-10 prose prose-invert max-w-none">
          {parseMarkdown(insights)}
        </div>
      </div>
    </div>
  );
}

export default AiAdvice;
