# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.config import config
from canonical.launchpad.windmill.testing import constants

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestRegistryYUIUnitTests(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'RegistryYUIUnitTests'
    view_name = u'/+yui-unittest'
    test_path = view_name + u'/canonical/launchpad/javascript'

    def test_YUITestFileView(self):
        client = self.client
        client.open(
            url=self.test_path + u'/registry/tests/milestone_table.html')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.waits.forElement(id='complete')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
