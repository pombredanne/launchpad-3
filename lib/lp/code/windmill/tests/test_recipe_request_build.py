# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for requesting recipe builds."""

__metaclass__ = type
__all__ = []

import transaction
from zope.component import getUtility
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
from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.model.processor import ProcessorFamily
from lp.testing import WindmillTestCase, quote_jquery_expression


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

    def _check_build_renders(self, ppa):
        self.client.waits.forElement(
            jquery=u"('tr.package-build a[href$=\"%s\"]')"
            % quote_jquery_expression(PPAFormatterAPI(ppa).url()),
            timeout=FOR_ELEMENT)

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
        self._check_build_renders(self.ppa)

    def test_recipe_build_request_already_pending(self):
        """Test that already pending builds are correctly highlighted.

        If all possible builds are pending, the the Request Builds button
        should be hidden.
        """

        client = self.client
        client.open(url=canonical_url(self.recipe))
        client.waits.forElement(
            id=u'request-builds', timeout=PAGE_LOAD)

        # Request a new build.
        client.click(id=u'request-builds')
        client.waits.forElement(id=u'field.archive')
        client.click(name=u'field.actions.request')

        # Give the new build a chance to be queued.
        client.waits.sleep(milliseconds=SLEEP)

        # And open the request form again.
        client.click(id=u'request-builds')
        client.waits.forElement(id=u'field.archive')

        def check_build_pending(field_id, build_name):
            client.asserts.assertTextIn(
                jquery=u"('label[for=\"field.distros.%d\"]')[0]" % field_id,
                validator=u'%s (build pending)' % build_name)

        # We need just a little time for the ajax call to complete
        client.waits.sleep(milliseconds=SLEEP)

        # Check that previous build is marked as pending
        check_build_pending(0, self.squirrel.displayname)

        # Now request builds for all the remaining distro series
        client.click(id=u'field.distros.1')
        client.click(id=u'field.distros.2')
        client.click(name=u'field.actions.request')

        # Give the new builds a chance to be queued.
        client.waits.sleep(milliseconds=SLEEP)

        distribution_set = getUtility(IDistributionSet)
        ubuntu_hoary = distribution_set.getByName('ubuntu').getSeries('hoary')
        ubuntu_warty = distribution_set.getByName('ubuntu').getSeries('warty')

        # Ensure new builds shows up.
        self._check_build_renders(ubuntu_hoary)
        self._check_build_renders(ubuntu_warty)

        # And open the request form again.
        client.click(id=u'request-builds')
        client.waits.forElement(id=u'field.archive')

        # We need just a little time for the ajax call to complete
        client.waits.sleep(milliseconds=SLEEP)

        # Check that previous builds are marked as pending
        check_build_pending(0, self.squirrel.displayname)
        check_build_pending(1, ubuntu_hoary.displayname)
        check_build_pending(2, ubuntu_warty.displayname)

        # Check that the Request Builds button is hidden
        client.asserts.assertNode(
            jquery=(u"('div.yui3-lazr-formoverlay-actions button[name=\""
                    "field.actions.request display=\"None\"\"]')"))

    def test_recipe_daily_build_request(self):
        """Request a recipe build."""

        client = self.client
        client.open(url=canonical_url(self.recipe))
        client.waits.forElement(
            id=u'request-daily-build', timeout=PAGE_LOAD)

        # Request a daily build.
        client.click(id=u'request-daily-build')

        # Ensure it shows up.
        client.waits.forElement(
            jquery=u"('tr.package-build a[href$=\"%s\"]')"
            % quote_jquery_expression(PPAFormatterAPI(self.ppa).url()),
            timeout=FOR_ELEMENT)
