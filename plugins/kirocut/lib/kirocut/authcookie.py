#!/usr/bin/env python3
"""The auth cookie both local servers (home.py, review.py) set, and when it may be framed. Stdlib only.

Opened in a browser tab the page is first-party and the cookie is `SameSite=Strict`: another site open in the same
browser can never send it. Opened inside the IDE (Simple Browser, an extension's webview) the page sits in an iframe
under another origin, where a Strict cookie is not sent and every request of the page would be a 403. So when the
request is plainly a framed one the cookie is `SameSite=None; Secure` (Chrome accepts Secure cookies from 127.0.0.1):

    Sec-Fetch-Dest: iframe | frame | embed | object     the browser says this document is being framed
    Sec-Fetch-Site: cross-site                          the request comes from another site's page
    ?embed=1 on the first URL                           the caller says so (the MCP tool adds it for the IDE panel)

Everything else about the token is unchanged: the 127.0.0.1 / localhost Host check, the token in the URL or the
cookie, the same-origin check on every POST. A framed cookie only helps a page the user already opened with the token.

    python3 authcookie.py demo
"""
import sys
from urllib.parse import parse_qs, urlsplit

FRAMED_DEST = {"iframe", "frame", "embed", "object"}


def framed(headers, path=""):
    """True when this request is for a page shown inside another page."""
    get = lambda k: (headers.get(k) or "").lower()
    if get("Sec-Fetch-Dest") in FRAMED_DEST or get("Sec-Fetch-Site") == "cross-site":
        return True
    return parse_qs(urlsplit(path).query).get("embed", [""])[0] == "1"


def header(handler, name, token):
    """The Set-Cookie value for this request's server."""
    same = "SameSite=None; Secure" if framed(handler.headers, getattr(handler, "path", "")) else "SameSite=Strict"
    return f"{name}={token}; Path=/; HttpOnly; {same}"


def demo():
    class H(dict):
        def get(self, k, d=None):
            return super().get(k, d)
    assert not framed(H(), "/?t=abc")
    assert framed(H({"Sec-Fetch-Dest": "iframe"}))
    assert framed(H({"Sec-Fetch-Site": "cross-site"}))
    assert not framed(H({"Sec-Fetch-Site": "none", "Sec-Fetch-Dest": "document"}), "/?t=abc")
    assert framed(H(), "/?t=abc&embed=1") and not framed(H(), "/?t=abc&embed=0")

    class R:
        headers, path = H(), "/?t=x"
    assert header(R, "c", "tok") == "c=tok; Path=/; HttpOnly; SameSite=Strict"
    R.headers = H({"Sec-Fetch-Dest": "iframe"})
    assert header(R, "c", "tok") == "c=tok; Path=/; HttpOnly; SameSite=None; Secure"
    print("authcookie demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
