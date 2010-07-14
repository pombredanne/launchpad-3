# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase

from zope.app.publication.requestpublicationregistry import factoryRegistry


class TestRegistration(TestCase):

    layer = FunctionalLayer

    def test_publication_factory_is_registered(self):
        # lp.vostok.publisher.vostok_request_publication_factory is registered
        # as the publication factory for requests to the hostname configured
        # for vostok.
        factory = factoryRegistry.lookup(
            "GET", "text/html", {'HTTP_HOST': config.vhost.vostok.hostname})
        self.assertEqual('vostok', factory.vhost_name)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
