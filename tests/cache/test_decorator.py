#! coding: utf-8

from ._fixtures import _GenericBackendFixture
from . import eq_, requires_py3k, winsleep
from unittest import TestCase
import time
from dogpile.cache import util, compat
import itertools
from dogpile.cache.api import NO_VALUE

class DecoratorTest(_GenericBackendFixture, TestCase):
    backend = "dogpile.cache.memory"

    def _fixture(self, namespace=None, expiration_time=None):
        reg = self._region(config_args={"expiration_time":.25})

        counter = itertools.count(1)
        @reg.cache_on_arguments(namespace=namespace,
                            expiration_time=expiration_time)
        def go(a, b):
            val = next(counter)
            return val, a, b
        return go

    def _multi_fixture(self, namespace=None, expiration_time=None):
        reg = self._region(config_args={"expiration_time":.25})

        counter = itertools.count(1)
        @reg.cache_multi_on_arguments(namespace=namespace,
                            expiration_time=expiration_time)
        def go(*args):
            val = next(counter)
            return ["%d %s" % (val, arg) for arg in args]
        return go


    def test_decorator(self):
        go = self._fixture()
        eq_(go(1, 2), (1, 1, 2))
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (3, 1, 2))

    def test_decorator_namespace(self):
        # TODO: test the namespace actually
        # working somehow...
        go = self._fixture(namespace="x")
        eq_(go(1, 2), (1, 1, 2))
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (3, 1, 2))

    def test_decorator_custom_expire(self):
        go = self._fixture(expiration_time=.5)
        eq_(go(1, 2), (1, 1, 2))
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (3, 1, 2))

    def test_decorator_expire_callable(self):
        go = self._fixture(expiration_time=lambda: .5)
        eq_(go(1, 2), (1, 1, 2))
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (1, 1, 2))
        time.sleep(.3)
        eq_(go(1, 2), (3, 1, 2))

    def test_decorator_expire_callable_zero(self):
        go = self._fixture(expiration_time=lambda: 0)
        eq_(go(1, 2), (1, 1, 2))
        winsleep()
        eq_(go(1, 2), (2, 1, 2))
        winsleep()
        eq_(go(1, 2), (3, 1, 2))

    def test_explicit_expire(self):
        go = self._fixture(expiration_time=1)
        eq_(go(1, 2), (1, 1, 2))
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), (1, 1, 2))
        go.invalidate(1, 2)
        eq_(go(1, 2), (3, 1, 2))

    def test_explicit_set(self):
        go = self._fixture(expiration_time=1)
        eq_(go(1, 2), (1, 1, 2))
        go.set(5, 1, 2)
        eq_(go(3, 4), (2, 3, 4))
        eq_(go(1, 2), 5)
        go.invalidate(1, 2)
        eq_(go(1, 2), (3, 1, 2))
        go.set(0, 1, 3)
        eq_(go(1, 3), 0)

    def test_explicit_get(self):
        go = self._fixture(expiration_time=1)
        eq_(go(1, 2), (1, 1, 2))
        eq_(go.get(1, 2), (1, 1, 2))
        eq_(go.get(2, 1), NO_VALUE)
        eq_(go(2, 1), (2, 2, 1))
        eq_(go.get(2, 1), (2, 2, 1))

    def test_explicit_get_multi(self):
        go = self._multi_fixture(expiration_time=1)
        eq_(go(1, 2), ['1 1', '1 2'])
        eq_(go.get(1, 2), ['1 1', '1 2'])
        eq_(go.get(3, 1), [NO_VALUE, '1 1'])
        eq_(go(3, 1), ['2 3', '1 1'])
        eq_(go.get(3, 1), ['2 3', '1 1'])

    def test_explicit_set_multi(self):
        go = self._multi_fixture(expiration_time=1)
        eq_(go(1, 2), ['1 1', '1 2'])
        eq_(go(1, 2), ['1 1', '1 2'])
        go.set({1: '1 5', 2: '1 6'})
        eq_(go(1, 2), ['1 5', '1 6'])

    def test_explicit_refresh(self):
        go = self._fixture(expiration_time=1)
        eq_(go(1, 2), (1, 1, 2))
        eq_(go.refresh(1, 2), (2, 1, 2))
        eq_(go(1, 2), (2, 1, 2))
        eq_(go(1, 2), (2, 1, 2))
        eq_(go.refresh(1, 2), (3, 1, 2))
        eq_(go(1, 2), (3, 1, 2))

    def test_explicit_refresh_multi(self):
        go = self._multi_fixture(expiration_time=1)
        eq_(go(1, 2), ['1 1', '1 2'])
        eq_(go(1, 2), ['1 1', '1 2'])
        eq_(go.refresh(1, 2), ['2 1', '2 2'])
        eq_(go(1, 2), ['2 1', '2 2'])
        eq_(go(1, 2), ['2 1', '2 2'])

