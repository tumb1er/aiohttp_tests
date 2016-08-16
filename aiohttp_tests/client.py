# coding: utf-8
import asyncio
import http.cookies
from unittest import mock
from urllib.parse import urlencode

from aiohttp import protocol, StreamReader, parsers, web, CIMultiDict
from aiohttp.client_reqrep import hdrs
from aiohttp.streams import EmptyStreamReader


class ResponseParser:
    """ Parses byte stream from HttpBuffer.
    """

    def __init__(self, buffer):
        self.buffer = buffer
        self.message = self.response = self.feed_data = None
        self.eof_found = False

    # noinspection PyUnusedLocal
    def parse_http_message(self, message, length):
        """ Parses HTTP headers."""
        self.message = message
        self.response = web.Response(reason=message.reason,
                                     status=message.code,
                                     headers=message.headers,
                                     body=b'')

        self.response._cookies = http.cookies.SimpleCookie()
        if hdrs.SET_COOKIE in message.headers:
            for hdr in message.headers.getall(hdrs.SET_COOKIE):
                self.response.cookies.load(hdr)

    # noinspection PyUnusedLocal
    def parse_http_content(self, content, length):
        """ Parses response body, dealing with transfer-encodings."""
        self.response.body += content

    def feed_eof(self):
        self.eof_found = True

    def __call__(self):
        parser = protocol.HttpResponseParser()
        self.feed_data = self.parse_http_message
        yield from parser(self, self.buffer)
        if not self.eof_found or self.buffer:
            parser = protocol.HttpPayloadParser(self.message)
            self.feed_data = self.parse_http_content
            yield from parser(self, self.buffer)
        return self.response


class TestHttpClient:
    peername = ('127.0.0.1', '12345')

    def __init__(self, app, peername=None):
        self.app = app
        self.async = False
        if peername:
            self.peername = peername

    @asyncio.coroutine
    def _request(self, method, path, *, body=None, headers=None):
        headers = headers or {}
        request_factory = self.app.make_handler()
        handler = request_factory()
        tr = mock.Mock()
        extra_info = {
            'peername': self.peername,
            'socket': mock.MagicMock(),
        }
        tr.get_extra_info = mock.Mock(side_effect=extra_info.get)
        handler.connection_made(tr)

        _headers = CIMultiDict(
            HOST='localhost',
        )
        _raw_headers = [
            (b'Host', b'localhost')
        ]

        if body is not None:
            headers.setdefault('CONTENT-LENGTH', str(len(body)))
            if not isinstance(body, bytes):
                body = bytes(body, encoding='utf-8')

        if headers:
            _headers.update(headers)
            for k, v in headers.items():
                _raw_headers.append(
                    (bytes(k, encoding='ascii'), bytes(v, encoding='ascii')))
        msg = protocol.RawRequestMessage(
                method, path, protocol.HttpVersion10, _headers, _raw_headers,
                should_close=True, compression=None)
        if body:
            payload = StreamReader(loop=self.app.loop)
            payload.feed_data(body)
            payload.feed_eof()
        else:
            payload = EmptyStreamReader()
        yield from handler.handle_request(msg, payload)

        data = b''.join(call[0][0] for call in tr.write.call_args_list)

        buffer = parsers.ParserBuffer(data)

        response_parser = ResponseParser(buffer)
        response = yield from response_parser()
        if not response.body and data:
            # aiohttp does not read response body without content-length and
            # chunked encoding
            response._body = bytes(buffer._data)
        handler.connection_lost(None)
        return response

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

    def close(self):
        self.app.loop.run_until_complete(self.app.finish())
