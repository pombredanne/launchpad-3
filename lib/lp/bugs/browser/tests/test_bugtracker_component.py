# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for linking bug tracker components to source packages."""

__metaclass__ = type

import unittest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestBugTrackerEditComponentView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTrackerEditComponentView, self).setUp()
        regular_user = self.factory.makePerson()
        login_person(regular_user)

        self.bug_tracker = self.factory.makeBugTracker()
        self.comp_group = self.factory.makeBugTrackerComponentGroup(
            u'alpha', self.bug_tracker)

    def _makeForm(self, sourcepackage):
        if sourcepackage is None:
            name = ''
        else:
            name = sourcepackage.name
        return {
            'field.sourcepackagename': name,
            'field.actions.save': 'Save',
            }

    def test_view_attributes(self):
        component = self.factory.makeBugTrackerComponent(
            u'Example', self.comp_group)
        form = self._makeForm(component)
        view = create_initialized_view(
            component, name='+edit', form=form)
        label = 'Link a distribution source package to the Example component'
        self.assertEqual(label, view.label)
        self.assertEqual(label, view.page_title)
        fields = ['sourcepackagename']
        self.assertEqual(fields, view.field_names)

    def test_linking(self):
        component = self.factory.makeBugTrackerComponent(
            u'Example', self.comp_group)
        package = self.factory.makeDistributionSourcePackage()
        self.assertIs(None, component.distro_source_package)

        form = self._makeForm(component)
        view = create_initialized_view(
            component, name='+edit', form=form)
        self.assertEqual([], view.errors)

        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(component.distro_source_package, package)
        expected = (
            "Test:Example is now linked to the foobar source package in Ubuntu")
        self.assertEqual(expected, notifications.pop().message)

    def test_cannot_doublelink_sourcepackages(self):
        # Two components try linking to same package
        component_a = self.factory.makeBugTrackerComponent(
            u'a', self.comp_group)
        component_b = self.factory.makeBugTrackerComponent(
            u'b', self.comp_group)
        package = self.factory.makeDistributionSourcePackage()

        form = self._makeForm(package)
        view = create_initialized_view(
            package, name='+edit', form=form)
        # TODO: How to cause the form to do its link action?
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual([], view.errors)
        self.assertEqual(component_a.distro_source_package, package)

        form = self._makeForm(component_b)
        view = create_initialized_view(
            package, name='+edit', form=form)
        # TODO: How to cause the form to do its link action?
        contents = view.render()
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual([], view.errors)
        self.assertIs(None, component_b.distro_source_package)
        self.assertEqual(1, len(view.errors))
        expected = (
            " is already linked to an upstream bugtracker component")
        self.assertEqual(expected, view.errors.pop())

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
