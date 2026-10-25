import { useId } from 'react';
import LegalMarkdown from './LegalMarkdown';
import SourceCitation from './SourceCitation';
import { citedNumbers } from '../../utils/citations';
import { parseStructuredResponse } from '../../utils/responseParser';
export default function ChatMessage({ message, onRetry }) {
  const scope = `answer-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const isUser = message.role === 'user';
  let content = typeof message.content === 'string' ? message.content : '';
  const legacy = !isUser && parseStructuredResponse(content);
  if (legacy)
    content = [
      legacy.mainAnswer,
      legacy.legalBasis,
      ...(legacy.recommendedNextSteps || []).map((step) => `- ${step}`),
    ]
      .filter(Boolean)
      .join('\n\n');
  const sources = (message.sources || []).map((source, index) => ({
    ...source,
    sourceNumber:
      Number(/\[SOURCE (\d+)\]/i.exec(source.sourceLabel || source.source_label || '')?.[1]) ||
      source.sourceNumber ||
      index + 1,
  }));
  const cited = citedNumbers(content);
  const used = sources.filter((source) => cited.has(source.sourceNumber));
  const additional = sources.filter((source) => !cited.has(source.sourceNumber));
  const metadata = message.ragMetadata || message.metadata || {};
  const isRetrievalOnly =
    metadata.generationStatus === 'RETRIEVAL_ONLY' || metadata.status === 'retrieval_only';

  const defaultNotice =
    metadata.safeUserMessage ||
    content ||
    'We found potentially relevant sources, but could not complete the answer. You can retry or inspect the retrieved passages below.';

  return (
    <article className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}>
      {isUser ? (
        <p className="user-content">{content}</p>
      ) : (
        <>
          {isRetrievalOnly ? (
            <div role="status" className="answer-notice retrieval-only-notice">
              <p className="notice-message">{defaultNotice}</p>
              {metadata.retryable && onRetry && (
                <button
                  type="button"
                  className="retry-action-btn"
                  onClick={() => onRetry(message)}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginRight: '6px', verticalAlign: '-2px' }}
                  >
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                  </svg>
                  Retry query
                </button>
              )}
            </div>
          ) : (
            <>
              {(metadata.qualityStatus === 'PARTIALLY_COMPLETE' ||
                metadata.generationStatus === 'PARTIAL_SUCCESS') && (
                <p role="status" className="answer-notice partial-notice">
                  Partial answer — some requested issues could not be confirmed from available statutory evidence.
                </p>
              )}
              {metadata.generationStatus === 'INSUFFICIENT_EVIDENCE' && (
                <p role="status" className="answer-notice insufficient-notice">
                  The available statutory corpus did not contain sufficient evidence to answer the core issues.
                </p>
              )}

              <LegalMarkdown
                content={content}
                scope={scope}
                available={new Set(sources.map((s) => s.sourceNumber))}
              />

              {used.length > 0 && (
                <section aria-label="Sources cited">
                  <h4>Sources cited ({used.length})</h4>
                  {used.map((source) => (
                    <SourceCitation key={source.sourceNumber} source={source} scope={scope} />
                  ))}
                </section>
              )}

              {additional.length > 0 && (
                <details className="additional-sources">
                  <summary>Additional retrieved sources ({additional.length})</summary>
                  {additional.map((source) => (
                    <SourceCitation key={source.sourceNumber} source={source} scope={scope} />
                  ))}
                </details>
              )}
            </>
          )}

          {isRetrievalOnly && sources.length > 0 && (
            <details className="retrieved-passages-section">
              <summary className="retrieved-passages-summary">
                Retrieved passages — not analyzed ({sources.length})
              </summary>
              <div className="retrieved-passages-body">
                <p className="retrieval-disclaimer">
                  The following statutory passages were retrieved as potentially relevant context, but no AI legal analysis could be completed. These excerpts are not a completed answer and do not constitute legal advice.
                </p>
                {/* Top 3 most relevant excerpts */}
                {sources.slice(0, 3).map((source) => (
                  <SourceCitation key={source.sourceNumber} source={source} scope={scope} />
                ))}
                {/* Inspection toggle for remaining results if > 3 */}
                {sources.length > 3 && (
                  <details className="additional-retrieved-passages" style={{ marginTop: '0.5rem' }}>
                    <summary style={{ cursor: 'pointer', color: '#0f766e', fontWeight: 500 }}>
                      Inspect additional results ({sources.length - 3} more)
                    </summary>
                    <div style={{ marginTop: '0.4rem' }}>
                      {sources.slice(3).map((source) => (
                        <SourceCitation key={source.sourceNumber} source={source} scope={scope} />
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </details>
          )}

          {metadata.pipeline && (
            <details className="additional-sources">
              <summary>Answer processing details</summary>
              <p>Pipeline: {metadata.pipeline}</p>
              <p>
                Generation: {metadata.generationStatus || 'N/A'}; review: {metadata.validationStatus || 'N/A'}
              </p>
              <p>
                Coverage: {metadata.qualityStatus || 'UNVERIFIED'}
              </p>
              <p>
                Planned issues: {metadata.allIssuesAddressed ? 'All planned issues addressed' : 'Partial (unresolved issues remain)'}
              </p>
              <p>
                Retrieved sources in context:{' '}
                {metadata.retrievalTrace?.context_source_count ?? sources.length}
              </p>
              {typeof metadata.retrievalDuration === 'number' && (
                <p>Retrieval duration: {metadata.retrievalDuration.toFixed(2)}s</p>
              )}
              {metadata.failedStage && <p>Failed stage: {metadata.failedStage}</p>}
              {metadata.errorCategory && <p>Error category: {metadata.errorCategory}</p>}
              <p>Request: {metadata.requestId || 'unavailable'}</p>
              <p>Notice: &ldquo;All planned issues addressed&rdquo; indicates coverage of planned issues only, not certified legal accuracy.</p>
              <p>Automatic review is an automated consistency check, not expert legal verification.</p>
            </details>
          )}

          <small className="answer-note">
            Academic prototype. Sources support review; they do not guarantee legal correctness.
          </small>
        </>
      )}
      {message.timestamp && <time className="message-time">{message.timestamp}</time>}
    </article>
  );
}
