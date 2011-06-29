# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test LibraryFileAliasView."""

__metaclass__ = type

import httplib

from zope.component import getMultiAdapter
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestLibraryFileAliasView(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def test_deleted_lfa(self):
        # When we initialise a LibraryFileAliasView against a deleted LFA,
        # we throw a 410 Gone error.
        lfa = self.factory.makeLibraryFileAlias()
        removeSecurityProxy(lfa).content = None
        self.assertTrue(lfa.deleted)
        request = LaunchpadTestRequest(
            environ={'REQUEST_METHOD': 'GET', 'HTTP_X_SCHEME' : 'http' })
        view = getMultiAdapter((lfa, request), name='+index')
        view.initialize()
        self.assertEqual(httplib.GONE, view.request.response.getStatus())
