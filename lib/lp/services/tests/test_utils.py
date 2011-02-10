# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

from contextlib import contextmanager
import itertools
import unittest

from lp.services.utils import (
    CachingIterator,
    decorate_with,
    docstring_dedent,
    iter_split,
    traceback_info,
    )
from lp.testing import TestCase


class TestIterateSplit(TestCase):
    """Tests for iter_split."""

    def test_iter_split(self):
        # iter_split loops over each way of splitting a string in two using
        # the given splitter.
        self.assertEqual([('one', '')], list(iter_split('one', '/')))
        self.assertEqual([], list(iter_split('', '/')))
        self.assertEqual(
            [('one/two', ''), ('one', 'two')],
            list(iter_split('one/two', '/')))
        self.assertEqual(
            [('one/two/three', ''), ('one/two', 'three'),
             ('one', 'two/three')],
            list(iter_split('one/two/three', '/')))


class TestCachingIterator(TestCase):
    """Tests for CachingIterator."""

    def test_reuse(self):
        # The same iterator can be used multiple times.
        iterator = CachingIterator(itertools.count())
        self.assertEqual(
            [0, 1, 2, 3, 4], list(itertools.islice(iterator, 0, 5)))
        self.assertEqual(
            [0, 1, 2, 3, 4], list(itertools.islice(iterator, 0, 5)))

    def test_more_values(self):
        # If a subsequent call to iter causes more values to be fetched, they
        # are also cached.
        iterator = CachingIterator(itertools.count())
        self.assertEqual(
            [0, 1, 2], list(itertools.islice(iterator, 0, 3)))
        self.assertEqual(
            [0, 1, 2, 3, 4], list(itertools.islice(iterator, 0, 5)))

    def test_limited_iterator(self):
        # Make sure that StopIteration is handled correctly.
        iterator = CachingIterator(iter([0, 1, 2, 3, 4]))
        self.assertEqual(
            [0, 1, 2], list(itertools.islice(iterator, 0, 3)))
        self.assertEqual([0, 1, 2, 3, 4], list(iterator))

    def test_parallel_iteration(self):
        # There can be parallel iterators over the CachingIterator.
        ci = CachingIterator(iter([0, 1, 2, 3, 4]))
        i1 = iter(ci)
        i2 = iter(ci)
        self.assertEqual(0, i1.next())
        self.assertEqual(0, i2.next())
        self.assertEqual([1, 2, 3, 4], list(i2))
        self.assertEqual([1, 2, 3, 4], list(i1))


class TestDecorateWith(TestCase):
    """Tests for `decorate_with`."""

    @contextmanager
    def trivialContextManager(self):
        """A trivial context manager, used for testing."""
        yield

    def test_decorate_with_calls_context(self):
        # When run, a function decorated with decorated_with runs with the
        # context given to decorated_with.
        calls = []
        @contextmanager
        def appending_twice():
            calls.append('before')
            yield
            calls.append('after')
        @decorate_with(appending_twice)
        def function():
            pass
        function()
        self.assertEquals(['before', 'after'], calls)

    def test_decorate_with_function(self):
        # The original function is actually called when we call the result of
        # decoration.
        calls = []
        @decorate_with(self.trivialContextManager)
        def function():
            calls.append('foo')
        function()
        self.assertEquals(['foo'], calls)

    def test_decorate_with_call_twice(self):
        # A function decorated with decorate_with can be called twice.
        calls = []
        @decorate_with(self.trivialContextManager)
        def function():
            calls.append('foo')
        function()
        function()
        self.assertEquals(['foo', 'foo'], calls)

    def test_decorate_with_arguments(self):
        # decorate_with passes through arguments.
        calls = []
        @decorate_with(self.trivialContextManager)
        def function(*args, **kwargs):
            calls.append((args, kwargs))
        function('foo', 'bar', qux=4)
        self.assertEquals([(('foo', 'bar'), {'qux': 4})], calls)

    def test_decorate_with_name_and_docstring(self):
        # decorate_with preserves function names and docstrings.
        @decorate_with(self.trivialContextManager)
        def arbitrary_name():
            """Arbitrary docstring."""
        self.assertEqual('arbitrary_name', arbitrary_name.__name__)
        self.assertEqual('Arbitrary docstring.', arbitrary_name.__doc__)

    def test_decorate_with_returns(self):
        # decorate_with returns the original function's return value.
        decorator = decorate_with(self.trivialContextManager)
        arbitrary_value = self.getUniqueString()
        result = decorator(lambda: arbitrary_value)()
        self.assertEqual(arbitrary_value, result)


class TestDocstringDedent(TestCase):
    """Tests for `docstring_dedent`."""

    def test_single_line(self):
        self.assertEqual(docstring_dedent('docstring'), 'docstring')

    def test_multi_line(self):
        docstring = """This is a multiline docstring.

        This is the second line.
        """
        result = 'This is a multiline docstring.\n\nThis is the second line.'
        self.assertEqual(docstring_dedent(docstring), result)


class TestTracebackInfo(TestCase):
    """Tests of `traceback_info`."""

    def test(self):
        # `traceback_info` sets the local variable __traceback_info__ in the
        # caller's frame.
        self.assertEqual(None, locals().get("__traceback_info__"))
        traceback_info("Pugwash")
        self.assertEqual("Pugwash", locals().get("__traceback_info__"))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
