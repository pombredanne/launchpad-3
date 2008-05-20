# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Create a real, socket connecting browser.

Unlike `zope.testbrowser.testing.Browser`, this browser performs actual socket
connections to a real HTTP server.  This is used in tests which utilize the
AppServerLayer to run the app server in a child process.  The Zope testing
browser fakes its connections in-process, so that's not good enough.
"""

__metaclass__ = type
__all__ = [
    'Browser',
    'setUp',
    'tearDown',
    ]


import base64
import urllib2
import weakref

from zope.testbrowser.browser import Browser as _Browser


class SocketClosingOnErrorHandler(urllib2.BaseHandler):
    """A handler that ensures that the socket gets closed on errors.

    Interestingly enough <wink> without this, a 404 will cause mechanize to
    leak open socket objects.
    """
    # Ensure that this handler is the first default error handler to execute,
    # because right after this, the built-in default handler will raise an
    # exception.
    handler_order = 0

    # Copy signature from base class.
    def http_error_default(self, req, fp, code, msg, hdrs):
        """See `urllib2.BaseHandler`."""
        fp.close()


# To ensure that the mechanize browser doesn't leak socket connections past
# the end of the test, we manage a set of weak references to live browser
# objects.  The layer can then call a function here to ensure that all live
# browsers get properly closed.
_live_browser_set = set()


class Browser(_Browser):
    """A browser subsclass that knows about basic auth."""

    def __init__(self, auth=None):
        super(Browser, self).__init__()
        # We have to add the error handler to the mechanize browser underlying
        # the Zope browser, because it's the former that's actually doing all
        # the work.
        self.mech_browser.add_handler(SocketClosingOnErrorHandler())
        if auth:
            # Unlike the higher level Zope test browser, we actually have to
            # encode the basic auth information.
            userpass = base64.encodestring(auth)
            self.addHeader('Authorization', 'Basic ' + userpass)
        _live_browser_set.add(weakref.ref(self, self._refclose))

    def _refclose(self, obj):
        """For weak reference cleanup."""
        self.close()

    def close(self):
        """Yay!  Zope browsers don't have a close() method."""
        self.mech_browser.close()


def setUp(test):
    """Set up appserver tests."""
    test.globs['Browser'] = Browser


def tearDown(test):
    """Tear down appserver tests."""
    for ref in _live_browser_set:
        browser = ref()
        if browser is not None:
            browser.close()
