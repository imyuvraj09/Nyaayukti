/**
 * Dedicated RAG Client Service for Nyaayukti.
 * Handles microservice HTTP communication with the Python FastAPI RAG Service.
 * Implements strict timeout management, typed error translation, and response normalization.
 */

const { RAG_SERVICE_URL, RAG_SERVICE_TIMEOUT_MS, RAG_SERVICE_TOKEN } = require('../config/env');
const {
  RAGServiceUnavailableError,
  RAGServiceTimeoutError,
  RAGResponseError,
  AppError,
} = require('../utils/errors');

class RAGService {
  constructor(baseUrl = RAG_SERVICE_URL, timeoutMs = RAG_SERVICE_TIMEOUT_MS) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.timeoutMs = timeoutMs;
  }

  /**
   * Check whether the FastAPI RAG service is reachable and healthy.
   * @returns {Promise<{ available: boolean, details: any }>}
   */
  async checkHealth() {
    const healthUrl = `${this.baseUrl}/api/v1/health`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(healthUrl, {
        method: 'GET',
        redirect: 'error',
        headers: { Accept: 'application/json', 'X-Service-Token': RAG_SERVICE_TOKEN },
        signal: controller.signal,
      });

      if (!response.ok) {
        clearTimeout(timeout);
        return { available: false, details: { status: response.status } };
      }

      const data = await response.json();
      clearTimeout(timeout);
      return { available: true, details: data };
    } catch (err) {
      clearTimeout(timeout);
      return { available: false, details: { error: err.message } };
    }
  }

  /**
   * Submit a legal inquiry to the Python FastAPI RAG service.
   *
   * @param {string} query - Cleaned user question
   * @param {string} [sessionId] - Optional session ID for tracing
   * @returns {Promise<{ content: string, sources: Array, ragMetadata: Object }>}
   */
  async queryLegalRAG(query, sessionId = null, requestId = null, conversationHistory = []) {
    const endpointUrl = `${this.baseUrl}/api/v1/query`;
    const startTime = Date.now();

    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);

    try {
      console.log(
        `[RAG Client] Calling RAG service at ${endpointUrl} (request_id: ${requestId || 'adhoc'}, timeout: ${this.timeoutMs}ms)`,
      );

      const response = await fetch(endpointUrl, {
        method: 'POST',
        redirect: 'error',
        headers: {
          'Content-Type': 'application/json',
          'X-Service-Token': RAG_SERVICE_TOKEN,
          Accept: 'application/json',
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
          request_id: requestId,
          conversation_history: conversationHistory,
        }),
        signal: controller.signal,
      });

      const durationMs = Date.now() - startTime;

      if (!response.ok) {
        // Discard upstream error bodies: they may contain provider details.
        await response.body?.cancel();

        console.error(`[RAG Client] HTTP ${response.status} from RAG service`);

        if (response.status === 429)
          throw new AppError('The answer service is busy. Retry shortly.', 429, 'RAG_BUSY');
        if (response.status === 503) {
          throw new RAGServiceUnavailableError();
        }
        if (response.status === 504 || response.status === 408) {
          throw new RAGServiceTimeoutError();
        }
        throw new RAGResponseError(`RAG service returned HTTP error: ${response.status}`);
      }

      const data = await response.json();
      clearTimeout(timer);

      if (data?.status === 'error') throw new RAGResponseError();

      // Validate required response fields
      if (!data || typeof data !== 'object' || typeof data.answer !== 'string') {
        throw new RAGResponseError('Malformed response payload from AI legal service.');
      }

      // Normalize sources
      const rawSources = Array.isArray(data.sources) ? data.sources : [];
      const normalizedSources = rawSources.map((s, idx) => ({
        sourceNumber: Number(/\[SOURCE (\d+)\]/i.exec(s.source_label || '')?.[1]) || idx + 1,
        sourceLabel: s.source_label || `[SOURCE ${idx + 1}]`,
        documentName: s.document_name || 'Indian Statutory Law',
        chunkId: s.chunk_id || '',
        pageNumbers: Array.isArray(s.page_numbers) ? s.page_numbers : [],
        // Respect empty strings from Python: intentionally suppressed metadata must not reappear.
        // Python sets section_number="" when provision_metadata_verified is false.
        sectionNumber: s.section_number != null && s.section_number !== '' ? s.section_number : null,
        sectionTitle: s.section_title != null && s.section_title !== '' ? s.section_title : null,
        actShortName: s.act_short_name != null && s.act_short_name !== '' ? s.act_short_name : null,
        documentType: s.document_type || 'Statute',
        sourceUrl:
          typeof (s.source_url || s.metadata?.source_url) === 'string' &&
          /^https?:\/\//i.test(s.source_url || s.metadata?.source_url)
            ? (s.source_url || s.metadata?.source_url)
            : null,
        relevanceScore:
          typeof s.reranker_score === 'number'
            ? s.reranker_score
            : typeof s.relevance_score === 'number'
              ? s.relevance_score
              : null,
        snippet: s.text_snippet || s.content_snippet || '',
        evidenceType: s.evidence_type || 'STATUTE',
        caseName: s.case_name || null,
        court: s.court || null,
        citation: s.citation || null,
        paragraphNumber: s.paragraph_number || null,
        isHoldingOrRatio: Boolean(s.is_holding_or_ratio),
      }));

      // Normalize metadata
      const normalizedMetadata = {
        pipeline: data.retrieval_metadata?.pipeline || null,
        retrievalTrace: data.retrieval_metadata || {},
        model: data.model_metadata?.model || null,
        provider: data.model_metadata?.provider || null,
        retrievalDuration: data.retrieval_metadata?.retrieval_seconds ?? null,
        generationError: data.model_metadata?.generation_error || null,
        totalDuration: durationMs,
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
        status: data.status || 'success',
        requestedFacets: Array.isArray(data.requested_facets) ? data.requested_facets : [],
        facetCoverage: data.facet_coverage || {},
        facetValidation: data.facet_validation || {},
        claimValidation: data.claim_validation || {},
        citedSources: Array.isArray(data.claim_validation?.cited_sources)
          ? data.claim_validation.cited_sources
          : [],
        qualityStatus: data.quality_status || 'UNVERIFIED',
        allIssuesAddressed:
          data.facet_validation?.all_issues_addressed ?? (data.quality_status === 'COMPLETE'),
        unresolvedIssues: Array.isArray(data.facet_validation?.unresolved_issues)
          ? data.facet_validation.unresolved_issues
          : [],
        caseLawStatus: data.case_law_status || null,
        evidenceGraph: data.evidence_graph || null,
        generationStatus:
          data.generation_status ||
          (data.status === 'retrieval_only'
            ? 'RETRIEVAL_ONLY'
            : data.status === 'no_sources_found'
              ? 'NO_SOURCES_FOUND'
              : data.status === 'partial_success'
                ? 'PARTIAL_SUCCESS'
                : data.status === 'success'
                  ? 'SUCCESS'
                  : 'UNKNOWN'),
        retrievalStatus: data.retrieval_status || (normalizedSources.length > 0 ? 'SUCCESS' : 'NO_SOURCES_FOUND'),
        validationStatus: data.validation_status || 'NOT_RUN',
        failedStage: data.failed_stage || null,
        errorCategory: data.error_category || data.model_metadata?.generation_error || null,
        retryable: typeof data.retryable === 'boolean' ? data.retryable : false,
        safeUserMessage: data.safe_user_message || null,
        requestId: data.request_id || requestId,
        intentCoverage: data.intent_coverage || null,
      };

      console.log(
        `[RAG Client] RAG response received in ${durationMs}ms with ${normalizedSources.length} sources (status: ${normalizedMetadata.status})`,
      );

      return {
        content: data.answer,
        sources: normalizedSources,
        ragMetadata: normalizedMetadata,
      };
    } catch (err) {
      clearTimeout(timer);

      if (err.name === 'AbortError') {
        console.error(`[RAG Client] Request timed out after ${this.timeoutMs}ms`);
        throw new RAGServiceTimeoutError();
      }

      // Check for connection refusal or DNS resolution failure
      if (
        err.code === 'ECONNREFUSED' ||
        err.code === 'ENOTFOUND' ||
        err.message?.includes('fetch failed') ||
        err.message?.includes('connect ECONNREFUSED')
      ) {
        console.error(
          `[RAG Client] Connection refused to RAG service at ${this.baseUrl}: ${err.message}`,
        );
        throw new RAGServiceUnavailableError();
      }

      // Re-throw our typed errors directly
      if (
        err instanceof AppError ||
        err instanceof RAGServiceUnavailableError ||
        err instanceof RAGServiceTimeoutError ||
        err instanceof RAGResponseError
      ) {
        throw err;
      }

      console.error('[RAG Client] Unexpected error communicating with RAG service:', err.message);
      throw new RAGResponseError('Unable to process AI legal response.');
    }
  }
}

// Singleton instance
const ragService = new RAGService();

module.exports = {
  RAGService,
  ragService,
};
