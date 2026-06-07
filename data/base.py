from __future__ import annotations

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


retry_on_request_error = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
