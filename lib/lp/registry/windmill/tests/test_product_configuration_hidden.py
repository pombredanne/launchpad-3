# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

import transaction

from canonical.launchpad.windmill.testing import (
    constants,
    lpuser,
    )
from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.service_usage_helpers import set_service_usage


class TestProductHiddenConfiguration(WindmillTestCase):
    """Test the Configuration links show/hide controls on products.

    Controls only work with javascript enabled.
    """

    layer = RegistryWindmillLayer
    suite_name = "Product configuration links hidden"

    def setUp(self):
        super(TestProductHiddenConfiguration, self).setUp()
        self.product = self.factory.makeProduct(name='hidden-configs')
        transaction.commit()

    def test_not_fully_configured_starts_shown(self):
        # A product that is not fully configured displays the links on
        # page load, but they can be hidden.
        client = self.client

        client.open(url=u'http://launchpad.dev:8085/hidden-configs')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        lpuser.FOO_BAR.ensure_login(client)

        # We can only safely use this class selector in this test b/c there's
        # only one collapsible element on this page.
        client.asserts.assertNotProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

        # When the "Configuration links" link is clicked and the actual links are
        # shown, the collapsible wrapper collapses, hiding the links.
        client.click(link=u"Configuration options")
        client.waits.forElement(
            classname="collapseWrapper lazr-closed",
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

    def test_configured_starts_collapsed(self):
        # A product that is fully configured hides the links on page
        # load, but they can be hidden.
        set_service_usage(
            self.product.name,
            codehosting_usage="EXTERNAL",
            bug_tracking_usage="LAUNCHPAD",
            answers_usage="EXTERNAL",
            translations_usage="NOT_APPLICABLE")
        transaction.commit()

        client = self.client

        client.open(url=u'http://launchpad.dev:8085/hidden-configs')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        lpuser.FOO_BAR.ensure_login(client)
        client.waits.forElement(
            classname='collapseWrapper lazr-closed',
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

        # When the "Configuration links" link is clicked and the actual links are
        # hidden, the collapsible wrapper opens, showing the links.
        client.click(link=u"Configuration options")
        client.waits.forElement(
            classname="lazr-opened",
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-open')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
