# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for bug set and bug application views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.malone import IMaloneApplication
from lp.bugs.publisher import BugsLayer
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestMaloneView(TestCaseWithFactory):
    """Test the MaloneView for the Bugs application."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMaloneView, self).setUp()
        self.application = getUtility(IMaloneApplication)

    def test_redirect_id_success(self):
        # The view redirects to the bug when it is found.
        bug = self.factory.makeBug()
        form = dict(id=str(bug.id))
        view = create_initialized_view(
            self.application, name='+index', layer=BugsLayer, form=form)
        self.assertEqual(None, view.error_message)
        self.assertEqual(
            canonical_url(bug), view.request.response.getHeader('Location'))

    def test_redirect_name_success(self):
        # The view redirects to the bug when it is found.
        bug = self.factory.makeBug()
        with celebrity_logged_in('admin'):
            bug.name = 'bingo'
        form = dict(id='bingo')
        view = create_initialized_view(
            self.application, name='+index', layer=BugsLayer, form=form)
        self.assertEqual(None, view.error_message)
        self.assertEqual(
            canonical_url(bug), view.request.response.getHeader('Location'))

    def test_redirect_unknown_bug_fail(self):
        # The view reports an error and does not redirect if the bug is not
        # found.
        form = dict(id='fnord')
        view = create_initialized_view(
            self.application, name='+index', layer=BugsLayer, form=form)
        self.assertEqual(
            "Bug 'fnord' is not registered.", view.error_message)
        self.assertEqual(None, view.request.response.getHeader('Location'))

    def test_redirect_list_of_bug_fail(self):
        # The view reports an error and does not redirect if list is provided
        # instead of a string.
        form = dict(id=['fnord', 'pting'])
        view = create_initialized_view(
            self.application, name='+index', layer=BugsLayer, form=form)
        self.assertEqual(
            "Bug ['fnord', 'pting'] is not registered.", view.error_message)
        self.assertEqual(None, view.request.response.getHeader('Location'))

    def test_search_specifications_form_rendering(self):
        # The view's template directly renders the form widgets.
        view = create_initialized_view(self.application, '+index')
        content = find_tag_by_id(view.render(), 'search-all-bugs')
        self.assertEqual('form', content.name)
        self.assertTrue(
            content.find(True, id='field.searchtext') is not None)
        self.assertTrue(
            content.find(True, id='field.actions.search') is not None)
        self.assertTrue(
            content.find(True, id='field.scope.option.all') is not None)
        self.assertTrue(
            content.find(True, id='field.scope.option.project') is not None)
        target_widget = view.widgets['scope'].target_widget
        self.assertTrue(
            content.find(True, id=target_widget.show_widget_id) is not None)
        text = str(content)
        picker_script = (
            "Y.lp.app.picker.create('DistributionOrProductOrProjectGroup'")
        self.assertTrue(picker_script in text)
        focus_script = "setFocusByName('field.searchtext')"
        self.assertTrue(focus_script in text)
