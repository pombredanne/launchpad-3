# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test error views."""

from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCase


class TestSystemErrorView(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_without_oops_id(self):
        request = LaunchpadTestRequest()
        SystemErrorView(Exception(), request)
        self.assertEquals(500, request.response.getStatus())
        self.assertEquals(
            None,
            request.response.getHeader('X-Lazr-OopsId', literal=True))

    def test_with_oops_id(self):
        request = LaunchpadTestRequest()
        request.oopsid = 'OOPS-1X1'
        SystemErrorView(Exception(), request)
        self.assertEquals(500, request.response.getStatus())
        self.assertEquals(
            'OOPS-1X1',
            request.response.getHeader('X-Lazr-OopsId', literal=True))
