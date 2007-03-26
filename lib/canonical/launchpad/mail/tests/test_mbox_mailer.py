# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the mbox_mailer.txt tests."""

import os
import doctest
import tempfile

from zope.testing.cleanup import cleanUp


def setup(testobj):
    """Set up for doc test"""
    fd, mbox_filename = tempfile.mkstemp()
    os.close(fd)
    testobj.globs['mbox_filename'] = mbox_filename
    fd, chained_filename = tempfile.mkstemp()
    os.close(fd)
    testobj.globs['chained_filename'] = chained_filename


def teardown(testobj):
    os.remove(testobj.globs['mbox_filename'])
    os.remove(testobj.globs['chained_filename'])
    cleanUp()


def test_suite():
    return doctest.DocFileSuite(
        'mbox_mailer.txt',
        setUp=setup, tearDown=teardown,
        optionflags=doctest.ELLIPSIS)
