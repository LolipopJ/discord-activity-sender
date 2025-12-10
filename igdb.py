import asyncio
import time
from typing import Dict, Optional

import aiohttp


class IGDBClient:
    def __init__(
        self,
        timeout: int = 10,
        proxy: Optional[str] = None,
        proxy_auth: Optional[aiohttp.BasicAuth] = None,
    ) -> None:
        self._ready = False
        self._closed = True

        self._client_id = None
        self._client_secret = None

        self._session: aiohttp.ClientSession = None
        self._timeout = timeout
        self._proxy = proxy
        self._proxy_auth = proxy_auth

        self._token: Optional[str] = None
        self._expires_at: float = 0.0

        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_sleep_time: float = 30.0

    async def start(
        self,
        client_id: str,
        client_secret: str,
    ) -> "IGDBClient":
        self._closed = False

        self._client_id = client_id
        self._client_secret = client_secret
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout),
            proxy=self._proxy,
            proxy_auth=self._proxy_auth,
        )

        await self._refresh_token()

        refresh_loop = asyncio.get_running_loop()
        self._refresh_task = refresh_loop.create_task(self._refresh_loop())

        self._ready = True
        return self

    def is_ready(self) -> bool:
        return self._ready

    def is_closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        self._closed = True
        self._ready = False
        if self._refresh_task:
            self._refresh_task.cancel()
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        if not self._session:
            raise RuntimeError("IGDB client session not initialized.")
        if not self._token or time.time() >= self._expires_at:
            raise RuntimeError("IGDB client has no valid access token.")

        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Client-ID", self._client_id)
        headers.setdefault("Authorization", f"Bearer {self._token}")

        async with self._session.request(
            method, url, headers=headers, **kwargs
        ) as resp:
            return resp

    async def _refresh_token(self) -> None:
        print("🔄 Refreshing Twitch access token...")
        result = await self._get_twitch_app_access_token()
        token = result.get("access_token")
        if token:
            try:
                expires_in = int(result.get("expires_in"))
            except Exception:
                expires_in = self._refresh_sleep_time

            self._token = token
            self._expires_at = time.time() + max(0, expires_in)
            print(
                f"✅️ Fetched new Twitch access token (prefix: {token[:8]}), expires in {expires_in} seconds."
            )
        else:
            raise RuntimeError(f"Failed to fetch Twitch access token: {result}.")

    async def _get_twitch_app_access_token(self) -> Dict[str, Optional[str]]:
        client_id = self._client_id
        client_secret = self._client_secret

        if not client_id or not client_secret:
            return {"error": "missing_client_credentials", "status_code": None}

        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }

        try:
            async with self._session.post(url, data=data) as resp:
                status = resp.status
                try:
                    body = await resp.json()
                except Exception:
                    return {"error": "invalid_json_response", "status_code": status}

                if status != 200:
                    return {
                        "error": body.get("message") or body,
                        "status_code": status,
                    }

                return {
                    "access_token": body.get("access_token"),
                    "expires_in": body.get("expires_in"),
                    "token_type": body.get("token_type"),
                }
        except aiohttp.ClientError as e:
            return {"error": f"request_exception: {e}", "status_code": None}

    def _time_until_refresh(self) -> float:
        return max(0.0, self._expires_at - time.time())

    async def _refresh_loop(self) -> None:
        while not self._closed:
            try:
                if self._token and self._expires_at > 0:
                    sleep_for = max(
                        self._refresh_sleep_time, self._time_until_refresh()
                    )
                else:
                    sleep_for = self._refresh_sleep_time
                await asyncio.sleep(sleep_for)
                await self._refresh_token()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌️ Error in refresh Twitch access token loop: {e}")
