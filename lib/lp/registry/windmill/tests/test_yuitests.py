# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

import re
import unittest

from windmill.authoring import WindmillTestClient

from canonical.config import config
from canonical.launchpad.windmill.testing import constants

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class YUIUnitTestCase(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'RegistryYUIUnitTests'

    _yui_results = None
    _log_pattern = re.compile(r'<pre id="python-log">\|\|(.*)</pre>')
    _view_name = u'http://launchpad.dev:8085/+yui-unittest/'

    def initialize(self, test_path):
        self.test_path = test_path
        self.yui_runner_url = self._view_name + test_path

    def setUp(self):
        super(YUIUnitTestCase, self).setUp()
        if self._yui_results is None:
            client = self.client
            client.open(url=self.yui_runner_url)
            client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
            client.waits.forElement(id='complete')
            response = client.commands.getPageText()
            match = self._log_pattern.search(response['result'])
            self._yui_results = {}
            lines = match.group(1).split('||')
            for line in lines:
                result, test_name, unit_test_name = line.split('::')
                self._yui_results[test_name] = dict(
                    result=result, message='oops',
                    unit_test_name=unit_test_name)

    def _verify_test(self, test_name):
        if test_name not in self._yui_results:
            self.fail("Test harness or js failed.")
        result = self._yui_results[test_name]
        self.assertTrue('pass' == result,
                'Failue in %s.%s: %s' % (
                    result['unit_test_name'], test_name, result['message']))

    def runTest(self):
        if self._yui_results is None:
            self.fail("Test harness or js failed.")
        for test_name in self._yui_results:
            result = self._yui_results[test_name]
            self.assertTrue('pass' == result['result'],
                    'Failue in %s.%s: %s' % (
                        result['unit_test_name'],
                        test_name, result['message']))


def test_suite():
    test_path = (
        u'canonical/launchpad/javascript/registry/tests/milestone_table.html')
    test_case = YUIUnitTestCase()
    test_case.initialize(test_path)
    suite = unittest.TestSuite()
    suite.addTest(test_case)
    return suite
