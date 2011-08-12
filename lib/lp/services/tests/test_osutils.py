# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.osutils."""

__metaclass__ = type

import errno
import os
import socket
import tempfile

from lp.services.osutils import (
    ensure_directory_exists,
    open_for_writing,
    remove_tree,
    until_no_eintr,
    )
from lp.testing import TestCase


class TestRemoveTree(TestCase):
    """Tests for remove_tree."""

    def test_removes_directory(self):
        # remove_tree deletes the directory.
        directory = tempfile.mkdtemp()
        remove_tree(directory)
        self.assertFalse(os.path.isdir(directory))
        self.assertFalse(os.path.exists(directory))

    def test_on_nonexistent_path_passes_silently(self):
        # remove_tree simply does nothing when called on a non-existent path.
        directory = tempfile.mkdtemp()
        nonexistent_tree = os.path.join(directory, 'foo')
        remove_tree(nonexistent_tree)
        self.assertFalse(os.path.isdir(nonexistent_tree))
        self.assertFalse(os.path.exists(nonexistent_tree))

    def test_raises_on_file(self):
        # If remove_tree is pased a file, it raises an OSError.
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, 'foo')
        fd = open(filename, 'w')
        fd.write('data')
        fd.close()
        self.assertRaises(OSError, remove_tree, filename)


class TestEnsureDirectoryExists(TestCase):
    """Tests for 'ensure_directory_exists'."""

    def test_directory_exists(self):
        directory = self.makeTemporaryDirectory()
        self.assertFalse(ensure_directory_exists(directory))

    def test_directory_doesnt_exist(self):
        directory = os.path.join(self.makeTemporaryDirectory(), 'foo/bar/baz')
        self.assertTrue(ensure_directory_exists(directory))
        self.assertTrue(os.path.isdir(directory))


class TestOpenForWriting(TestCase):
    """Tests for 'open_for_writing'."""

    def test_opens_for_writing(self):
        # open_for_writing opens a file for, umm, writing.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, 'foo')
        fp = open_for_writing(filename, 'w')
        fp.write("Hello world!\n")
        fp.close()
        self.assertEqual("Hello world!\n", open(filename).read())

    def test_opens_for_writing_append(self):
        # open_for_writing can also open to append.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, 'foo')
        fp = open_for_writing(filename, 'w')
        fp.write("Hello world!\n")
        fp.close()
        fp = open_for_writing(filename, 'a')
        fp.write("Next line\n")
        fp.close()
        self.assertEqual("Hello world!\nNext line\n", open(filename).read())

    def test_even_if_directory_doesnt_exist(self):
        # open_for_writing will open a file for writing even if the directory
        # doesn't exist.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, 'foo', 'bar', 'baz', 'filename')
        fp = open_for_writing(filename, 'w')
        fp.write("Hello world!\n")
        fp.close()
        self.assertEqual("Hello world!\n", open(filename).read())


class TestUntilNoEINTR(TestCase):
    """Tests for until_no_eintr."""

    # The maximum number of retries used in our tests.
    MAX_RETRIES = 10

    # A number of retries less than the maximum number used in tests.
    SOME_RETRIES = MAX_RETRIES / 2

    def test_no_calls(self):
        # If the user has, bizarrely, asked for 0 attempts, then never try to
        # call the function.
        calls = []
        until_no_eintr(0, calls.append, None)
        self.assertEqual([], calls)

    def test_function_doesnt_raise(self):
        # If the function doesn't raise, call it only once.
        calls = []
        until_no_eintr(self.MAX_RETRIES, calls.append, None)
        self.assertEqual(1, len(calls))

    def test_returns_function_return(self):
        # If the function doesn't raise, return its value.
        ret = until_no_eintr(1, lambda: 42)
        self.assertEqual(42, ret)

    def test_raises_exception(self):
        # If the function raises an exception that's not EINTR, then re-raise
        # it.
        self.assertRaises(ZeroDivisionError, until_no_eintr, 1, lambda: 1/0)

    def test_retries_on_ioerror_eintr(self):
        # Retry the function as long as it keeps raising IOError(EINTR).
        calls = []
        def function():
            calls.append(None)
            if len(calls) < self.SOME_RETRIES:
                raise IOError(errno.EINTR, os.strerror(errno.EINTR))
            return 'orange'
        ret = until_no_eintr(self.MAX_RETRIES, function)
        self.assertEqual(self.SOME_RETRIES, len(calls))
        self.assertEqual('orange', ret)

    def test_retries_on_oserror_eintr(self):
        # Retry the function as long as it keeps raising OSError(EINTR).
        calls = []
        def function():
            calls.append(None)
            if len(calls) < self.SOME_RETRIES:
                raise OSError(errno.EINTR, os.strerror(errno.EINTR))
            return 'orange'
        ret = until_no_eintr(self.MAX_RETRIES, function)
        self.assertEqual(self.SOME_RETRIES, len(calls))
        self.assertEqual('orange', ret)

    def test_retries_on_socket_error_eintr(self):
        # Retry the function as long as it keeps raising socket.error(EINTR).
        # This test is redundant on Python 2.6, since socket.error is an
        # IOError there.
        calls = []
        def function():
            calls.append(None)
            if len(calls) < self.SOME_RETRIES:
                raise socket.error(errno.EINTR, os.strerror(errno.EINTR))
            return 'orange'
        ret = until_no_eintr(self.MAX_RETRIES, function)
        self.assertEqual(self.SOME_RETRIES, len(calls))
        self.assertEqual('orange', ret)

    def test_raises_other_error_without_retry(self):
        # Any other kind of IOError (or OSError or socket.error) is re-raised
        # with a retry attempt.
        calls = []
        def function():
            calls.append(None)
            if len(calls) < self.SOME_RETRIES:
                raise IOError(errno.ENOENT, os.strerror(errno.ENOENT))
            return 'orange'
        error = self.assertRaises(
            IOError, until_no_eintr, self.MAX_RETRIES, function)
        self.assertEqual(errno.ENOENT, error.errno)
        self.assertEqual(1, len(calls))

    def test_never_exceeds_retries(self):
        # If the function keeps on raising EINTR, then stop running it after
        # the given number of retries, and just re-raise the error.
        calls = []
        def function():
            calls.append(None)
            raise IOError(errno.EINTR, os.strerror(errno.EINTR))
        error = self.assertRaises(
            IOError, until_no_eintr, self.MAX_RETRIES, function)
        self.assertEqual(errno.EINTR, error.errno)
        self.assertEqual(self.MAX_RETRIES, len(calls))
