# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Alter the standard functional testing environment for Launchpad."""

import zope.app.testing.functional
from zope.app.testing.functional import (
    FunctionalTestSetup, HTTPCaller, ZopePublication, SimpleCookie)

import unittest
import logging
import doctest
import sys
from zope.testing.loggingsupport import Handler
from zope.testbrowser.testing import Browser

from canonical.config import config
from canonical.chunkydiff import elided_source
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.testing import reset_logging, layers

class NewFunctionalTestSetup(FunctionalTestSetup):
    """Wrap standard FunctionalTestSetup to ensure it is only called
       from tests specifying a valid Layer.
    """
    def __init__(self, *args, **kw):
        from canonical.testing.layers import Functional, Zopeless
        assert Functional.isSetUp or Zopeless.isSetUp, \
                'FunctionalTestSetup invoked at an inappropriate time'
        super(NewFunctionalTestSetup, self).__init__(*args, **kw)
FunctionalTestSetup = NewFunctionalTestSetup

class FunctionalTestCase(unittest.TestCase):
    """Functional test case.
    
    This functionality should be moved into canonical.testing.layers.
    """
    layer = layers.Functional
    def setUp(self):
        """Prepares for a functional test case."""
        super(FunctionalTestCase, self).setUp()

    def tearDown(self):
        """Cleans up after a functional test case."""
        super(FunctionalTestCase, self).tearDown()

    def getRootFolder(self):
        """Returns the Zope root folder."""
        raise NotImplementedError('getRootFolder')
        #return FunctionalTestSetup().getRootFolder()

    def commit(self):
        commit()

    def abort(self):
        abort()


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


class StdoutHandler(Handler):
    def emit(self, record):
        Handler.emit(self, record)
        print >> StdoutWrapper(), '%s:%s:%s' % (
                    record.levelname, record.name, self.format(record)
                    )


class MockRootFolder:
    """Implement the minimum functionality required by Z3 ZODB dependancies

    Installed as part of the FunctionalDocFileSuite to allow the http()
    method (zope.app.testing.functional.HTTPCaller) to work.
    """
    @property
    def _p_jar(self):
        return self
    def sync(self):
        pass


class UnstickyCookieHTTPCaller(HTTPCaller):
    """HTTPCaller propogates cookies between subsequent requests.
    This is a nice feature, except it triggers a bug in Launchpad where
    sending both Basic Auth and cookie credentials raises an exception
    (Bug 39881).
    """
    def __init__(self, *args, **kw):
        if kw.get('debug'):
            self._debug = True
            del kw['debug']
        else:
            self._debug = False
        HTTPCaller.__init__(self, *args, **kw)
    def __call__(self, *args, **kw):
        if self._debug:
            import pdb; pdb.set_trace()
        try:
            return HTTPCaller.__call__(self, *args, **kw)
        finally:
            self.resetCookies()

    def resetCookies(self):
        self.cookies = SimpleCookie()


def FunctionalDocFileSuite(*paths, **kw):
    kwsetUp = kw.get('setUp')

    # Set stdout_logging keyword argument to True to make
    # logging output be sent to stdout, forcing doctests to deal with it.
    if kw.has_key('stdout_logging'):
        stdout_logging = kw.get('stdout_logging')
        del kw['stdout_logging']
    else:
        stdout_logging = True

    if kw.has_key('stdout_logging_level'):
        stdout_logging_level = kw.get('stdout_logging_level')
        del kw['stdout_logging_level']
    else:
        stdout_logging_level = logging.INFO

    if kw.has_key('layer'):
        layer = kw.pop('layer')
    else:
        layer = layers.Functional

    def setUp(test):
        if kwsetUp is not None:
            kwsetUp(test)
        # Fake a root folder to keep Z3 ZODB dependancies happy
        fs = FunctionalTestSetup()
        if not fs.connection:
            fs.connection = fs.db.open()
        root = fs.connection.root()
        root[ZopePublication.root_name] = MockRootFolder()
        # Out tests report being on a different port
        test.globs['http'] = UnstickyCookieHTTPCaller(port=9000)
        test.globs['debug_http'] = UnstickyCookieHTTPCaller(
                port=9000,debug=True
                )
        # Set up our Browser objects with handleErrors set to False, since
        # that gives a tracebacks instead of unhelpful error messages.
        def setupBrowser(auth=None):
            browser = Browser()
            browser.handleErrors = False
            if auth is not None:
                browser.addHeader("Authorization", auth)
            return browser

        test.globs['browser'] = setupBrowser()
        test.globs['anon_browser'] = setupBrowser()
        test.globs['user_browser'] = setupBrowser(
            auth="Basic test@canonical.com:test")
        test.globs['admin_browser'] = setupBrowser(
            auth="Basic foo.bar@canonical.com:test")
        
        if stdout_logging:
            log = StdoutHandler('')
            log.setLoggerLevel(stdout_logging_level)
            log.install()
            test.globs['log'] = log
            # Store here as well in case test overwrites 'log' global
            test.globs['_functional_log'] = log
    kw['setUp'] = setUp

    kwtearDown = kw.get('tearDown')
    def tearDown(test):
        if kwtearDown is not None:
            kwtearDown(test)
        if stdout_logging:
            test.globs['_functional_log'].uninstall()
    kw['tearDown'] = tearDown

    suite = zope.app.testing.functional.FunctionalDocFileSuite(*paths, **kw)
    suite.layer = layer
    return suite


def PageTestDocFileSuite(*paths, **kw):
    if not kw.get('stdout_logging'):
        kw['stdout_logging'] = False
    suite = FunctionalDocFileSuite(*paths, **kw)
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
                # There was no difference.  May be an error in elided_source().
                # In any case, return the whole thing.
                newgot = got
        else:
            newgot = got
        return doctest.OutputChecker.output_difference(
            self, example, newgot, optionflags)


if __name__ == '__main__':
    unittest.main()
