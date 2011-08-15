# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for browsing the root of the vostok skin."""

__metaclass__ = type

import os

from zope.publisher.defaultview import getDefaultViewName

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from lp.app.browser.tales import IMainTemplateFile
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view
from lp.vostok.browser.root import VostokRootView
from lp.vostok.browser.tests.request import VostokTestRequest
from lp.vostok.publisher import (
    VostokLayer,
    VostokRoot,
    )


class TestRootRegistrations(TestCase):
    """Test the registration of views for `VostokRoot`."""

    layer = FunctionalLayer

    def test_root_default_view_name(self):
        # The default view for the vostok root object is called "+index".
        view_name = getDefaultViewName(VostokRoot(), VostokTestRequest())
        self.assertEquals('+index', view_name)

    def test_root_index_view(self):
        # VostokRootView is registered as the view for the VostokRoot object.
        view = create_initialized_view(
            VostokRoot(), name='+index', layer=VostokLayer)
        self.assertIsInstance(view, VostokRootView)


class TestRootView(TestCaseWithFactory):
    """Tests for `VostokRootView`."""

    layer = DatabaseFunctionalLayer

    def view(self):
        return create_initialized_view(
            VostokRoot(), name='+index', layer=VostokLayer)

    def test_distributions(self):
        # VostokRootView.distributions is an iterable of all registered
        # distributions.
        root_view = self.view()
        new_distro = self.factory.makeDistribution()
        self.assertIn(new_distro, list(root_view.distributions))


class TestRootTemplate(TestCaseWithFactory):
    """Tests for the templates used by views of `VostokRoot`."""

    layer = DatabaseFunctionalLayer

    def test_distribution_list(self):
        # The element with id 'distro-list' on the root page contains a list
        # of links to all registered distributions.
        v = create_initialized_view(
            VostokRoot(), name='+index', layer=VostokLayer)
        contents = v.render()
        link_list = find_tag_by_id(contents, 'distro-list')('a')
        distro_list = list(v.distributions)
        self.assertEqual(len(link_list), len(distro_list))
        for distro, link in zip(distro_list, link_list):
            self.assertEqual(distro.displayname, extract_text(link))


class TestVostokLayerToMainTemplateAdapter(TestCase):

    layer = FunctionalLayer

    def test_path(self):
        main_template_path = IMainTemplateFile(VostokTestRequest()).path
        self.assertIn('lp/vostok', main_template_path)
        self.assertTrue(os.path.isfile(main_template_path))
