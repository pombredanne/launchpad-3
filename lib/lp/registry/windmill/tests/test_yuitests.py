# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.config import config
from canonical.launchpad.windmill.testing import constants
from canonical.launchpad.testing.pages import find_tags_by_class

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class YUIUnitTestCase(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'RegistryYUIUnitTests'

    _yui_results = None
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
            self._yui_results = {}
            entries = find_tags_by_class(
                response['result'], 'yui-console-entry-TestRunner')
            for entry in entries:
                category = entry.find(
                    attrs={'class': 'yui-console-entry-cat'})
                if category is None:
                    continue
                result = category.string
                if result not in ('pass', 'fail'):
                    continue
                message = entry.pre.string
                test_name, ignore = message.split(':', 1)
                self._yui_results[test_name] = dict(
                    result=result, message=message)

    def runTest(self):
        if self._yui_results is None or len(self._yui_results) == 0:
            self.fail("Test harness or js failed.")
        for test_name in self._yui_results:
            result = self._yui_results[test_name]
            self.assertTrue('pass' == result['result'],
                    'Failure in %s.%s: %s' % (
                        self.test_path, test_name, result['message']))


def test_suite():
    test_path = (
        u'canonical/launchpad/javascript/registry/tests/milestone_table.html')
    test_case = YUIUnitTestCase()
    test_case.initialize(test_path)
    suite = unittest.TestSuite()
    suite.addTest(test_case)
    return suite
