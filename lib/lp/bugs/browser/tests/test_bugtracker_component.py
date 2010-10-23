# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for linking bug tracker components to source packages."""

__metaclass__ = type

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
            u'alpha',
            self.bug_tracker)
        self.component = self.factory.makeBugTrackerComponent(
            u'Example',
            self.comp_group)

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
        view = create_initialized_view(
            self.component, name='+edit')
        label = 'Link a distribution source package to the Example component'
        self.assertEqual(label, view.label)
        self.assertEqual(label, view.page_title)
        fields = ['sourcepackagename']
        self.assertEqual(fields, view.field_names)

    def test_linking(self):
        form = self._makeForm(self.owner)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.security_contact, self.owner)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            "Test:Example is now linked to the foobar source package in Ubuntu")
        self.assertEqual(expected, notifications.pop().message)
        
    def test_cannot_doublelink_sourcepackages(self):
        # Two components try linking to same package
        form = self._makeForm(self.owner)
        self.assertEqual(1, len(view.errors))
        expected = (
            "foobar is already linked to an upstream bugtracker component")
        self.assertEqual(expected, view.errors.pop())

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
