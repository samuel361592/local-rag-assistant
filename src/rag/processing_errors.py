"""User-facing errors shared by the document loaders."""


class DocumentProcessingError(RuntimeError):
    """A document processing failure safe to display to the user."""


class PDFProcessingError(DocumentProcessingError):
    """PDF/image processing failure (keeps the original public exception)."""


class ExcelProcessingError(DocumentProcessingError):
    """Excel processing failure safe to display to the user."""
