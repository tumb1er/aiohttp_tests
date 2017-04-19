# coding: utf-8
import asyncio
from urllib.parse import urlencode

from aiohttp.test_utils import TestClient
from multidict import CIMultiDict


class TestHttpClient:
    peername = ('127.0.0.1', '12345')

    def __init__(self, app, peername=None):
        self.app = app
        self.async = False
        self.loop = asyncio.get_event_loop()
        self.client = TestClient(app, loop=self.loop)
        self.loop.run_until_complete(self.client.start_server())
        if peername:
            self.peername = peername

    @asyncio.coroutine
    def close(self):
        yield from self.client.close()

    @asyncio.coroutine
    def _request(self, method, path, *, body=None, headers=None):
        if not isinstance(path, str):
            path = str(path)
        headers = CIMultiDict(headers or {})

        headers.setdefault('HOST', 'localhost')

        if body is not None:
            if not isinstance(body, bytes):
                body = bytes(body, encoding='utf-8')
            headers.setdefault('CONTENT-LENGTH', str(len(body)))
        resp = yield from self.client.request(method, path, data=body,
                                              headers=headers)

        resp.body = yield from resp.read()
        try:
            resp.text = yield from resp.text()
        except IndexError:
            # chardet failed
            pass
        return resp

    # noinspection PyUnusedLocal
    def request(self, method, path, *, body=None, headers=None):
        coro = self._request(method, path, body=body, headers=headers)
        if self.async:
            return coro
        else:
            return self.app.loop.run_until_complete(coro)

    def get(self, url, headers=None):
        return self.request('GET', url, headers=headers)

    def head(self, url, headers=None):
        return self.request('HEAD', url, headers=headers)

    def delete(self, url, headers=None):
        return self.request('DELETE', url, headers=headers)

    def post(self, url, headers=None, data=None, body=b''):
        if not body and data:
            body = bytes(urlencode(data), encoding="utf-8")
        return self.request('POST', url, body=body, headers=headers)

    def put(self, url, headers=None, data=None, body=b''):
        if not body and data:
            body = bytes(urlencode(data), encoding="utf-8")
        return self.request('PUT', url, body=body, headers=headers)

    def patch(self, url, headers=None, data=None, body=b''):
        if not body and data:
            body = bytes(urlencode(data), encoding="utf-8")
        return self.request('PATCH', url, body=body, headers=headers)
