# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for vostok's custom publications."""

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase

from lp.vostok.publisher import VostokLayer

from zope.app.publication.requestpublicationregistry import factoryRegistry


VOSTOK_ENVIRONMENT = {
    'HTTP_HOST': config.vhost.vostok.hostname,
    'REQUEST_METHOD': 'GET',
    }

class TestRegistration(TestCase):
    """Vostok's publication customizations are installed correctly."""

    layer = FunctionalLayer

    def test_publication_factory_is_registered(self):
        # There is a vostok-specific request factory registered for the
        # hostname configured for vostok.
        factory = factoryRegistry.lookup(
            "GET", "text/html", VOSTOK_ENVIRONMENT)
        self.assertEqual('vostok', factory.vhost_name)

    def test_vostok_request_provides_vostok_layer(self):
        # The Request object constructed for requests to the vostok hostname
        # provides VostokLayer.
        factory = factoryRegistry.lookup(
            "GET", "text/html", VOSTOK_ENVIRONMENT)
        request_factory, publication = factory()
        request = request_factory('', VOSTOK_ENVIRONMENT)
        self.assertProvides(request, VostokLayer)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
