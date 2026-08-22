from typing import Any


class ATSException(Exception):
    """
    Base exception for ATS application errors.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error: str = "ATS_ERROR",
        details: Any = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error = error
        self.details = details

        super().__init__(message)

class ResumeUploadError(ATSException):
    """
    Errors related to resume upload and storage.
    """

    def __init__(
        self,
        message: str,
        details: Any = None,
        status_code: int = 400,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error="UPLOAD_ERROR",
            details=details,
        )
        
        
class ResumeParsingError(ATSException):
    """
    Error raised when resume parsing fails.
    """

    def __init__(
            self,
            message: str,
            status_code: int = 422,
            details: Any = None,
        ):
        super().__init__(
            message=message,
            status_code=status_code,
            error="PARSING_ERROR",
            details=details,
        )


class ScoringError(ATSException):
    """
    Error raised when candidate scoring fails.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 422,
        details: Any = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error="SCORING_ERROR",
            details=details,
        )


class RankingError(ATSException):
    """
    Error raised when candidate ranking fails.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 422,
        details: Any = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error="RANKING_ERROR",
            details=details,
        )

class ShortlistingError(ATSException):
    """
    Error raised when candidate shortlisting fails.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 422,
        details: Any = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error="SHORTLISTING_ERROR",
            details=details,
        )