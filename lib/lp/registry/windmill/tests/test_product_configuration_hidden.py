# Copyright 2009 Canonical Ltd.  This software is licensed under the
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

    layer = RegistryWindmillLayer
    suite_name = "Product configuration links hidden"

    def setUp(self):
        super(TestProductHiddenConfiguration, self).setUp()
        self.product = self.factory.makeProduct(name='hidden-configs')
        transaction.commit()

    def test_not_fully_configured_starts_shown(self):
        """Test the Configuration links on a product.

        This test ensures that, with Javascript enabled, the configuration
        links start closed on a fully configured project, and show all
        configuration links when opened.

        Additionally, on a not fully configured project, it starts by showing
        the links, and can be closed.
        """
        client = self.client

        client.open(url=u'http://launchpad.dev:8085/hidden-configs')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        lpuser.FOO_BAR.ensure_login(client)
        # We can only safe use this class selector in this test b/c there's
        # only one collapsible element on this page.
        client.asserts.assertNotProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

        # When the Show link is clicked when it's open, it closes it.
        client.click(link=u"Show configuration links")
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

    def test_configured_starts_collapsed(self):
        """Test the Configuration links on a product.

        This test ensures that, with Javascript enabled, the configuration
        links start closed on a fully configured project, and show all
        configuration links when opened.

        Additionally, on a not fully configured project, it starts by showing
        the links, and can be closed.
        """
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
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-closed')

        client.click(link=u"Show configuration links")
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertProperty(
            classname='collapseWrapper',
            validator='className|lazr-open')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
