"""Stable public retrieval errors; causes are for logs, never for the UI."""

class RetrievalError(RuntimeError):
    error_code = "INTERNAL_RETRIEVAL_ERROR"

    def __init__(self, message="檢索失敗，請稍後重試。", *, cause=None):
        super().__init__(message)
        self.user_message = message
        self._cause = cause

    @property
    def cause(self):
        return self._cause or self.__cause__


class DegradableRetrievalError(RetrievalError):
    pass


class UserInputError(RetrievalError, ValueError):
    error_code = "USER_INPUT_INVALID"


class DenseRetrievalError(DegradableRetrievalError):
    error_code = "DENSE_RETRIEVAL_FAILED"


class BM25SearchError(DegradableRetrievalError):
    error_code = "BM25_SEARCH_FAILED"


class RerankerOperationalError(DegradableRetrievalError):
    error_code = "RERANKER_OPERATIONAL_FAILED"


class RerankerOutputError(DegradableRetrievalError, ValueError):
    error_code = "RERANKER_OUTPUT_INVALID"


class RerankerIntegrityError(RetrievalError):
    error_code = "RERANKER_INTEGRITY_FAILED"


class RetrievalInvariantError(RetrievalError):
    error_code = "RETRIEVAL_INVARIANT_VIOLATION"


class KnowledgeStateError(RetrievalError):
    error_code = "KNOWLEDGE_STATE_INVALID"


class RetrievalConfigError(RetrievalError, ValueError):
    error_code = "RETRIEVAL_CONFIG_INVALID"
