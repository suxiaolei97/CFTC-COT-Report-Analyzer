import sys
import os
import socket

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

import requests

_original_get = requests.get
_original_request = requests.Session.request


def _get(*args, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30
    return _original_get(*args, **kwargs)


def _request(self, method, url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30
    return _original_request(self, method, url, **kwargs)


requests.get = _get
requests.Session.request = _request
socket.setdefaulttimeout(30)

from app import CotTui


def main() -> None:
    app = CotTui()
    app.run()


if __name__ == "__main__":
    main()
