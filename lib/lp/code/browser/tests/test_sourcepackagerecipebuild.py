# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=F0401,E1002

"""Tests for the source package recipe view classes and templates."""

__metaclass__ = type

from mechanize import LinkNotFoundError
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.testing.pages import (
    extract_text, find_tags_by_class)
from canonical.launchpad.webapp import canonical_url
from canonical.testing import DatabaseFunctionalLayer
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.soyuz.model.processor import ProcessorFamily
from lp.testing import ANONYMOUS, BrowserTestCase, login, logout
from lp.testing.factory import remove_security_proxy_and_shout_at_engineer


class TestSourcePackageRecipeBuild(BrowserTestCase):
    """Create some sample data for recipe tests."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Provide useful defaults."""
        super(TestSourcePackageRecipeBuild, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test')
        self.user = self.chef
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa')
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret', version='100.04',
            distribution=self.ppa.distribution)
        naked_squirrel = remove_security_proxy_and_shout_at_engineer(
            self.squirrel)
        naked_squirrel.nominatedarchindep = self.squirrel.newArch(
            'i386', ProcessorFamily.get(1), False, self.chef,
            supports_virtualized=True)

    def makeRecipeBuild(self):
        """Create and return a specific recipe."""
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(
            owner=self.chef, name='cake', product=chocolate)
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, distroseries=self.squirrel, name=u'cake_recipe',
            description=u'This recipe builds a foo for disto bar, with my'
            ' Secret Squirrel changes.', branches=[cake_branch],
            daily_build_archive=self.ppa)
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe)
        return build

    def test_cancel_build(self):
        """An admin can cancel a build."""
        experts = getUtility(ILaunchpadCelebrities).bazaar_experts.teamowner
        queue = self.factory.makeSourcePackageRecipeBuildJob()
        build = queue.specific_job.build
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=experts)
        browser.getLink('Cancel build').click()

        self.assertEqual(
            browser.getLink('Cancel').url,
            build_url)

        browser.getControl('Cancel build').click()

        self.assertEqual(
            browser.url,
            build_url)

        login(ANONYMOUS)
        self.assertEqual(
            BuildStatus.SUPERSEDED,
            build.status)

    def test_cancel_build_not_admin(self):
        """No one but admins can cancel a build."""
        queue = self.factory.makeSourcePackageRecipeBuildJob()
        build = queue.specific_job.build
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=self.chef)
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink, 'Cancel build')

    def test_cancel_build_wrong_state(self):
        """If the build isn't queued, you can't cancel it."""
        experts = getUtility(ILaunchpadCelebrities).bazaar_experts.teamowner
        build = self.makeRecipeBuild()
        build.cancelBuild()
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=experts)
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink, 'Cancel build')

    def test_rescore_build(self):
        """An admin can rescore a build."""
        experts = getUtility(ILaunchpadCelebrities).bazaar_experts.teamowner
        queue = self.factory.makeSourcePackageRecipeBuildJob()
        build = queue.specific_job.build
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=experts)
        browser.getLink('Rescore build').click()

        self.assertEqual(
            browser.getLink('Cancel').url,
            build_url)

        browser.getControl('Score').value = '1024'

        browser.getControl('Rescore build').click()

        self.assertEqual(
            browser.url,
            build_url)

        login(ANONYMOUS)
        self.assertEqual(
            build.buildqueue_record.lastscore,
            1024)

    def test_rescore_build_invalid_score(self):
        """Build scores can only take numbers."""
        experts = getUtility(ILaunchpadCelebrities).bazaar_experts.teamowner
        queue = self.factory.makeSourcePackageRecipeBuildJob()
        build = queue.specific_job.build
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=experts)
        browser.getLink('Rescore build').click()

        self.assertEqual(
            browser.getLink('Cancel').url,
            build_url)

        browser.getControl('Score').value = 'tentwentyfour'

        browser.getControl('Rescore build').click()

        self.assertEqual(
            extract_text(find_tags_by_class(browser.contents, 'message')[1]),
            'You have specified an invalid value for score. '
            'Please specify an integer')

    def test_rescore_build_not_admin(self):
        """No one but admins can rescore a build."""
        queue = self.factory.makeSourcePackageRecipeBuildJob()
        build = queue.specific_job.build
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=self.chef)
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink, 'Rescore build')

    def test_rescore_build_wrong_state(self):
        """If the build isn't queued, you can't rescore it."""
        experts = getUtility(ILaunchpadCelebrities).bazaar_experts.teamowner
        build = self.makeRecipeBuild()
        build.cancelBuild()
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=experts)
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink, 'Rescore build')
