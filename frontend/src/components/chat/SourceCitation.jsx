import { sourceAnchor } from '../../utils/citations';

export default function SourceCitation({ source, scope }) {
  const pages = source.pageNumbers || source.page_numbers || [];
  // Only display section metadata that survived Python-side verification.
  // Empty strings are intentional suppressions, not missing values.
  const sectionNumber = (source.sectionNumber || source.section_number) || null;
  const sectionTitle = (source.sectionTitle || source.section_title) || null;
  const docName = source.documentName || source.document_name || 'Source document';
  const isConstitution = docName.toLowerCase().includes('constitution');
  const provisionPrefix = isConstitution ? 'Article' : 'Section';

  // Only display official source link if present in trusted corpus metadata and HTTP/HTTPS
  const rawUrl = source.sourceUrl || source.source_url;
  const sourceUrl =
    typeof rawUrl === 'string' && /^https?:\/\//i.test(rawUrl) ? rawUrl : null;

  return (
    <details className="source-card" id={sourceAnchor(scope, source.sourceNumber)} tabIndex={-1}>
      <summary>
        <strong>
          [{source.sourceNumber}] {docName}
          {sectionNumber && ` — ${provisionPrefix} ${sectionNumber}`}
          {sectionTitle && ` (${sectionTitle})`}
        </strong>
        {pages.length > 0 && (
          <small className="source-pages">PDF page {pages.join(', ')}</small>
        )}
      </summary>
      <div className="source-details">
        {source.documentType && (
          <small className="source-doc-type">{source.documentType}</small>
        )}
        <p className="source-excerpt">
          {source.snippet || source.content_snippet || source.text_snippet || 'No excerpt available.'}
        </p>
        {sourceUrl && (
          <div className="source-link">
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="source-external-url"
            >
              View official document source ↗
            </a>
          </div>
        )}
      </div>
    </details>
  );
}
