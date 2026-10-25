import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { normaliseCitations, sourceAnchor } from '../../utils/citations';

// Transform text nodes only: code, escaped text and existing links remain intact.
function citationLinks(scope, available) {
  return () => (tree) => {
    function walk(node) {
      if (!node.children || ['link', 'code', 'inlineCode'].includes(node.type)) return;
      node.children = node.children.flatMap((child) => {
        if (child.type !== 'text') {
          walk(child);
          return [child];
        }
        const parts = [];
        let cursor = 0;
        for (const match of child.value.matchAll(/\[SOURCE\s+(\d+)\]/gi)) {
          parts.push({ type: 'text', value: child.value.slice(cursor, match.index) });
          const number = Number(match[1]);
          parts.push(
            available.has(number)
              ? {
                  type: 'link',
                  url: `#${sourceAnchor(scope, number)}`,
                  children: [{ type: 'text', value: `[${number}]` }],
                }
              : { type: 'text', value: '[source unavailable]' },
          );
          cursor = match.index + match[0].length;
        }
        parts.push({ type: 'text', value: child.value.slice(cursor) });
        return parts;
      });
    }
    walk(tree);
  };
}
export default function LegalMarkdown({ content, scope = 'answer', available = new Set() }) {
  return (
    <div className="legal-markdown">
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm, citationLinks(scope, available)]}
        components={{
          img: () => null,
          a: ({ href, children }) => {
            const local = href?.startsWith(`#${scope}-source-`);
            if (!local) return <span>{children}</span>; // Model-generated URLs are not evidence.
            return (
              <a
                href={href}
                onClick={(event) => {
                  event.preventDefault();
                  const target = document.getElementById(href.slice(1));
                  if (target) {
                    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
                      if (parent.tagName === 'DETAILS') parent.open = true;
                    }
                    target.open = true;
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    target.focus();
                  }
                }}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {normaliseCitations(content)}
      </ReactMarkdown>
    </div>
  );
}
