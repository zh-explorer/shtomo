# this code if copy from urllib3
# https://github.com/urllib3/urllib3/blob/2ac40569acb464074bdc3f308124d781d6aa0860/src/urllib3/contrib/socks.py#L178C38-L178C38
from __future__ import annotations

from urllib.parse import urlparse
import socks


class SOCKSProxyManager():
    def __init__(
            self,
            proxy_url: str,
            username: str | None = None,
            password: str | None = None,
    ):
        parsed = urlparse(proxy_url)

        if username is None and password is None and parsed.username is not None:
            username, password = parsed.username , parsed.password
        if parsed.scheme == "socks5":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = False
        elif parsed.scheme == "socks5h":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = True
        elif parsed.scheme == "socks4":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = False
        elif parsed.scheme == "socks4a":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = True
        else:
            raise ValueError(f"Unable to determine SOCKS version from {proxy_url}")

        self.proxy_url = proxy_url

        self.socks_options = {
            "socks_version": socks_version,
            "proxy_host": parsed.hostname,
            "proxy_port": parsed.port,
            "username": username,
            "password": password,
            "rdns": rdns,
        }