class KeyGenerationTest(TestCase):
    def _keygen_decorator(self, namespace=None, **kw):
        canary = []
        def decorate(fn):
            canary.append(util.function_key_generator(namespace, fn, **kw))
            return fn
        return decorate, canary

    def _multi_keygen_decorator(self, namespace=None, **kw):
        canary = []
        def decorate(fn):
            canary.append(util.function_multi_key_generator(namespace, fn, **kw))
            return fn
        return decorate, canary

    def test_keygen_fn(self):
        decorate, canary = self._keygen_decorator()

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        eq_(gen(1, 2), "tests.cache.test_decorator:one|1 2")
        eq_(gen(None, 5), "tests.cache.test_decorator:one|None 5")

    def test_multi_keygen_fn(self):
        decorate, canary = self._multi_keygen_decorator()

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        eq_(gen(1, 2), [
                "tests.cache.test_decorator:one|1",
                "tests.cache.test_decorator:one|2"
            ])

    def test_keygen_fn_namespace(self):
        decorate, canary = self._keygen_decorator("mynamespace")

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        eq_(gen(1, 2), "tests.cache.test_decorator:one|mynamespace|1 2")
        eq_(gen(None, 5), "tests.cache.test_decorator:one|mynamespace|None 5")

    def test_key_isnt_unicode_bydefault(self):
        decorate, canary = self._keygen_decorator("mynamespace")

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        assert isinstance(gen('foo'), str)

    def test_unicode_key(self):
        decorate, canary = self._keygen_decorator("mynamespace",
                                        to_str=compat.text_type)

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        eq_(gen(compat.u('méil'), compat.u('drôle')),
                compat.ue("tests.cache.test_decorator:"
                        "one|mynamespace|m\xe9il dr\xf4le"))

    def test_unicode_key_multi(self):
        decorate, canary = self._multi_keygen_decorator("mynamespace",
                                        to_str=compat.text_type)

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        eq_(gen(compat.u('méil'), compat.u('drôle')),
            [
                compat.ue('tests.cache.test_decorator:one|mynamespace|m\xe9il'),
                compat.ue('tests.cache.test_decorator:one|mynamespace|dr\xf4le')
            ])

    @requires_py3k
    def test_unicode_key_by_default(self):
        decorate, canary = self._keygen_decorator("mynamespace",
                                        to_str=compat.text_type)

        @decorate
        def one(a, b):
            pass
        gen = canary[0]

        assert isinstance(gen('méil'), str)

        eq_(gen('méil', 'drôle'),
                "tests.cache.test_decorator:"
                        "one|mynamespace|m\xe9il dr\xf4le")

