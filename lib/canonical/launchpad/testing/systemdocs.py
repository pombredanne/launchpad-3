# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Infrastructure for setting up doctests."""

__metaclass__ = type
__all__ = [
    'LayeredDocFileSuite',
    'SpecialOutputChecker',
    'setUp',
    'setGlobs',
    'strip_prefix',
    'tearDown',
    ]

import logging
import os
import sys

import transaction
from zope.component import getUtility, getMultiAdapter
from zope.testing import doctest
from zope.testing.loggingsupport import Handler

from canonical.chunkydiff import elided_source
from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


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
    """A logging handler that prints log messages to sys.stdout.

    This causes log messages to become part of the output captured by
    doctest, making the test cover the logging behaviour of the code
    being run.
    """
    def emit(self, record):
        Handler.emit(self, record)
        print >> sys.stdout, '%s:%s:%s' % (
            record.levelname, record.name, self.format(record))


def LayeredDocFileSuite(*args, **kw):
    """Create a DocFileSuite, optionally applying a layer to it.

    In addition to the standard DocFileSuite arguments, the following
    optional keyword arguments are accepted:

    :param stdout_logging: If True, log messages are sent to the
      doctest's stdout (defaults to True).
    :param stdout_logging_level: The logging level for the above.
    :param layer: A Zope test runner layer to apply to the tests (by
      default no layer is applied).
    """
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

    layer = kw.pop('layer', None)
    suite = doctest.DocFileSuite(*args, **kw)
    if layer is not None:
        suite.layer = layer
    return suite


class SpecialOutputChecker(doctest.OutputChecker):
    """An OutputChecker that runs the 'chunkydiff' checker if appropriate."""
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


def create_view(context, name, form=None, layer=None, server_url=None,
                method='GET'):
    """Return a view based on the given arguments.

    :param context: The context for the view.
    :param name: The web page the view should handle.
    :param form: A dictionary with the form keys.
    :param layer: The layer where the page we are interested in is located.
    :param server_url: The URL from where this request was done.
    :param method: The method used in the request. Defaults to 'GET'.
    :return: The view class for the given context and the name.
    """
    request = LaunchpadTestRequest(
        form=form, SERVER_URL=server_url, method=method)
    if layer is not None:
        setFirstLayer(request, layer)
    return getMultiAdapter((context, request), name=name)


def setGlobs(test):
    """Add the common globals for testing system documentation."""
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility
    test.globs['transaction'] = transaction
    test.globs['flush_database_updates'] = flush_database_updates
    test.globs['create_view'] = create_view


def setUp(test):
    """Setup the common globals and login for testing system documentation."""
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)


def tearDown(test):
    """Tear down the common system documentation test."""
    logout()
