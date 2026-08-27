class LabValidationError(ValueError):
    """Structured failure for invalid protected Worker Lab data."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
