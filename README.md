aiohttp_tests
=============

Unittest helper utilities for aiohttp-based applications.

Example usage:

```python

import asyncio
import time
from unittest import mock

import aiohttp_tests as at
from aiohttp import web


settings = mock.Mock()


@at.override_settings(settings, SETTINGS_VALUE='new_value')
class ExampleTestCase(at.BaseTestCase):
    """ Aiohttp tests utilities example"""

    @asyncio.coroutine
    def sample_view(self, request):
        text = yield from self.sample_async_method()
        return web.Response(text=text)

    @asyncio.coroutine
    def sample_async_method(self):
        yield from asyncio.sleep(0.1)
        return 'OK'

    def init_app(self, loop):
        """ You must initialize aiohttp application correctly."""
        app = web.Application(loop=loop)
        app.router.add_route('GET', '/', self.sample_view)
        return app

    def init_patchers(self):
        super().init_patchers()
        # Short alias for mock.patch that stores patcher and mock objects
        # locally. Patchers are stopped automatically on teardown.
        # Method is called by BaseTestCase.setUp
        self.mock('time.time', return_value=self.now)

    def setUp(self):
        self.now = time.time()
        super().setUp()

    def testMockUtils(self):
        """ Shows usage of get_mock and get_patcher methods."""
        self.assertEqual(time.time(), self.now)
        self.get_mock('time.time').return_value = self.now - 1
        self.assertEqual(time.time(), self.now - 1)
        self.get_patcher('time.time').stop()
        self.assertGreater(time.time(), self.now)

    def testOverrideSettings(self):
        """ Django-style override_settings decorator for any settings module."""
        self.assertEqual(settings.SETTINGS_VALUE, 'new_value')

        with at.override_settings(settings, SETTINGS_VALUE='other_value'):
            self.assertEqual(settings.SETTINGS_VALUE, 'other_value')

    def testSyncClient(self):
        """ Synchronous execution of requests, with new event loop every time.
        Other HTTP methods, HTTP headers, request body or form/data are also
        supported.
        """
        response = self.client.get('/', headers={'Accept': 'application/json'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.text, 'OK')
        self.assertEqual(response.headers.get('content-type'),
                         'text/plain; charset=utf-8')

        # other HTTP methods
        response = self.client.post('/', body='POST body')
        self.assertEqual(response.status, 405)

        # urlencoded form/data also supported
        response = self.client.request('PUT', '/', data={'field': 'value'})
        self.assertEqual(response.status, 405)

    @at.async_test
    def testAsyncClient(self):
        """ test client requests could be done async, if needed."""

        # you can mock any coroutine to return a 'done' Future with custom
        # result.
        done_future = self.empty_result("async response")

        # mock.patck.object shortcut
        self.mock_object(self, 'sample_async_method', return_value=done_future)
        response = yield from self.client.get('/')
        self.assertEqual(response.text, "async response")

```





