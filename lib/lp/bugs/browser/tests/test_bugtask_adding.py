# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from zope.component import getUtility

from lp.registry.interfaces.packaging import IPackagingUtil
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.ftests import login_person
from canonical.testing import DatabaseFunctionalLayer


class TestProductBugTaskCreationStep(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductBugTaskCreationStep, self).setUp()
        self.ubuntu_series = getUtility(ILaunchpadCelebrities).ubuntu['hoary']
        self.sourcepackagename = self.factory.makeSourcePackageName('bat')
        self.sourcepackage = self.factory.makeSourcePackage(
            sourcepackagename=self.sourcepackagename,
            distroseries=self.ubuntu_series)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.sourcepackagename,
            distroseries=self.ubuntu_series)
        self.product = self.factory.makeProduct(name="bat")
        self.packaging_util = getUtility(IPackagingUtil)
        self.user = self.factory.makePerson()
        login_person(self.user)
        self.bug_task = self.factory.makeBugTask(
            target=self.sourcepackage, owner=self.user)
        self.bug = self.bug_task.bug

    def test_create_upstream_bugtask_without_packaging(self):
        form = {
            'field.product': 'bat',
            'field.add_packaging': 'off',
            'field.__visited_steps__':
                'choose_product|specify_remote_bug_url',
            'field.actions.continue': 'Continue',
            }
        view = create_initialized_view(
            self.bug_task, '+choose-affected-product', form=form)
        self.assertEqual([], view.view.errors)
        self.assertTrue(self.bug.getBugTask(self.product) is not None)
        has_packaging = self.packaging_util.packagingEntryExists(
            self.sourcepackagename, self.ubuntu_series,
            self.product.development_focus)
        self.assertFalse(has_packaging)

    def test_create_upstream_bugtask_with_packaging(self):
        form = {
            'field.product': 'bat',
            'field.add_packaging': 'on',
            'field.__visited_steps__':
                'choose_product|specify_remote_bug_url',
            'field.actions.continue': 'Continue',
            }
        view = create_initialized_view(
            self.bug_task, '+choose-affected-product', form=form)
        self.assertEqual([], view.view.errors)
        self.assertTrue(self.bug.getBugTask(self.product) is not None)
        has_packaging = self.packaging_util.packagingEntryExists(
            self.sourcepackagename, self.ubuntu_series,
            self.product.development_focus)
        self.assertTrue(has_packaging)
