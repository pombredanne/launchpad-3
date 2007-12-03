# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helpers for OpenID page tests."""

__metaclass__ = type
__all__ = [
    'PublisherFetcher',
    'install_consumerview',
    'make_endpoint',
    'make_identifier_select_endpoint',
    'maybe_fixup_identifier_select_request',
    'uninstall_consumerview',
]

from StringIO import StringIO
import urllib2

from openid import fetchers
from openid.consumer.discover import (
    OpenIDServiceEndpoint, OPENID_1_0_TYPE, OPENID_1_1_TYPE,
    OPENID_2_0_TYPE, OPENID_IDP_2_0_TYPE)
from openid.message import IDENTIFIER_SELECT

from zope.app.testing.ztapi import browserView
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.checker import defineChecker, Checker, CheckerPublic
from zope.testbrowser.testing import PublisherHTTPHandler

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.vhosts import allvhosts


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


def install_consumer():
    defineChecker(ConsumerView, Checker({
        '__call__': CheckerPublic,
        'browserDefault': CheckerPublic,
        'render': CheckerPublic}))
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


def make_endpoint(protocol_uri, claimed_id, local_id=None):
    """Create an endpoint for use with `Consumer.beginWithoutDiscovery`."""
    assert protocol_uri in [
        OPENID_1_0_TYPE, OPENID_1_1_TYPE, OPENID_2_0_TYPE], (
        "Unexpected protocol URI: %s" % protocol_uri)

    endpoint = OpenIDServiceEndpoint()
    endpoint.type_uris = [protocol_uri]
    endpoint.server_url = allvhosts.configs['openid'].rooturl + '+openid'
    endpoint.claimed_id = claimed_id
    endpoint.local_id = local_id or claimed_id
    return endpoint


def make_identifier_select_endpoint(protocol_uri):
    """Create an identifier select OpenID endpoint.

    If the OpenID 1.x protocol is selected, the endpoint will be
    suitable for use with Launchpad's non-standard identifier select
    workflow.
    """
    assert protocol_uri in [
        OPENID_1_0_TYPE, OPENID_1_1_TYPE, OPENID_2_0_TYPE], (
        "Unexpected protocol URI: %s" % protocol_uri)

    endpoint = OpenIDServiceEndpoint()
    endpoint.server_url = allvhosts.configs['openid'].rooturl + '+openid'
    if protocol_uri == OPENID_2_0_TYPE:
        endpoint.type_uris = [OPENID_IDP_2_0_TYPE]
    else:
        endpoint.type_uris = [protocol_uri]
        endpoint.claimed_id = IDENTIFIER_SELECT
        endpoint.local_id = IDENTIFIER_SELECT
    return endpoint


def maybe_fixup_identifier_select_request(consumer, claimed_id):
    """Fix up an OpenID 1.1 identifier select request.

    OpenID 1.1 does not support identifier select, so responses using
    our non-standard identifier select mode appear to be corrupt.

    This function checks to see if the current request was a 1.1
    identifier select one, and updates the internal state to use the
    given claimed ID if so.
    """
    endpoint = consumer.session[consumer._token_key]
    if (OPENID_1_0_TYPE in endpoint.type_uris or
        OPENID_1_1_TYPE in endpoint.type_uris):
        assert endpoint.claimed_id == IDENTIFIER_SELECT, (
            "Request did not use identifier select mode")
        endpoint.claimed_id = claimed_id
        endpoint.local_id = claimed_id
    else:
        # For standard identifier select, local_id is None.
        assert endpoint.local_id is None, (
            "Request did not use identifier select mode")
