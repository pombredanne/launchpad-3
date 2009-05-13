# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Infrastructure for setting up doctests."""

__metaclass__ = type
__all__ = [
    'default_optionflags',
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

# pprint25 is a copy of pprint.py from Python 2.5, which is almost
# identical to that in 2.4 except that it resolves an ordering issue
# which makes the 2.4 version unsuitable for use in a doctest.
import pprint25

import transaction
from zope.component import getUtility, getMultiAdapter
from zope.security.management import endInteraction, newInteraction
from zope.testing import doctest
from zope.testing.loggingsupport import Handler

from canonical.chunkydiff import elided_source
from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import reset_logging
from lp.testing import ANONYMOUS, login, login_person, logout
from lp.testing.factory import LaunchpadObjectFactory


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
    def get_doctest(self, string, globs, name, filename, lineno,
                    optionflags=0):
        filename = strip_prefix(filename)
        return doctest.DocTestParser.get_doctest(
            self, string, globs, name, filename, lineno,
            optionflags=optionflags)


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
            reset_logging()
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
        if config.canonical.chunkydiff is False:
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
                method='GET', principal=None, query_string='', cookie='',
                path_info='/', current_request=False, **kwargs):
    """Return a view based on the given arguments.

    :param context: The context for the view.
    :param name: The web page the view should handle.
    :param form: A dictionary with the form keys.
    :param layer: The layer where the page we are interested in is located.
    :param server_url: The URL from where this request was done.
    :param method: The method used in the request. Defaults to 'GET'.
    :param principal: The principal for the request, default to the
        unauthenticated principal.
    :param query_string: The query string for the request.
    :patam cookie: The HTTP_COOKIE value for the request.
    :param path_info: The PATH_INFO value for the request.
    :param current_request: If True, the request will be set as the current
        interaction.
    :param **kwargs: Any other parameter for the request.
    :return: The view class for the given context and the name.
    """
    request = LaunchpadTestRequest(
        form=form, SERVER_URL=server_url, QUERY_STRING=query_string,
        HTTP_COOKIE=cookie, method=method, **kwargs)
    if principal is not None:
        request.setPrincipal(principal)
    else:
        request.setPrincipal(
            getUtility(IPlacelessAuthUtility).unauthenticatedPrincipal())
    if layer is not None:
        setFirstLayer(request, layer)
    if current_request:
        endInteraction()
        newInteraction(request)
    return getMultiAdapter((context, request), name=name)


def create_initialized_view(context, name, form=None, layer=None,
                            server_url=None, method=None, principal=None,
                            query_string=None, cookie=None):
    """Return a view that has already been initialized."""
    if method is None:
        if form is None:
            method = 'GET'
        else:
            method = 'POST'
    view = create_view(
        context, name, form, layer, server_url, method, principal,
        query_string, cookie)
    view.initialize()
    return view


def ordered_dict_as_string(dict):
    """Return the contents of a dict as an ordered string.

    The output will be ordered by key, so {'z': 1, 'a': 2, 'c': 3} will
    be printed as {'a': 2, 'c': 3, 'z': 1}.

    We do this because dict ordering is not guaranteed.
    """
    # XXX 2008-06-25 gmb:
    #     Once we move to Python 2.5 we won't need this, since dict
    #     ordering is guaranteed when __str__() is called.
    item_string = '%r: %r'
    item_strings = []
    for key, value in sorted(dict.items()):
        item_strings.append(item_string % (key, value))

    return '{%s}' % ', '.join(
        "%r: %r" % (key, value) for key, value in sorted(dict.items()))


def setGlobs(test):
    """Add the common globals for testing system documentation."""
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['login_person'] = login_person
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility
    test.globs['transaction'] = transaction
    test.globs['flush_database_updates'] = flush_database_updates
    test.globs['create_view'] = create_view
    test.globs['create_initialized_view'] = create_initialized_view
    test.globs['factory'] = LaunchpadObjectFactory()
    test.globs['ordered_dict_as_string'] = ordered_dict_as_string
    test.globs['verifyObject'] = verifyObject
    test.globs['pretty'] = pprint25.PrettyPrinter(width=1).pformat


def setUp(test):
    """Setup the common globals and login for testing system documentation."""
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)


def tearDown(test):
    """Tear down the common system documentation test."""
    logout()
