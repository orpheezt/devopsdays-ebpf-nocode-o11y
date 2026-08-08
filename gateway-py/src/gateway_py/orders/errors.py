class DownstreamError(Exception):
    def __init__(
        self,
        *,
        service: str,
        reason: str,
        upstream_status: int | None = None,
    ) -> None:
        self.service = service
        self.reason = reason
        self.upstream_status = upstream_status
        detail = f"downstream service '{service}' failed: {reason}"
        if upstream_status is not None:
            detail += f" (status {upstream_status})"
        super().__init__(detail)


class DownstreamTimeoutError(DownstreamError):
    """The downstream call exceeded the configured timeout."""


class DownstreamTransportError(DownstreamError):
    """The downstream service could not be reached (connect/network error)."""


class DownstreamStatusError(DownstreamError):
    """The downstream service answered with a non-2xx status."""
