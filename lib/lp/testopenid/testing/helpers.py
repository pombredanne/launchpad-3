# Copyright 2010 Canonical Ltd.  All rights reserved.

"""Helpers for TestOpenID page tests."""

__metaclass__ = type
__all__ = [
    'complete_from_browser',
    'EchoView',
    'make_identifier_select_endpoint',
    'PublisherFetcher',
    ]

from StringIO import StringIO
import urllib2

from openid import fetchers
from openid.consumer.discover import (
    OPENID_IDP_2_0_TYPE,
    OpenIDServiceEndpoint,
    )
from zope.testbrowser.testing import PublisherHTTPHandler

from canonical.launchpad.webapp import LaunchpadView
from lp.testopenid.interfaces.server import get_server_url


class EchoView(LaunchpadView):
    """A view which just echoes its form arguments in the response."""

    def render(self):
        out = StringIO()
        print >> out, 'Request method: %s' % self.request.method
        keys = sorted(self.request.form.keys())
        for key in keys:
            print >> out, '%s:%s' % (key, self.request.form[key])
        return out.getvalue()


class PublisherFetcher(fetchers.Urllib2Fetcher):
    """An `HTTPFetcher` that passes requests on to the Zope publisher."""
    def __init__(self):
        super(PublisherFetcher, self).__init__()
        self.opener = urllib2.build_opener(PublisherHTTPHandler)

    def urlopen(self, request):
        request.add_header('X-zope-handle-errors', True)
        return self.opener.open(request)


def complete_from_browser(consumer, browser):
    """Complete OpenID request based on output of +echo.

    :param consumer: an OpenID `Consumer` instance.
    :param browser: a Zope testbrowser `Browser` instance.

    This function parses the body of the +echo view into a set of query
    arguments representing the OpenID response.
    """
    assert browser.contents.startswith('Request method'), (
        "Browser contents does not look like it came from +echo")
    # Skip the first line.
    query = dict(line.split(':', 1)
                 for line in browser.contents.splitlines()[1:])

    response = consumer.complete(query, browser.url)
    return response


def make_identifier_select_endpoint():
    """Create an endpoint for use in OpenID identifier select mode."""
    endpoint = OpenIDServiceEndpoint()
    endpoint.server_url = get_server_url()
    endpoint.type_uris = [OPENID_IDP_2_0_TYPE]
    return endpoint
