"""CommuneClient — thin httpx wrapper with API key auth.

Auth: Authorization: Bearer comm_...

Raises:
  httpx.ConnectError / httpx.TimeoutException — caller wraps with network_error()
  All non-2xx responses — caller checks response.is_success and calls api_error()
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .state import AppState

DEFAULT_TIMEOUT = 30.0


class CommuneClient:
    """HTTP client for the Commune API.

    Usage:
        client = CommuneClient.from_state(state)
        r = client.get("/v1/domains")
        if not r.is_success:
            api_error(r, json_output=state.should_json())
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_state(cls, state: AppState) -> "CommuneClient":
        return cls(
            base_url=state.base_url,
            api_key=state.api_key,
            timeout=DEFAULT_TIMEOUT,
        )

    def _base_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "commune-cli/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _url(self, path: str) -> str:
        return self.base_url + path

    def _req(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[bytes] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        headers = self._base_headers()
        if extra_headers:
            headers.update(extra_headers)
        if data is not None:
            headers.pop("Content-Type", None)

        if params:
            params = {k: v for k, v in params.items() if v is not None}

        with httpx.Client(timeout=self.timeout) as client:
            return client.request(
                method,
                self._url(path),
                headers=headers,
                params=params or None,
                json=json,
                content=data,
            )

    def get(self, path: str, *, params: Optional[dict[str, Any]] = None) -> httpx.Response:
        return self._req("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        data: Optional[bytes] = None,
        extra_headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        return self._req("POST", path, json=json, data=data, extra_headers=extra_headers, params=params)

    def patch(self, path: str, *, json: Optional[Any] = None) -> httpx.Response:
        return self._req("PATCH", path, json=json)

    def delete(self, path: str, *, params: Optional[dict[str, Any]] = None) -> httpx.Response:
        return self._req("DELETE", path, params=params)

    def put(self, path: str, *, json: Optional[Any] = None) -> httpx.Response:
        return self._req("PUT", path, json=json)
