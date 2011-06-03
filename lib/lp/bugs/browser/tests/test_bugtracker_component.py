# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for linking bug tracker components to source packages."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class BugTrackerEditComponentViewTextCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BugTrackerEditComponentViewTextCase, self).setUp()
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
        distro = getUtility(IDistributionSet).getByName('ubuntu')
        package = self.factory.makeDistributionSourcePackage(
            sourcepackagename='example', distribution=distro)
        form = self._makeForm(package)
        view = create_initialized_view(
            component, name='+edit', form=form)
        label = 'Link a distribution source package to Example component'
        self.assertEqual(label, view.label)
        self.assertEqual('Link component', view.page_title)
        self.assertEqual(['sourcepackagename'], view.field_names)
        url = canonical_url(component.component_group.bug_tracker)
        self.assertEqual(url, view.next_url)
        self.assertEqual(url, view.cancel_url)

    def test_linking(self):
        component = self.factory.makeBugTrackerComponent(
            u'Example', self.comp_group)
        distro = getUtility(IDistributionSet).getByName('ubuntu')
        package = self.factory.makeDistributionSourcePackage(
            sourcepackagename='example', distribution=distro)

        self.assertIs(None, component.distro_source_package)
        form = self._makeForm(package)
        view = create_initialized_view(
            component, name='+edit', form=form)
        self.assertEqual([], view.errors)

        notifications = view.request.response.notifications
        #self.assertEqual(1, len(notifications))
        self.assertEqual(component.distro_source_package, package)
        expected = (
            u"alpha:Example is now linked to the example "
            "source package in ubuntu")
        self.assertEqual(expected, notifications.pop().message)

    def test_cannot_doublelink_sourcepackages(self):
        # Two components try linking to same package
        component_a = self.factory.makeBugTrackerComponent(
            u'a', self.comp_group)
        component_b = self.factory.makeBugTrackerComponent(
            u'b', self.comp_group)
        distro = getUtility(IDistributionSet).getByName('ubuntu')
        package = self.factory.makeDistributionSourcePackage(
            sourcepackagename='example', distribution=distro)

        form = self._makeForm(package)
        view = create_initialized_view(
            component_a, name='+edit', form=form)
        notifications = view.request.response.notifications
        self.assertEqual([], view.errors)
        self.assertEqual(1, len(notifications))
        self.assertEqual(package, component_a.distro_source_package)

        form = self._makeForm(package)
        view = create_initialized_view(
            component_b, name='+edit', form=form)
        self.assertIs(None, component_b.distro_source_package)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            u"""The example source package is already linked to """
            """alpha:a in ubuntu""")
        self.assertEqual(expected, notifications.pop().message)
