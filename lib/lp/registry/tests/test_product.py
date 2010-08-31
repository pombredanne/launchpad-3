# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from cStringIO import StringIO
import datetime
import unittest

from lazr.lifecycle.snapshot import Snapshot
import pytz
import transaction
from zope.component import getUtility

from canonical.launchpad.ftests import (
    login,
    syncUpdate,
    )
from canonical.launchpad.testing.pages import (
    find_main_content,
    get_feedback_messages,
    setupBrowser,
    )
from canonical.testing import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import (
    IProduct,
    License,
    )
from lp.registry.model.commercialsubscription import CommercialSubscription
from lp.registry.model.product import Product
from lp.registry.model.productlicense import ProductLicense
from lp.testing import TestCaseWithFactory


class TestProduct(TestCaseWithFactory):
    """Tests product object."""

    layer = LaunchpadFunctionalLayer

    def test_deactivation_failure(self):
        # Ensure that a product cannot be deactivated if
        # it is linked to source packages.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        source_package = self.factory.makeSourcePackage()
        self.assertEqual(True, product.active)
        source_package.setPackaging(
            product.development_focus, self.factory.makePerson())
        self.assertRaises(
            AssertionError,
            setattr, product, 'active', False)

    def test_deactivation_success(self):
        # Ensure that a product can be deactivated if
        # it is not linked to source packages.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        self.assertEqual(True, product.active)
        product.active = False
        self.assertEqual(False, product.active)

    def test_milestone_sorting_getMilestonesAndReleases(self):
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        milestone_0_1 = self.factory.makeMilestone(
            product=product,
            productseries=series,
            name='0.1')
        milestone_0_2 = self.factory.makeMilestone(
            product=product,
            productseries=series,
            name='0.2')
        release_1 = self.factory.makeProductRelease(
            product=product,
            milestone=milestone_0_1)
        release_2 = self.factory.makeProductRelease(
            product=product,
            milestone=milestone_0_2)
        release_file1 = self.factory.makeProductReleaseFile(
            product=product,
            release=release_1,
            productseries=series,
            milestone=milestone_0_1)
        release_file2 = self.factory.makeProductReleaseFile(
            product=product,
            release=release_2,
            productseries=series,
            milestone=milestone_0_2)
        expected = [(milestone_0_2, release_2), (milestone_0_1, release_1)]
        self.assertEqual(
            expected,
            list(product.getMilestonesAndReleases()))

    def test_getTimeline_limit(self):
        # Only 20 milestones/releases per series should be included in the
        # getTimeline() results. The results are sorted by
        # descending dateexpected and name, so the presumed latest
        # milestones should be included.
        product = self.factory.makeProduct(name='foo')
        for i in range(25):
            milestone_list = self.factory.makeMilestone(
                product=product,
                productseries=product.development_focus,
                name=str(i))

        # 0 through 4 should not be in the list.
        expected_milestones = [
            '/foo/+milestone/24',
            '/foo/+milestone/23',
            '/foo/+milestone/22',
            '/foo/+milestone/21',
            '/foo/+milestone/20',
            '/foo/+milestone/19',
            '/foo/+milestone/18',
            '/foo/+milestone/17',
            '/foo/+milestone/16',
            '/foo/+milestone/15',
            '/foo/+milestone/14',
            '/foo/+milestone/13',
            '/foo/+milestone/12',
            '/foo/+milestone/11',
            '/foo/+milestone/10',
            '/foo/+milestone/9',
            '/foo/+milestone/8',
            '/foo/+milestone/7',
            '/foo/+milestone/6',
            '/foo/+milestone/5',
            ]

        [series] = product.getTimeline()
        timeline_milestones = [
            landmark['uri']
            for landmark in series['landmarks']]
        self.assertEqual(
            expected_milestones,
            timeline_milestones)


