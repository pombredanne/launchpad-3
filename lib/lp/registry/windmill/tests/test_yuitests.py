# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getSiteManager
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.config import config
from canonical.launchpad.windmill.testing import constants
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp.publisher import LaunchpadView

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestRegistryYUIUnitTests(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'RegistryYUIUnitTests'

    def test_YUITestFileView(self):
        client = self.client
        client.open(url=u'/+yui-unittest')
        client.waits.forPageLoad(timeout=10000)
        client.asserts.assertTextIn(
            xpath="//p", validator='goodbye')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
