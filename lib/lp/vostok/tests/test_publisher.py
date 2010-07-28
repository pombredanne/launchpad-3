# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for vostok's custom publications."""

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.testing.layers import FunctionalLayer
from canonical.launchpad.webapp.interfaces import IOpenLaunchBag

from lp.testing import TestCase
from lp.testing.publication import get_request_and_publication

from lp.vostok.publisher import VostokLayer, VostokRoot

from zope.component import getUtility


class TestRegistration(TestCase):
    """Vostok's publication customizations are installed correctly."""

    layer = FunctionalLayer

    def test_code_request_provides_code_layer(self):
        # The request constructed for requests to the code hostname provides
        # CodeLayer.
        request, publication = get_request_and_publication(
            host=config.vhost.code.hostname)
        self.assertProvides(request, VostokLayer)

    def test_root_object(self):
        # The root object for requests to the vostok host is an instance of
        # VostokRoot.
        request, publication = get_request_and_publication(
            host=config.vhost.code.hostname)
        self.assertProvides(request, VostokLayer)
        # XXX This shouldn't be needed:
        # XXX Use test traverse instead?
        getUtility(IOpenLaunchBag).clear()
        root = publication.getApplication(request)
        self.assertIsInstance(root, VostokRoot)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