class CacheDecoratorTest(_GenericBackendFixture, TestCase):
    backend = "mock"

    def test_cache_arg(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_on_arguments()
        def generate(x, y):
            return next(counter) + x + y

        eq_(generate(1, 2), 4)
        eq_(generate(2, 1), 5)
        eq_(generate(1, 2), 4)
        generate.invalidate(1, 2)
        eq_(generate(1, 2), 6)

    def test_reentrant_call(self):
        reg = self._region(backend="dogpile.cache.memory")

        counter = itertools.count(1)

        # if these two classes get the same namespace,
        # you get a reentrant deadlock.
        class Foo(object):
            @classmethod
            @reg.cache_on_arguments(namespace="foo")
            def generate(cls, x, y):
                return next(counter) + x + y

        class Bar(object):
            @classmethod
            @reg.cache_on_arguments(namespace="bar")
            def generate(cls, x, y):
                return Foo.generate(x, y)

        eq_(Bar.generate(1, 2), 4)

    def test_multi(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_multi_on_arguments()
        def generate(*args):
            return ["%d %d" % (arg, next(counter)) for arg in args]

        eq_(generate(2, 8, 10), ['2 2', '8 3', '10 1'])
        eq_(generate(2, 9, 10), ['2 2', '9 4', '10 1'])

        generate.invalidate(2)
        eq_(generate(2, 7, 10), ['2 5', '7 6', '10 1'])

        generate.set({7: 18, 10: 15})
        eq_(generate(2, 7, 10), ['2 5', 18, 15])

    def test_multi_asdict(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_multi_on_arguments(asdict=True)
        def generate(*args):
            return dict(
                    [(arg, "%d %d" % (arg, next(counter))) for arg in args]
                    )

        eq_(generate(2, 8, 10), {2: '2 2', 8: '8 3', 10: '10 1'})
        eq_(generate(2, 9, 10), {2: '2 2', 9: '9 4', 10: '10 1'})

        generate.invalidate(2)
        eq_(generate(2, 7, 10), {2: '2 5', 7: '7 6', 10: '10 1'})

        generate.set({7: 18, 10: 15})
        eq_(generate(2, 7, 10), {2: '2 5', 7: 18, 10: 15})

        eq_(
            generate.refresh(2, 7),
            {2: '2 7', 7: '7 8'}
        )
        eq_(generate(2, 7, 10), {2: '2 7', 10: 15, 7: '7 8'})


    def test_multi_asdict_keys_missing(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_multi_on_arguments(asdict=True)
        def generate(*args):
            return dict(
                    [(arg, "%d %d" % (arg, next(counter)))
                        for arg in args if arg != 10]
                    )

        eq_(generate(2, 8, 10), {2: '2 1', 8: '8 2'})
        eq_(generate(2, 9, 10), {2: '2 1', 9: '9 3'})

        assert reg.get(10) is NO_VALUE

        generate.invalidate(2)
        eq_(generate(2, 7, 10), {2: '2 4', 7: '7 5'})

        generate.set({7: 18, 10: 15})
        eq_(generate(2, 7, 10), {2: '2 4', 7: 18, 10: 15})

    def test_multi_asdict_keys_missing_existing_cache_fn(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_multi_on_arguments(asdict=True,
                            should_cache_fn=lambda v: not v.startswith('8 '))
        def generate(*args):
            return dict(
                    [(arg, "%d %d" % (arg, next(counter)))
                        for arg in args if arg != 10]
                    )

        eq_(generate(2, 8, 10), {2: '2 1', 8: '8 2'})
        eq_(generate(2, 8, 10), {2: '2 1', 8: '8 3'})
        eq_(generate(2, 8, 10), {2: '2 1', 8: '8 4'})
        eq_(generate(2, 9, 10), {2: '2 1', 9: '9 5'})

        assert reg.get(10) is NO_VALUE

        generate.invalidate(2)
        eq_(generate(2, 7, 10), {2: '2 6', 7: '7 7'})

        generate.set({7: 18, 10: 15})
        eq_(generate(2, 7, 10), {2: '2 6', 7: 18, 10: 15})

    def test_multi_namespace(self):
        reg = self._region()

        counter = itertools.count(1)

        @reg.cache_multi_on_arguments(namespace="foo")
        def generate(*args):
            return ["%d %d" % (arg, next(counter)) for arg in args]

        eq_(generate(2, 8, 10), ['2 2', '8 3', '10 1'])
        eq_(generate(2, 9, 10), ['2 2', '9 4', '10 1'])

        eq_(
            sorted(list(reg.backend._cache)),
            [
            'tests.cache.test_decorator:generate|foo|10',
            'tests.cache.test_decorator:generate|foo|2',
            'tests.cache.test_decorator:generate|foo|8',
            'tests.cache.test_decorator:generate|foo|9']
        )
        generate.invalidate(2)
        eq_(generate(2, 7, 10), ['2 5', '7 6', '10 1'])

        generate.set({7: 18, 10: 15})
        eq_(generate(2, 7, 10), ['2 5', 18, 15])
