# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helpers for OpenID page tests."""

__metaclass__ = type
__all__ = ['install_consumerview', 'uninstall_consumerview']

from StringIO import StringIO

from zope.app.testing.ztapi import browserView
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.checker import defineChecker, Checker, CheckerPublic

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

