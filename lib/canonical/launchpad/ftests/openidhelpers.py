# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helpers for OpenID page tests."""

__metaclass__ = type
__all__ = [
    'PublisherFetcher',
    'install_consumerview',
    'uninstall_consumerview',
]

from StringIO import StringIO
import urllib2

from openid import fetchers

from zope.app.testing.ztapi import browserView
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.checker import defineChecker, Checker, CheckerPublic
from zope.testbrowser.testing import PublisherHTTPHandler

from canonical.launchpad.webapp.publisher import LaunchpadView


class ConsumerView(LaunchpadView):
    """Register a view that renders the parameters in the response
    in an easily testable format.
    """
    implements(IBrowserPublisher)
    def render(self):
        out = StringIO()
        print >> out, 'Consumer received %s' % self.request.method
        keys = sorted(self.request.form.keys())
        for key in keys:
            print >> out, '%s:%s' % (key, self.request.form[key])
        return out.getvalue()
    def browserDefault(self, request):
        return self, ()


defineChecker(ConsumerView, Checker({
    '__call__': CheckerPublic,
    'browserDefault': CheckerPublic,
    'render': CheckerPublic,
    }))


def install_consumer():
    browserView(None, '+openid-consumer', ConsumerView)

def uninstall_consumer():
    # Don't bother - work out how to do this if it is a problem, but I
    # think YAGNI.
    pass


class PublisherFetcher(fetchers.Urllib2Fetcher):
    """An `HTTPFetcher` that passes requests on to the Zope publisher."""
    def __init__(self):
        self.urlopen = urllib2.build_opener(PublisherHTTPHandler).open

    def fetch(self, url, body=None, headers=None):
        if not fetchers._allowedURL(url):
            raise ValueError('Bad URL scheme: %r' % (url,))

        if headers is None:
            headers = {}

        headers.setdefault(
            'User-Agent',
            "%s Python-urllib/%s" % (fetchers.USER_AGENT,
                                     urllib2.__version__,))
        headers.setdefault('X-zope-handle-errors', True)

        req = urllib2.Request(url, data=body, headers=headers)
        try:
            f = self.urlopen(req)
            try:
                return self._makeResponse(f)
            finally:
                f.close()
        except urllib2.HTTPError, why:
            try:
                return self._makeResponse(why)
            finally:
                why.close()