class TestProductFiles(unittest.TestCase):
    """Tests for downloadable product files."""

    layer = LaunchpadFunctionalLayer

    def test_adddownloadfile_nonascii_filename(self):
        """Test uploading a file with a non-ascii char in the filename."""
        # XXX EdwinGrubbs 2008-03-06 bug=69988
        # Doctests are difficult to use with non-ascii characters, so
        # I have used a unittest.
        firefox_owner = setupBrowser(auth='Basic mark@example.com:test')
        filename = u'foo\xa5.txt'.encode('utf-8')
        firefox_owner.open(
            'http://launchpad.dev/firefox/1.0/1.0.0/+adddownloadfile')
        foo_file = StringIO('Foo installer package...')
        foo_signature = StringIO('Dummy GPG signature for the Foo installer')
        firefox_owner.getControl(name='field.filecontent').add_file(
            foo_file, 'text/plain', filename)
        firefox_owner.getControl(name='field.signature').add_file(
            foo_signature, 'text/plain', '%s.asc' % filename)
        firefox_owner.getControl('Description').value="Foo installer"
        firefox_owner.getControl(name="field.contenttype").displayValue = \
           ["Installer file"]
        firefox_owner.getControl("Upload").click()
        self.assertEqual(
            get_feedback_messages(firefox_owner.contents),
            [u"Your file 'foo\xa5.txt' has been uploaded."])
        firefox_owner.open('http://launchpad.dev/firefox/+download')
        content = find_main_content(firefox_owner.contents)
        rows = content.findAll('tr')

        a_list = rows[-1].findAll('a')
        # 1st row
        a_element = a_list[0]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/foo%C2%A5.txt')
        self.assertEqual(a_element.contents[0].strip(), u'foo\xa5.txt')
        # 2nd row
        a_element = a_list[1]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/'
            'foo%C2%A5.txt/+md5')
        self.assertEqual(a_element.contents[0].strip(), u'md5')
        # 3rd row
        a_element = a_list[2]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/'
            'foo%C2%A5.txt.asc')
        self.assertEqual(a_element.contents[0].strip(), u'sig')


class ProductAttributeCacheTestCase(unittest.TestCase):
    """Cached attributes must be cleared at the end of a transaction."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.product = Product.selectOneBy(name='tomcat')

    def testLicensesCache(self):
        """License cache should be cleared automatically."""
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        product_license = ProductLicense(
            product=self.product, license=License.PYTHON)
        syncUpdate(product_license)
        # Cache doesn't see new value.
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        self.product.licenses = (License.PERL, License.PHP)
        self.assertEqual(self.product.licenses,
                         (License.PERL, License.PHP))
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        transaction.abort()
        product_license = ProductLicense(
            product=self.product, license=License.MIT)
        syncUpdate(product_license)
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO, License.MIT))

    def testCommercialSubscriptionCache(self):
        """commercial_subscription cache should not traverse transactions."""
        self.assertEqual(self.product.commercial_subscription, None)
        now = datetime.datetime.now(pytz.UTC)
        subscription = CommercialSubscription(
            product=self.product,
            date_starts=now,
            date_expires=now,
            registrant=self.product.owner,
            purchaser=self.product.owner,
            sales_system_id='foo',
            whiteboard='bar')
        # Cache does not see the change to the database.
        syncUpdate(subscription)
        self.assertEqual(self.product.commercial_subscription, None)
        self.product.redeemSubscriptionVoucher(
            'hello', self.product.owner, self.product.owner, 1)
        self.assertEqual(self.product.commercial_subscription.sales_system_id,
                         'hello')
        transaction.abort()
        # Cache is cleared.
        self.assertEqual(self.product.commercial_subscription, None)

        # Cache is cleared again.
        transaction.abort()
        subscription = CommercialSubscription(
            product=self.product,
            date_starts=now,
            date_expires=now,
            registrant=self.product.owner,
            purchaser=self.product.owner,
            sales_system_id='new',
            whiteboard='')
        syncUpdate(subscription)
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        self.assertEqual(self.product.commercial_subscription.sales_system_id,
                         'new')


class ProductSnapshotTestCase(TestCaseWithFactory):
    """A TestCase for product snapshots."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(ProductSnapshotTestCase, self).setUp()
        self.product = self.factory.makeProduct(name="shamwow")

    def test_snapshot(self):
        """Snapshots of products should not include marked attribues.

        Wrap an export with 'doNotSnapshot' to force the snapshot to not
        include that attribute.
        """
        snapshot = Snapshot(self.product, providing=IProduct)
        omitted = [
            'series',
            'releases',
            ]
        for attribute in omitted:
            self.assertFalse(
                hasattr(snapshot, attribute),
                "Snapshot should not include %s." % attribute)


class BugSupervisorTestCase(TestCaseWithFactory):
    """A TestCase for bug supervisor management."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BugSupervisorTestCase, self).setUp()
        self.person = self.factory.makePerson()
        self.product = self.factory.makeProduct(owner=self.person)
        login(self.person.preferredemail.email)

    def testPersonCanSetSelfAsSupervisor(self):
        # A person can set themselves as bug supervisor for a product.
        # This is a regression test for bug 438985.
        user = getUtility(IPersonSet).getByName(self.person.name)
        self.product.setBugSupervisor(
            bug_supervisor=self.person, user=user)

        self.assertEqual(
            self.product.bug_supervisor, self.person,
            "%s should be bug supervisor for %s. "
            "Instead, bug supervisor for firefox is %s" % (
            self.person.name, self.product.name,
            self.product.bug_supervisor.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
