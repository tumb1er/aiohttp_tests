# coding: utf-8
import asyncio
import collections
from functools import wraps
from unittest import TestCase, mock

from aiohttp_tests.client import TestHttpClient


class BaseTestCase(TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.app = self.init_app(self.loop)
        self.client = TestHttpClient(self.app)
        self._start_patchers()

    def init_patchers(self):
        pass

    def empty_result(self, value=None):
        result = asyncio.Future(loop=self.loop)
        result.set_result(value)
        return result

    def mock(self, *args, **kwargs):
        patcher = mock.patch(*args, **kwargs)
        self._mocks[args[0]] = patcher.start()
        self._patchers[args[0]] = patcher

    def tearDown(self):
        self.loop.run_until_complete(self.app.finish())
        self.loop.stop()
        asyncio.set_event_loop(None)
        self.loop = None
        for p in self._patchers.values():
            p.stop()

    def _start_patchers(self):
        self._patchers = collections.OrderedDict()
        self._mocks = {}
        self.init_patchers()

    def init_app(self, loop):
        raise NotImplementedError()


def async(test_method):
    """
    :param test_method: тест, который нужно вызывать асинхронно
    :type test_method: asyncio.coroutine
    """

    @wraps(test_method)
    def inner(self, *args, **kwargs):
        self.client.async = True
        self.loop.run_until_complete(test_method(self, *args, **kwargs))
    return inner
