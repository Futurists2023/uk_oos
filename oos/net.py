"""Shared HTTP session with polite defaults, retries and backoff."""
import time
import warnings

warnings.filterwarnings("ignore", module="requests")  # silence urllib3/chardet version warning

import requests

import config

_session = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "en-GB,en;q=0.9",
        })
    return _session


def get(url: str, **kwargs) -> requests.Response:
    """GET with retries on 429/5xx and network errors (exponential backoff)."""
    kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)
    last_exc = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = session().get(url, **kwargs)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = int(resp.headers.get("Retry-After", 0)) or (5 * 2 ** attempt)
                print(f"    {resp.status_code} on {url} - waiting {wait}s")
                time.sleep(wait)
                continue
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(3 * 2 ** attempt)
    if last_exc:
        raise last_exc
    return resp
