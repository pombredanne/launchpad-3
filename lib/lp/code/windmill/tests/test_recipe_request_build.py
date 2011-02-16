# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for requesting recipe builds."""

__metaclass__ = type
__all__ = []

import transaction
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.publisher import canonical_url
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )
from lp.testing.windmill.lpuser import login_person
from lp.app.browser.tales import PPAFormatterAPI
from lp.code.windmill.testing import CodeWindmillLayer
from lp.soyuz.model.processor import ProcessorFamily
from lp.testing import WindmillTestCase


class TestRecipeBuild(WindmillTestCase):
    """Test setting branch status."""

    layer = CodeWindmillLayer
    suite_name = "Request recipe build"

    def setUp(self):
        super(TestRecipeBuild, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test',
            email="chef@example.com")
        self.user = self.chef
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa')
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret', version='100.04',
            distribution=self.ppa.distribution)
        naked_squirrel = removeSecurityProxy(self.squirrel)
        naked_squirrel.nominatedarchindep = self.squirrel.newArch(
            'i386', ProcessorFamily.get(1), False, self.chef,
            supports_virtualized=True)
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(
            owner=self.chef, name='cake', product=chocolate)
        self.recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, distroseries=self.squirrel, name=u'cake_recipe',
            description=u'This recipe builds a foo for disto bar, with my'
            ' Secret Squirrel changes.', branches=[cake_branch],
            daily_build_archive=self.ppa, build_daily=True, is_stale=True)
        transaction.commit()
        login_person(self.chef, "chef@example.com", "test", self.client)

    def makeRecipeBuild(self):
        """Create and return a specific recipe."""
        build = self.factory.makeSourcePackageRecipeBuild(recipe=self.recipe)
        return build

    def test_recipe_build_request(self):
        """Request a recipe build."""

        client = self.client
        client.open(url=canonical_url(self.recipe))
        client.waits.forElement(
            id=u'request-builds', timeout=PAGE_LOAD)

        # Request a new build.
        client.click(id=u'request-builds')
        client.waits.forElement(id=u'field.archive')
        client.click(name=u'field.actions.request')

        # Ensure it shows up.
        client.waits.forElement(
            xpath = (u'//tr[contains(@class, "package-build")]/td[4]'
                     '/a[@href="%s"]') % PPAFormatterAPI(self.ppa).url(),
            timeout=SLEEP)

        # And try the same one again.
        client.click(id=u'request-builds')
        client.waits.forElement(id=u'field.archive')
        client.click(name=u'field.actions.request')

        # And check that there's an error.
        client.waits.forElement(
            xpath = (
                u'//div[contains(@class, "yui3-lazr-formoverlay-errors")]'
                '/ul/li'), timeout=FOR_ELEMENT)
        client.asserts.assertText(
            xpath = (
                u'//div[contains(@class, "yui3-lazr-formoverlay-errors")]'
                '/ul/li'),
            validator=u'An identical build is already pending for %s %s.'
                        % (self.ppa.distribution.name, self.squirrel.name))

    def test_recipe_daily_build_request(self):
        """Request a recipe build."""

        client = self.client
        client.open(url=canonical_url(self.recipe))
        client.waits.forElement(
            id=u'request-daily-builds', timeout=PAGE_LOAD)

        # Request a daily build.
        client.click(id=u'request-daily-builds')

        # Ensure it shows up.
        client.waits.forElement(
            xpath = (u'//tr[contains(@class, "package-build")]/td[4]'
                     '/a[@href="%s"]') % PPAFormatterAPI(self.ppa).url(),
            timeout=SLEEP)
