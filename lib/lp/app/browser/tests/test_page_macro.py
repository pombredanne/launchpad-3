# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Launchpad's 'view/macro:page' TALES adapter."""

__metaclass__ = type

import os

from zope.component import getMultiAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.launchpad.webapp.publisher import rootObject
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import FunctionalLayer
from lp.testing import TestCase


class TestPageMacroDispatcher(TestCase):

    layer = FunctionalLayer

    def test_base_template(self):
        # Requests on the launchpad.dev vhost use the Launchpad base template.
        root_view = getMultiAdapter(
            (rootObject, LaunchpadTestRequest()), name='index.html')
        adapter = getMultiAdapter([root_view], IPathAdapter, name='macro')
        template_path = os.path.normpath(adapter.base.filename)
        self.assertIn('lp/app/templates', template_path)
        # The base template defines a 'master' macro as the adapter expects.
        self.assertIn('master', adapter.base.macros.keys())
