# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Alter the standard functional testing environment for Launchpad."""

__metaclass__ = type

# Import everything so we can override
import zope.app.testing.functional
from zope.app.testing.functional import *

from canonical.launchpad.webapp import LaunchpadBrowserRequest

import os.path

from zope.app.component.hooks import setSite, getSite
from zope.component import getUtility
import zope.security.management
from zope.publisher.interfaces.http import IHeaderOutput

from canonical.publication import LaunchpadBrowserPublication
from canonical.chunkydiff import elided_source
from canonical.config import config
import canonical.launchpad.layers


ftesting_path = os.path.abspath(os.path.join(config.root, 'ftesting.zcml'))

Functional = ZCMLLayer(ftesting_path, __name__, 'Functional')

class FunctionalTestSetup(zope.app.testing.functional.FunctionalTestSetup):
    def __init__(self, config_file=None):
        """As per zope.app.testing.functional.FunctionalTestSetup.

        Overridden to ensure a consistant ftesting.zcml is used.
        """
        if config_file is None:
            config_file = ftesting_path
        super(FunctionalTestSetup, self).__init__(config_file)


class FunctionalTestCase(unittest.TestCase):
    """Functional test case."""
    layer = Functional
    def setUp(self):
        """Prepares for a functional test case."""
        super(FunctionalTestCase, self).setUp()
        FunctionalTestSetup().setUp()

    def tearDown(self):
        """Cleans up after a functional test case."""
        FunctionalTestSetup().tearDown()
        super(FunctionalTestCase, self).tearDown()

    def getRootFolder(self):
        """Returns the Zope root folder."""
        return FunctionalTestSetup().getRootFolder()

    def commit(self):
        commit()

    def abort(self):
        abort()


def http(request_string, port=9000, handle_errors=True, debug=False):
    """Execute an HTTP request string via the publisher

    This is used for HTTP doc tests.

    XXX: This method should be removed, and the override in
    FunctionalDocFileSuite removed, once we have removed the ZODB
    dependancy from zope.app.testing.functional.HTTPCaller
    -- StuartBishop 20060228
    """
    # Commit work done by previous python code.
    commit()

    # Discard leading white space to make call layout simpler
    request_string = request_string.lstrip()

    # split off and parse the command line
    l = request_string.find('\n')
    command_line = request_string[:l].rstrip()
    request_string = request_string[l+1:]
    method, path, protocol = command_line.split()
    path = urllib.unquote(path)

    instream = StringIO(request_string)
    environment = {"HTTP_HOST": 'localhost:%s' % port,
                   "HTTP_REFERER": 'localhost',
                   "REQUEST_METHOD": method,
                   "SERVER_PROTOCOL": protocol,
                   }

    headers = [split_header(header)
               for header in rfc822.Message(instream).headers]
    for name, value in headers:
        name = ('_'.join(name.upper().split('-')))
        if name not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            name = 'HTTP_' + name
        environment[name] = value.rstrip()

    old_site = getSite()
    setSite(None)
    app = FunctionalTestSetup().getApplication()

    if method not in ('GET', 'POST', 'HEAD'):
        raise RuntimeError("Request method was not GET, POST or HEAD.")

    request_cls = LaunchpadBrowserRequest
    publication_cls = LaunchpadBrowserPublication

    request = app._request(path, instream, environment=environment,
                           request=request_cls, publication=publication_cls)
    canonical.launchpad.layers.setFirstLayer(
        request, canonical.launchpad.layers.PageTestLayer)
    response = ResponseWrapper(
            request.response, path,
            omit=['x-content-type-warning','x-powered-by']
            )

    if debug:
        import pdb;pdb.set_trace()
    publish(request, handle_errors=handle_errors)
    setSite(old_site)

    return response


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
                # There was no difference.  May be an error in elided_source().
                # In any case, return the whole thing.
                newgot = got
        else:
            newgot = got
        return doctest.OutputChecker.output_difference(
            self, example, newgot, optionflags)


class StdoutWrapper:
    """A wrapper for sys.stdout.  Writes to this file like object will
    write to whatever sys.stdout is pointing to at the time.

    The purpose of this class is to allow doctest to capture log
    messages.  Since doctest replaces sys.stdout, configuring the
    logging module to send messages to sys.stdout before running the
    tests will not result in the output being captured.  Using an
    instance of this class solves the problem.
    """
    def __getattr__(self, attr):
        return getattr(sys.stdout, attr)


def FunctionalDocFileSuite(*paths, **kw):
    if not kw.has_key('checker'):
        kw['checker'] = SpecialOutputChecker()
    kwsetUp = kw.get('setUp')
    def setUp(test):
        # for doctests, direct log messages to stdout, so that they
        # must be processed along with other command output.
        logging.root.handlers[0].close()
        logging.root.removeHandler(logging.root.handlers[0])
        logging.basicConfig(stream=StdoutWrapper(), level=logging.WARNING)
        if kwsetUp is not None:
            kwsetUp(test)
        # XXX: Override the standard method, which has hard coded ZODB
        # dependancies. -- StuartBishop 20060228
        test.globs['http'] = http
    kw['setUp'] = setUp
    return zope.app.testing.functional.FunctionalDocFileSuite(*paths, **kw)


if __name__ == '__main__':
    unittest.main()
