# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

import re
import unittest

from canonical.config import config
from canonical.launchpad.windmill.testing import constants

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestRegistryYUIUnitTests(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'RegistryYUIUnitTests'
    log_pattern = re.compile(r'<pre id="python-log">\|\|(.*)</pre>')
    view_name = u'/+yui-unittest/'
    test_dir = u'canonical/launchpad/javascript'
    test_path = test_dir + u'/registry/tests/milestone_table.html'

    def test_YUITestFileView(self):
        client = self.client
        client.open(url=self.view_name + self.test_path)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.waits.forElement(id='complete')
        response = client.commands.getPageText()
        match = self.log_pattern.search(response['result'])
        lines = match.group(1).split('||')
        for line in lines:
            result, test_name, unit_test_name = line.split('::')
            self.assertTrue('pass' == result,
                'Failue in %s.%s' % (unit_test_name, test_name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
