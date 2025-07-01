# app/core/exceptions.py

class ServiceUnavailable(Exception):
    """Raised when an upstream service (retrieval or LLM) fails."""
    pass


class BadGateway(Exception):
    """Raised when an external dependency returns an unexpected response."""
    pass
