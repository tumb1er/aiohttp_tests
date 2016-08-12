# coding: utf-8
import inspect

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

    def finished_coroutine(self, value=None):
        @asyncio.coroutine
        def coro(*args, **kwargs):
            return value
        return coro

    def mock(self, *args, **kwargs):
        patcher = mock.patch(*args, **kwargs)
        self._mocks[args[0]] = patcher.start()
        self._patchers[args[0]] = patcher

    def mock_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self._mocks[args[0]] = patcher.start()
        self._patchers[args[0]] = patcher

    def get_mock(self, name):
        return self._mocks[name]

    def get_patcher(self, name):
        return self._patchers[name]

    def tearDown(self):
        self.cleanup_app()
        self.loop.stop()
        asyncio.set_event_loop(None)
        self.loop = None
        for p in self._patchers.values():
            if hasattr(p, 'is_local'):
                p.stop()

    def cleanup_app(self):
        self.loop.run_until_complete(self.app.cleanup())

    def _start_patchers(self):
        self._patchers = collections.OrderedDict()
        self._mocks = {}
        self.init_patchers()

    def init_app(self, loop):
        raise NotImplementedError()


def async_test(what):
    """ replaces all coroutines in a 'what' class, or 'what' callable itself
    with sync method that uses run_until_complete to execute coroutine

    >>> async_test(SomeTestCase)
    <class 'SomeTestCase'>

    >>> class SomeTestCase(TestCase):
    >>>     @async_test
    >>>     async def testAny(self):
    >>>         await asyncio.sleep(1)
    >>>
    >>> asyncio.iscoroutinefunction(SomeTestCase.testAny)
    False

    """
    if inspect.isclass(what):
        for k in dir(what):
            func = getattr(what, k)
            if not k.startswith('test'):
                continue
            if not (callable(func) and asyncio.iscoroutinefunction(func)):
                continue

            def get_wrapper(func):
                @wraps(func)
                def wrapper(self, *args, **kwargs):
                    if func.__name__ != self._testMethodName:
                        raise RuntimeError("testee mismatch")
                    if hasattr(self, 'client'):
                        self.client.async = True

                    self.loop.run_until_complete(func(self, *args,**kwargs))
                return wrapper

            setattr(what, k, get_wrapper(func))
        return what

    else:
        @wraps(what)
        def wrapper(self):
            self.loop.run_until_complete(what(self))
    return wrapper


class override_settings(object):
    def __init__(self, settings, **kwargs):
        self.old_values = {}
        self.new_values = {}
        self.settings = settings
        for k, v in kwargs.items():
            if hasattr(settings, k):
                self.old_values[k] = getattr(settings, k)
            self.new_values[k] = v

    def __call__(self, decorated):
        if isinstance(decorated, type):
            return self.decorate_class(decorated)
        return self.decorate_callable(decorated)

    def decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith('test'):
                continue
            if callable(getattr(klass, attr)):
                new_func = self.decorate_callable(getattr(klass, attr))
                setattr(klass, attr, new_func)
        return klass

    def start(self):
        for k, v in self.new_values.items():
            setattr(self.settings, k, v)

    def stop(self):
        for k, v in self.new_values.items():
            if k in self.old_values:
                setattr(self.settings, k, self.old_values[k])
            else:
                delattr(self.settings, k)

    def decorate_callable(self, func):

        @wraps(func)
        def inner(*args, **kwargs):
            try:
                self.start()
                return func(*args, **kwargs)
            finally:
                self.stop()

        return inner

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
