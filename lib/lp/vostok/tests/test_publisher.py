# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for vostok's custom publications."""

__metaclass__ = type

from canonical.config import config
from canonical.testing.layers import FunctionalLayer
from lp.testing import TestCase
from lp.testing.publication import get_request_and_publication
from lp.vostok.publisher import (
    VostokBrowserRequest,
    VostokBrowserResponse,
    VostokLayer,
    VostokRoot,
    )


class TestRegistration(TestCase):
    """Vostok's publication customizations are installed correctly."""

    layer = FunctionalLayer

    def test_vostok_request_provides_vostok_layer(self):
        # The request constructed for requests to the vostok hostname provides
        # VostokLayer.
        request, publication = get_request_and_publication(
            host=config.vhost.vostok.hostname)
        self.assertProvides(request, VostokLayer)

    def test_root_object(self):
        # The root object for requests to the vostok host is an instance of
        # VostokRoot.
        request, publication = get_request_and_publication(
            host=config.vhost.vostok.hostname)
        self.assertProvides(request, VostokLayer)
        root = publication.getApplication(request)
        self.assertIsInstance(root, VostokRoot)


class TestVostokBrowserRequest(TestCase):

    def test_createResponse(self):
        request = VostokBrowserRequest(None, {})
        self.assertIsInstance(
            request._createResponse(), VostokBrowserResponse)


class TestVostokBrowserResponse(TestCase):

    def test_redirect_to_different_host(self):
        # Unlike Launchpad's BrowserResponse class, VostokBrowserResponse
        # doesn't allow redirects to any host other than the current one.
        request = VostokBrowserRequest(None, {})
        response = request._createResponse()
        response._request = request
        self.assertRaises(
            ValueError, response.redirect, 'http://launchpad.dev')
