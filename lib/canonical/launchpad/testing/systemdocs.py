# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'LayeredDocFileSuite',
    'SpecialOutputChecker',
    'strip_prefix',
    ]

import logging
import os
import sys

from zope.testing import doctest
from zope.testing.loggingsupport import Handler

from canonical.chunkydiff import elided_source
from canonical.config import config


default_optionflags = (doctest.REPORT_NDIFF |
                       doctest.NORMALIZE_WHITESPACE |
                       doctest.ELLIPSIS)


def strip_prefix(path):
    """Return path with the Launchpad tree root removed."""
    prefix = config.root
    if not prefix.endswith(os.path.sep):
        prefix += os.path.sep

    if path.startswith(prefix):
        return path[len(prefix):]
    else:
        return path


class FilePrefixStrippingDocTestParser(doctest.DocTestParser):
    """A DocTestParser that strips a prefix from doctests."""
    def get_doctest(self, string, globs, name, filename, lineno):
        filename = strip_prefix(filename)
        return doctest.DocTestParser.get_doctest(
            self, string, globs, name, filename, lineno)


default_parser = FilePrefixStrippingDocTestParser()


class StdoutHandler(Handler):
    def emit(self, record):
        Handler.emit(self, record)
        print >> sys.stdout, '%s:%s:%s' % (
            record.levelname, record.name, self.format(record))


def LayeredDocFileSuite(*args, **kw):
    """Create a DocFileSuite with a layer."""
    kw.setdefault('optionflags', default_optionflags)
    kw.setdefault('parser', default_parser)

    # Make sure that paths are resolved relative to our caller
    kw['package'] = doctest._normalize_module(kw.get('package'))

    # Set stdout_logging keyword argument to True to make
    # logging output be sent to stdout, forcing doctests to deal with it.
    stdout_logging = kw.pop('stdout_logging', True)
    stdout_logging_level = kw.pop('stdout_logging_level', logging.INFO)

    if stdout_logging:
        kw_setUp = kw.get('setUp')
        def setUp(test):
            if kw_setUp is not None:
                kw_setUp(test)
            log = StdoutHandler('')
            log.setLoggerLevel(stdout_logging_level)
            log.install()
            test.globs['log'] = log
            # Store as instance attribute so we can uninstall it.
            test._stdout_logger = log
        kw['setUp'] = setUp

        kw_tearDown = kw.get('tearDown')
        def tearDown(test):
            if kw_tearDown is not None:
                kw_tearDown(test)
            test._stdout_logger.uninstall()
        kw['tearDown'] = tearDown

    layer = kw.pop('layer')
    suite = doctest.DocFileSuite(*args, **kw)
    if layer is not None:
        suite.layer = layer
    return suite


class SpecialOutputChecker(doctest.OutputChecker):
    def output_difference(self, example, got, optionflags):
        if config.chunkydiff is False:
            return doctest.OutputChecker.output_difference(
                self, example, got, optionflags)

        if optionflags & doctest.ELLIPSIS:
            normalize_whitespace = optionflags & doctest.NORMALIZE_WHITESPACE
            newgot = elided_source(example.want, got,
                                   normalize_whitespace=normalize_whitespace)
            if newgot == example.want:
                # There was no difference.  May be an error in
                # elided_source().  In any case, return the whole thing.
                newgot = got
        else:
            newgot = got
        return doctest.OutputChecker.output_difference(
            self, example, newgot, optionflags)
