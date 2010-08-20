# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest
import datetime
import pytz
import transaction
from cStringIO import StringIO

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.pages import (
    find_main_content, get_feedback_messages, setupBrowser)
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )

from canonical.launchpad.ftests import syncUpdate

from lazr.lifecycle.snapshot import Snapshot
from lp.app.enums import ServiceUsage
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct, License
from lp.registry.model.product import Product
from lp.registry.model.productlicense import ProductLicense
from lp.registry.model.commercialsubscription import (
    CommercialSubscription)
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class TestProductUsageEnums(TestCaseWithFactory):
    """Tests the usage enums for the product."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductUsageEnums, self).setUp()
        self.product = self.factory.makeProduct()

    def test_answers_usage_no_data(self):
        # By default, we don't know anything about a product
        self.assertEqual(ServiceUsage.UNKNOWN, self.product.answers_usage)

    def test_answers_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.product.owner)
        self.product.official_answers = True
        self.assertEqual(ServiceUsage.LAUNCHPAD, self.product.answers_usage)

    def test_answers_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.product.owner)
        self.product.answers_usage = ServiceUsage.EXTERNAL
        self.assertEqual(ServiceUsage.EXTERNAL, self.product.answers_usage)

    def test_answers_setter(self):
        login_person(self.product.owner)
        self.product.official_answers = True
        self.product.answers_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.product.official_answers)
        self.product.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.product.official_answers)

    def test_codehosting_usage(self):
        # Only test get for codehosting; this has no setter because the
        # state is derived from other data.
        product = self.factory.makeProduct()
        self.assertEqual(ServiceUsage.UNKNOWN, product.codehosting_usage)

    def test_translations_usage_no_data(self):
        # By default, we don't know anything about a product
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.product.translations_usage)

    def test_translations_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.product.owner)
        self.product.official_rosetta = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.product.translations_usage)

    def test_translations_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.product.owner)
        self.product.translations_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            ServiceUsage.EXTERNAL,
            self.product.translations_usage)

    def test_translations_setter(self):
        login_person(self.product.owner)
        self.product.official_rosetta = True
        self.product.translations_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.product.official_rosetta)
        self.product.translations_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.product.official_rosetta)

    def test_bug_tracking_usage(self):
        # Only test get for bug_tracking; this has no setter because the
        # state is derived from other data.
        product = self.factory.makeProduct()
        self.assertEqual(ServiceUsage.UNKNOWN, product.bug_tracking_usage)

    def test_blueprints_usage_no_data(self):
        # By default, we don't know anything about a product
        self.assertEqual(ServiceUsage.UNKNOWN, self.product.blueprints_usage)

    def test_blueprints_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.product.owner)
        self.product.official_blueprints = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.product.blueprints_usage)

    def test_blueprints_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.product.owner)
        self.product.blueprints_usage = ServiceUsage.EXTERNAL
        self.assertEqual(ServiceUsage.EXTERNAL, self.product.blueprints_usage)

    def test_blueprints_setter(self):
        login_person(self.product.owner)
        self.product.official_blueprints = True
        self.product.blueprints_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.product.official_blueprints)
        self.product.blueprints_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.product.official_blueprints)


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
