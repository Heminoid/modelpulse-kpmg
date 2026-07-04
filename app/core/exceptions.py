"""Custom exception hierarchy for ModelPulse."""


class ModelPulseError(Exception):
    """Base exception for all ModelPulse errors."""
    pass


class DatasetNotFoundError(ModelPulseError):
    """Raised when a dataset cannot be found."""
    pass


class MappingNotFoundError(ModelPulseError):
    """Raised when a column mapping cannot be found."""
    pass


class MonitorNotFoundError(ModelPulseError):
    """Raised when a monitor configuration cannot be found."""
    pass


class RunNotFoundError(ModelPulseError):
    """Raised when a monitor run cannot be found."""
    pass


class InvalidFileTypeError(ModelPulseError):
    """Raised when an uploaded file has an unsupported extension."""
    pass


class FileTooLargeError(ModelPulseError):
    """Raised when an uploaded file exceeds the size limit."""
    pass


class InsufficientDataError(ModelPulseError):
    """Raised when there is not enough data to perform an operation."""
    pass
