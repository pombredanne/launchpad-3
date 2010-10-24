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

#       set_service_usage(
#           self.product.name,
#           codehosting_usage="EXTERNAL",
#           bug_tracking_usage="LAUNCHPAD",
#           answers_usage="EXTERNAL",
#           translations_usage="NOT_APPLICABLE")

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
        lpuser.SAMPLE_PERSON.ensure_login(client)
        client.asserts.assertNotProperty(
            id='configuration_links',    
            validator='className|collapsed')
        


def _test_expander(client):
    extra_opts_form = u"//div[@id='show-hide-configs']/div"
    form_closed = u"%s[@class='collapsed']" % extra_opts_form
    form_opened = u"%s[@class='expanded']" % extra_opts_form

    # The collapsible area is collapsed and doesn't display.
    client.asserts.assertNode(xpath=form_closed)

    # Click to expand the extra options form.
    client.click(link=u'Extra options')

    # The collapsible area is expanded and does display.
    client.asserts.assertNode(xpath=form_opened)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
