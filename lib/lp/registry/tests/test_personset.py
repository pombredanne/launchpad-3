# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type


from testtools.matchers import (
    GreaterThan,
    LessThan,
    )
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.code.tests.helpers import remove_all_sample_data_branches
from lp.registry.errors import (
    InvalidName,
    NameAlreadyTaken,
    NoSuchAccount,
    NotPlaceholderAccount,
    )
from lp.registry.interfaces.nameblacklist import INameBlacklistSet
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    PersonCreationRationale,
    TeamEmailAddressError,
    )
from lp.registry.interfaces.ssh import (
    SSHKeyAdditionError,
    SSHKeyType,
    )
from lp.registry.model.codeofconduct import SignedCodeOfConduct
from lp.registry.model.person import Person
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.sqlbase import (
    cursor,
    flush_database_caches,
    )
from lp.services.identity.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    AccountSuspendedError,
    IAccountSet,
    )
from lp.services.identity.interfaces.emailaddress import (
    EmailAddressAlreadyTaken,
    EmailAddressStatus,
    IEmailAddressSet,
    InvalidEmailAddress,
    )
from lp.services.identity.model.account import Account
from lp.services.identity.model.emailaddress import EmailAddress
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.webapp.interfaces import ILaunchBag
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    anonymous_logged_in,
    login,
    logout,
    person_logged_in,
    StormStatementRecorder,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


def make_openid_identifier(account, identifier):
    openid_identifier = OpenIdIdentifier()
    openid_identifier.identifier = identifier
    openid_identifier.account = account
    return IStore(OpenIdIdentifier).add(openid_identifier)


class TestPersonSet(TestCaseWithFactory):
    """Test `IPersonSet`."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSet, self).setUp()
        login(ANONYMOUS)
        self.addCleanup(logout)
        self.person_set = getUtility(IPersonSet)

    def test_isNameBlacklisted(self):
        cursor().execute(
            "INSERT INTO NameBlacklist(id, regexp) VALUES (-100, 'foo')")
        self.failUnless(self.person_set.isNameBlacklisted('foo'))
        self.failIf(self.person_set.isNameBlacklisted('bar'))

    def test_isNameBlacklisted_user_is_admin(self):
        team = self.factory.makeTeam()
        name_blacklist_set = getUtility(INameBlacklistSet)
        self.admin_exp = name_blacklist_set.create(u'fnord', admin=team)
        self.store = IStore(self.admin_exp)
        self.store.flush()
        user = team.teamowner
        self.assertFalse(self.person_set.isNameBlacklisted('fnord', user))

    def test_getByEmail_ignores_case_and_whitespace(self):
        person1_email = 'foo.bar@canonical.com'
        person1 = self.person_set.getByEmail(person1_email)
        self.failIf(
            person1 is None,
            "PersonSet.getByEmail() could not find %r" % person1_email)

        person2 = self.person_set.getByEmail('  foo.BAR@canonICAL.com  ')
        self.failIf(
            person2 is None,
            "PersonSet.getByEmail() should ignore case and whitespace.")
        self.assertEqual(person1, person2)

    def test_getByEmail_ignores_unvalidated_emails(self):
        person = self.factory.makePerson()
        self.factory.makeEmail(
            'fnord@example.com',
            person,
            email_status=EmailAddressStatus.NEW)
        found = self.person_set.getByEmail('fnord@example.com')
        self.assertTrue(found is None)

    def test_getPrecachedPersonsFromIDs(self):
        # The getPrecachedPersonsFromIDs() method should only make one
        # query to load all the extraneous data. Accessing the
        # attributes should then cause zero queries.
        person_ids = [self.factory.makePerson().id for i in range(3)]
        person_ids += [self.factory.makeTeam().id for i in range(3)]
        transaction.commit()

        with StormStatementRecorder() as recorder:
            persons = list(self.person_set.getPrecachedPersonsFromIDs(
                person_ids, need_karma=True, need_ubuntu_coc=True,
                need_teamowner=True, need_location=True, need_archive=True,
                need_preferred_email=True, need_validity=True))
        self.assertThat(recorder, HasQueryCount(LessThan(3)))

        with StormStatementRecorder() as recorder:
            for person in persons:
                person.is_valid_person
                person.karma
                person.is_ubuntu_coc_signer
                person.location,
                person.archive
                person.preferredemail
                person.teamowner
        self.assertThat(recorder, HasQueryCount(LessThan(1)))

    def test_getPrecachedPersonsFromIDs_is_ubuntu_coc_signer(self):
        # getPrecachedPersonsFromIDs() sets is_ubuntu_coc_signer
        # correctly.
        person_ids = [self.factory.makePerson().id for i in range(3)]
        SignedCodeOfConduct(owner=person_ids[0], active=True)
        flush_database_caches()

        persons = list(
            self.person_set.getPrecachedPersonsFromIDs(
                person_ids, need_ubuntu_coc=True))
        self.assertContentEqual(
            zip(person_ids, [True, False, False]),
            [(p.id, p.is_ubuntu_coc_signer) for p in persons])

    def test_getByOpenIDIdentifier_returns_person(self):
        # getByOpenIDIdentifier takes a full OpenID identifier and
        # returns the corresponding person.
        person = self.factory.makePerson()
        with person_logged_in(person):
            identifier = person.account.openid_identifiers.one().identifier
        for id_url in (
                u'http://testopenid.dev/+id/%s' % identifier,
                u'http://login1.dev/+id/%s' % identifier,
                u'http://login2.dev/+id/%s' % identifier):
            self.assertEqual(
                person, self.person_set.getByOpenIDIdentifier(id_url))

    def test_getByOpenIDIdentifier_for_nonexistent_identifier_is_none(self):
        # None is returned if there's no matching person.
        self.assertIs(
            None,
            self.person_set.getByOpenIDIdentifier(
                u'http://testopenid.dev/+id/notanid'))

    def test_getByOpenIDIdentifier_for_bad_domain_is_none(self):
        # Even though the OpenIDIdentifier table doesn't store the
        # domain, we verify it against our known OpenID faux-vhosts.
        # If it doesn't match, we don't even try to check the identifier.
        person = self.factory.makePerson()
        with person_logged_in(person):
            identifier = person.account.openid_identifiers.one().identifier
        self.assertIs(
            None,
            self.person_set.getByOpenIDIdentifier(
                u'http://not.launchpad.dev/+id/%s' % identifier))

    def test_find__accepts_queries_with_or_operator(self):
        # PersonSet.find() allows to search for OR combined terms.
        person_one = self.factory.makePerson(name='baz')
        person_two = self.factory.makeTeam(name='blah')
        result = list(self.person_set.find('baz OR blah'))
        self.assertEqual([person_one, person_two], result)

    def test_findPerson__accepts_queries_with_or_operator(self):
        # PersonSet.findPerson() allows to search for OR combined terms.
        person_one = self.factory.makePerson(
            name='baz', email='one@example.org')
        person_two = self.factory.makePerson(
            name='blah', email='two@example.com')
        result = list(self.person_set.findPerson('baz OR blah'))
        self.assertEqual([person_one, person_two], result)
        # Note that these OR searches do not work for email addresses.
        result = list(self.person_set.findPerson(
            'one@example.org OR two@example.org'))
        self.assertEqual([], result)

    def test_findPerson__case_insensitive_email_address_search(self):
        # A search for email addresses is case insensitve.
        person_one = self.factory.makePerson(
            name='baz', email='ONE@example.org')
        person_two = self.factory.makePerson(
            name='blah', email='two@example.com')
        result = list(self.person_set.findPerson('one@example.org'))
        self.assertEqual([person_one], result)
        result = list(self.person_set.findPerson('TWO@example.com'))
        self.assertEqual([person_two], result)

    def test_findTeam__accepts_queries_with_or_operator(self):
        # PersonSet.findTeam() allows to search for OR combined terms.
        team_one = self.factory.makeTeam(name='baz', email='ONE@example.org')
        team_two = self.factory.makeTeam(name='blah', email='TWO@example.com')
        result = list(self.person_set.findTeam('baz OR blah'))
        self.assertEqual([team_one, team_two], result)
        # Note that these OR searches do not work for email addresses.
        result = list(self.person_set.findTeam(
            'one@example.org OR two@example.org'))
        self.assertEqual([], result)

    def test_findTeam__case_insensitive_email_address_search(self):
        # A search for email addresses is case insensitve.
        team_one = self.factory.makeTeam(name='baz', email='ONE@example.org')
        team_two = self.factory.makeTeam(name='blah', email='TWO@example.com')
        result = list(self.person_set.findTeam('one@example.org'))
        self.assertEqual([team_one], result)
        result = list(self.person_set.findTeam('TWO@example.com'))
        self.assertEqual([team_two], result)


class TestPersonSetCreateByOpenId(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetCreateByOpenId, self).setUp()
        self.person_set = getUtility(IPersonSet)
        self.store = IMasterStore(Account)

        # Generate some valid test data.
        self.account = self.makeAccount()
        self.identifier = make_openid_identifier(self.account, u'whatever')
        self.person = self.makePerson(self.account)
        self.email = self.makeEmailAddress(
            email='whatever@example.com', person=self.person)

    def makeAccount(self):
        return self.store.add(Account(
            displayname='Displayname',
            creation_rationale=AccountCreationRationale.UNKNOWN,
            status=AccountStatus.ACTIVE))

    def makePerson(self, account):
        return self.store.add(Person(
            name='acc%d' % account.id, account=account,
            display_name='Displayname',
            creation_rationale=PersonCreationRationale.UNKNOWN))

    def makeEmailAddress(self, email, person):
            return self.store.add(EmailAddress(
                email=email,
                account=person.account,
                person=person,
                status=EmailAddressStatus.PREFERRED))

    def testAllValid(self):
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, self.email.email, 'Ignored Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertIs(False, updated)
        self.assertIs(self.person, found)
        self.assertIs(self.account, found.account)
        self.assertIs(self.email, found.preferredemail)
        self.assertIs(self.email.account, self.account)
        self.assertIs(self.email.person, self.person)
        self.assertEqual(
            [self.identifier], list(self.account.openid_identifiers))

    def testEmailAddressCaseInsensitive(self):
        # As per testAllValid, but the email address used for the lookup
        # is all upper case.
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, self.email.email.upper(),
            'Ignored Name', PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertIs(False, updated)
        self.assertIs(self.person, found)
        self.assertIs(self.account, found.account)
        self.assertIs(self.email, found.preferredemail)
        self.assertIs(self.email.account, self.account)
        self.assertIs(self.email.person, self.person)
        self.assertEqual(
            [self.identifier], list(self.account.openid_identifiers))

    def testNewOpenId(self):
        # Account looked up by email and the new OpenId identifier
        # attached. We can do this because we trust our OpenId Provider.
        new_identifier = u'newident'
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            new_identifier, self.email.email, 'Ignored Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertIs(True, updated)
        self.assertIs(self.person, found)
        self.assertIs(self.account, found.account)
        self.assertIs(self.email, found.preferredemail)
        self.assertIs(self.email.account, self.account)
        self.assertIs(self.email.person, self.person)

        # Old OpenId Identifier still attached.
        self.assertIn(self.identifier, list(self.account.openid_identifiers))

        # So is our new one.
        identifiers = [
            identifier.identifier for identifier
                in self.account.openid_identifiers]
        self.assertIn(new_identifier, identifiers)

    def testNewAccountAndIdentifier(self):
        # If neither the OpenId Identifier nor the email address are
        # found, we create everything.
        new_email = u'new_email@example.com'
        new_identifier = u'new_identifier'
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            new_identifier, new_email, 'New Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        # We have a new Person
        self.assertIs(True, updated)
        self.assertIsNot(None, found)

        # It is correctly linked to an account, emailaddress and
        # identifier.
        self.assertIs(found, found.preferredemail.person)
        self.assertEqual(
            new_identifier, found.account.openid_identifiers.any().identifier)

    def testNoAccount(self):
        # EmailAddress is linked to a Person, but there is no Account.
        # Convert this stub into something valid.
        self.email.account = None
        self.email.status = EmailAddressStatus.NEW
        self.person.account = None
        new_identifier = u'new_identifier'
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            new_identifier, self.email.email, 'Ignored',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertTrue(updated)

        self.assertIsNot(None, found.account)
        self.assertEqual(
            new_identifier, found.account.openid_identifiers.any().identifier)
        self.assertIs(self.email.person, found)
        self.assertEqual(EmailAddressStatus.PREFERRED, self.email.status)

    def testEmailAddressAccountAndOpenIDAccountAreDifferent(self):
        # The EmailAddress and OpenId Identifier are both in the database,
        # but they are not linked to the same account. In this case, the
        # OpenId Identifier trumps the EmailAddress's account.
        self.identifier.account = self.store.find(
            Account, displayname='Foo Bar').one()
        email_account = self.email.account

        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, self.email.email, 'New Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertFalse(updated)
        self.assertIs(IPerson(self.identifier.account), found)

        self.assertIs(found.account, self.identifier.account)
        self.assertIn(self.identifier, list(found.account.openid_identifiers))
        self.assertIs(email_account, self.email.account)

    def testEmptyOpenIDIdentifier(self):
        self.assertRaises(
            AssertionError,
            self.person_set.getOrCreateByOpenIDIdentifier, u'', 'foo@bar.com',
            'New Name', PersonCreationRationale.UNKNOWN, 'No Comment')

    def testTeamEmailAddress(self):
        # If the EmailAddress is linked to a team, login fails. There is
        # no way to automatically recover -- someone must manually fix
        # the email address of the team or the SSO account.
        self.factory.makeTeam(email="foo@bar.com")

        self.assertRaises(
            TeamEmailAddressError,
            self.person_set.getOrCreateByOpenIDIdentifier,
            u'other-openid-identifier', 'foo@bar.com', 'New Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')

    def testDeactivatedAccount(self):
        # Logging into a deactivated account with a new email address
        # reactivates the account, adds that email address, and sets it
        # as preferred.
        addr = 'not@an.address'
        self.person.preDeactivate('I hate life.')
        self.assertEqual(AccountStatus.DEACTIVATED, self.person.account_status)
        self.assertIs(None, self.person.preferredemail)
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, addr, 'New Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        self.assertEqual(AccountStatus.ACTIVE, self.person.account_status)
        self.assertEqual(addr, self.person.preferredemail.email)

    def testPlaceholderAccount(self):
        # Logging into a username placeholder account activates the
        # account and adds the email address.
        email = u'placeholder@example.com'
        openid = u'placeholder-id'
        name = u'placeholder'
        person = self.person_set.createPlaceholderPerson(openid, name)
        self.assertEqual(AccountStatus.PLACEHOLDER, person.account.status)
        original_created = person.datecreated
        transaction.commit()
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            openid, email, 'New Name', PersonCreationRationale.UNKNOWN,
            'No Comment')
        self.assertEqual(person, found)
        self.assertEqual(AccountStatus.ACTIVE, person.account.status)
        self.assertEqual(name, person.name)
        self.assertEqual('New Name', person.display_name)
        self.assertThat(person.datecreated, GreaterThan(original_created))


class TestCreatePersonAndEmail(TestCase):
    """Test `IPersonSet`.createPersonAndEmail()."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        self.addCleanup(logout)
        self.person_set = getUtility(IPersonSet)

    def test_duplicated_name_not_accepted(self):
        self.person_set.createPersonAndEmail(
            'testing@example.com', PersonCreationRationale.UNKNOWN,
            name='zzzz')
        self.assertRaises(
            NameAlreadyTaken, self.person_set.createPersonAndEmail,
            'testing2@example.com', PersonCreationRationale.UNKNOWN,
            name='zzzz')

    def test_duplicated_email_not_accepted(self):
        self.person_set.createPersonAndEmail(
            'testing@example.com', PersonCreationRationale.UNKNOWN)
        self.assertRaises(
            EmailAddressAlreadyTaken, self.person_set.createPersonAndEmail,
            'testing@example.com', PersonCreationRationale.UNKNOWN)

    def test_invalid_email_not_accepted(self):
        self.assertRaises(
            InvalidEmailAddress, self.person_set.createPersonAndEmail,
            'testing@.com', PersonCreationRationale.UNKNOWN)

    def test_invalid_name_not_accepted(self):
        self.assertRaises(
            InvalidName, self.person_set.createPersonAndEmail,
            'testing@example.com', PersonCreationRationale.UNKNOWN,
            name='/john')


class TestPersonSetBranchCounts(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.person_set = getUtility(IPersonSet)

    def test_no_branches(self):
        """Initially there should be no branches."""
        self.assertEqual(0, self.person_set.getPeopleWithBranches().count())

    def test_five_branches(self):
        branches = [self.factory.makeAnyBranch() for x in range(5)]
        # Each branch has a different product, so any individual product
        # will return one branch.
        self.assertEqual(5, self.person_set.getPeopleWithBranches().count())
        self.assertEqual(1, self.person_set.getPeopleWithBranches(
                branches[0].product).count())


class TestPersonSetEnsurePerson(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
    email_address = 'testing.ensure.person@example.com'
    displayname = 'Testing ensurePerson'
    rationale = PersonCreationRationale.SOURCEPACKAGEUPLOAD

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person_set = getUtility(IPersonSet)

    def test_ensurePerson_returns_existing_person(self):
        # IPerson.ensurePerson returns existing person and does not
        # override its details.
        testing_displayname = 'will not be modified'
        testing_person = self.factory.makePerson(
            email=self.email_address, displayname=testing_displayname)

        ensured_person = self.person_set.ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertEquals(testing_person.id, ensured_person.id)
        self.assertIsNot(
            ensured_person.displayname, self.displayname,
            'Person.displayname should not be overridden.')
        self.assertIsNot(
            ensured_person.creation_rationale, self.rationale,
            'Person.creation_rationale should not be overridden.')

    def test_ensurePerson_hides_new_person_email(self):
        # IPersonSet.ensurePerson creates new person with
        # 'hide_email_addresses' set.
        ensured_person = self.person_set.ensurePerson(
            self.email_address, self.displayname, self.rationale)
        self.assertTrue(ensured_person.hide_email_addresses)


class TestPersonSetGetOrCreateByOpenIDIdentifier(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetGetOrCreateByOpenIDIdentifier, self).setUp()
        self.person_set = getUtility(IPersonSet)

    def callGetOrCreate(self, identifier, email='a@b.com'):
        return self.person_set.getOrCreateByOpenIDIdentifier(
            identifier, email, "Joe Bloggs",
            PersonCreationRationale.SOFTWARE_CENTER_PURCHASE,
            "when purchasing an application via Software Center.")

    def test_existing_person(self):
        email = 'test-email@example.com'
        person = self.factory.makePerson(email=email)
        openid_ident = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier

        result, db_updated = self.callGetOrCreate(openid_ident, email=email)

        self.assertEqual(person, result)
        self.assertFalse(db_updated)

    def test_existing_deactivated_account(self):
        # An existing deactivated account will be reactivated.
        person = self.factory.makePerson(
            account_status=AccountStatus.DEACTIVATED)
        openid_ident = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier

        found_person, db_updated = self.callGetOrCreate(openid_ident)
        self.assertEqual(person, found_person)
        self.assertEqual(AccountStatus.ACTIVE, person.account.status)
        self.assertTrue(db_updated)
        self.assertEndsWith(
            removeSecurityProxy(person.account).status_history,
            ": Deactivated -> Active: "
            "when purchasing an application via Software Center.\n")

    def test_existing_suspended_account(self):
        # An existing suspended account will raise an exception.
        person = self.factory.makePerson(
            account_status=AccountStatus.SUSPENDED)
        openid_ident = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier

        self.assertRaises(
            AccountSuspendedError, self.callGetOrCreate, openid_ident)

    def test_no_account_or_email(self):
        # An identifier can be used to create an account (it is assumed
        # to be already authenticated with SSO).
        person, db_updated = self.callGetOrCreate(u'openid-identifier')

        self.assertEqual(
            u"openid-identifier", removeSecurityProxy(
                person.account).openid_identifiers.any().identifier)
        self.assertTrue(db_updated)

    def test_no_matching_account_existing_email(self):
        # The openid_identity of the account matching the email will
        # updated.
        other_person = self.factory.makePerson('a@b.com')

        person, db_updated = self.callGetOrCreate(
            u'other-openid-identifier', 'a@b.com')

        self.assertEqual(other_person, person)
        self.assert_(
            u'other-openid-identifier' in [
                identifier.identifier for identifier in removeSecurityProxy(
                    person.account).openid_identifiers])


class TestPersonSetGetOrCreateSoftwareCenterCustomer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetGetOrCreateSoftwareCenterCustomer, self).setUp()
        self.sca = getUtility(IPersonSet).getByName('software-center-agent')

    def test_restricted_to_sca(self):
        # Only the software-center-agent celebrity can invoke this
        # privileged method.
        def do_it():
            return getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer(
                getUtility(ILaunchBag).user, u'somebody',
                'somebody@example.com', 'Example')
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName('admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)

        with person_logged_in(self.sca):
            person = do_it()
        self.assertIsInstance(person, Person)

    def test_finds_by_openid(self):
        # A Person with the requested OpenID identifier is returned.
        somebody = self.factory.makePerson()
        make_openid_identifier(somebody.account, u'somebody')
        with person_logged_in(self.sca):
            got = getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer(
                self.sca, u'somebody', 'somebody@example.com', 'Example')
        self.assertEqual(somebody, got)

        # The email address doesn't get linked, as that could change how
        # future logins work.
        self.assertIs(
            None,
            getUtility(IEmailAddressSet).getByEmail('somebody@example.com'))

    def test_creates_new(self):
        # If an unknown OpenID identifier and email address are
        # provided, a new account is created and returned.
        with person_logged_in(self.sca):
            made = getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer(
                self.sca, u'somebody', 'somebody@example.com', 'Example')
        with admin_logged_in():
            self.assertEqual('Example', made.displayname)
            self.assertEqual('somebody@example.com', made.preferredemail.email)

        # The email address is linked, since it can't compromise an
        # account that is being created just for it.
        email = getUtility(IEmailAddressSet).getByEmail('somebody@example.com')
        self.assertEqual(made, email.person)

    def test_activates_unactivated(self):
        # An unactivated account should be treated just like a new
        # account -- it gets activated with the given email address.
        somebody = self.factory.makePerson(
            email='existing@example.com',
            account_status=AccountStatus.NOACCOUNT)
        make_openid_identifier(somebody.account, u'somebody')
        self.assertEqual(AccountStatus.NOACCOUNT, somebody.account.status)
        with person_logged_in(self.sca):
            got = getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer(
                self.sca, u'somebody', 'somebody@example.com', 'Example')
        self.assertEqual(somebody, got)
        with admin_logged_in():
            self.assertEqual(AccountStatus.ACTIVE, somebody.account.status)
            self.assertEqual(
                'somebody@example.com', somebody.preferredemail.email)

    def test_fails_if_email_is_already_registered(self):
        # Only the OpenID identifier is used to look up an account. If
        # the OpenID identifier isn't already registered by the email
        # address is, the request is rejected to avoid potentially
        # adding an unwanted OpenID identifier to the address' account.
        #
        # The user must log into Launchpad directly first to register
        # their OpenID identifier.
        other = self.factory.makePerson(email='other@example.com')
        with person_logged_in(self.sca):
            self.assertRaises(
                EmailAddressAlreadyTaken,
                getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer,
                self.sca, u'somebody', 'other@example.com', 'Example')

        # The email address stays with the old owner.
        email = getUtility(IEmailAddressSet).getByEmail('other@example.com')
        self.assertEqual(other, email.person)

    def test_fails_if_account_is_suspended(self):
        # Suspended accounts cannot be returned.
        somebody = self.factory.makePerson()
        make_openid_identifier(somebody.account, u'somebody')
        with admin_logged_in():
            somebody.setAccountStatus(
                AccountStatus.SUSPENDED, None, "Go away!")
        with person_logged_in(self.sca):
            self.assertRaises(
                AccountSuspendedError,
                getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer,
                self.sca, u'somebody', 'somebody@example.com', 'Example')

    def test_fails_if_account_is_deactivated(self):
        # We don't want to reactivate explicitly deactivated accounts,
        # nor do we want to potentially compromise them with a bad email
        # address.
        somebody = self.factory.makePerson()
        make_openid_identifier(somebody.account, u'somebody')
        with admin_logged_in():
            somebody.setAccountStatus(
                AccountStatus.DEACTIVATED, None, "Goodbye cruel world.")
        with person_logged_in(self.sca):
            self.assertRaises(
                NameAlreadyTaken,
                getUtility(IPersonSet).getOrCreateSoftwareCenterCustomer,
                self.sca, u'somebody', 'somebody@example.com', 'Example')


class TestPersonGetUsernameForSSO(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonGetUsernameForSSO, self).setUp()
        self.sso = getUtility(IPersonSet).getByName(u'ubuntu-sso')

    def test_restricted_to_sca(self):
        # Only the ubuntu-sso celebrity can invoke this
        # privileged method.
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')

        def do_it():
            return getUtility(IPersonSet).getUsernameForSSO(
                getUtility(ILaunchBag).user, u'openid')
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName(u'admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)

        with person_logged_in(self.sso):
            self.assertEqual('username', do_it())


class TestPersonSetUsernameFromSSO(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetUsernameFromSSO, self).setUp()
        self.sso = getUtility(IPersonSet).getByName(u'ubuntu-sso')

    def test_restricted_to_sca(self):
        # Only the ubuntu-sso celebrity can invoke this
        # privileged method.
        def do_it():
            getUtility(IPersonSet).setUsernameFromSSO(
                getUtility(ILaunchBag).user, u'openid', u'username')
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName(u'admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)

        with person_logged_in(self.sso):
            do_it()

    def test_creates_new_placeholder(self):
        # If an unknown OpenID identifier and email address are
        # provided, a new account is created with the given username and
        # returned.
        with person_logged_in(self.sso):
            getUtility(IPersonSet).setUsernameFromSSO(
                self.sso, u'openid', u'username')
        person = getUtility(IPersonSet).getByName(u'username')
        self.assertEqual(u'username', person.name)
        self.assertEqual(u'username', person.displayname)
        self.assertEqual(AccountStatus.PLACEHOLDER, person.account.status)
        with admin_logged_in():
            self.assertContentEqual(
                [u'openid'],
                [oid.identifier for oid in person.account.openid_identifiers])
            self.assertContentEqual([], person.validatedemails)
            self.assertContentEqual([], person.guessedemails)

    def test_creates_new_placeholder_dry_run(self):
        with person_logged_in(self.sso):
            getUtility(IPersonSet).setUsernameFromSSO(
                self.sso, u'openid', u'username', dry_run=True)
        self.assertRaises(
            LookupError,
            getUtility(IAccountSet).getByOpenIDIdentifier, u'openid')
        self.assertIs(None, getUtility(IPersonSet).getByName(u'username'))

    def test_updates_existing_placeholder(self):
        # An existing placeholder Person with the request OpenID
        # identifier has its name updated.
        getUtility(IPersonSet).setUsernameFromSSO(
            self.sso, u'openid', u'username')
        person = getUtility(IPersonSet).getByName(u'username')

        # Another call for the same OpenID identifier updates the
        # existing Person.
        getUtility(IPersonSet).setUsernameFromSSO(
            self.sso, u'openid', u'newsername')
        self.assertEqual(u'newsername', person.name)
        self.assertEqual(u'newsername', person.displayname)
        self.assertEqual(AccountStatus.PLACEHOLDER, person.account.status)
        with admin_logged_in():
            self.assertContentEqual([], person.validatedemails)
            self.assertContentEqual([], person.guessedemails)

    def test_updates_existing_placeholder_dry_run(self):
        getUtility(IPersonSet).setUsernameFromSSO(
            self.sso, u'openid', u'username')
        person = getUtility(IPersonSet).getByName(u'username')

        getUtility(IPersonSet).setUsernameFromSSO(
            self.sso, u'openid', u'newsername', dry_run=True)
        self.assertEqual(u'username', person.name)

    def test_validation(self, dry_run=False):
        # An invalid username is rejected with an InvalidName exception.
        self.assertRaises(
            InvalidName,
            getUtility(IPersonSet).setUsernameFromSSO,
            self.sso, u'openid', u'username!!', dry_run=dry_run)
        transaction.abort()

        # A username that's already in use is rejected with a
        # NameAlreadyTaken exception.
        self.factory.makePerson(name='taken')
        self.assertRaises(
            NameAlreadyTaken,
            getUtility(IPersonSet).setUsernameFromSSO,
            self.sso, u'openid', u'taken', dry_run=dry_run)
        transaction.abort()

        # setUsernameFromSSO can't be used to set an OpenID
        # identifier's username if a non-placeholder account exists.
        somebody = self.factory.makePerson()
        make_openid_identifier(somebody.account, u'openid-taken')
        self.assertRaises(
            NotPlaceholderAccount,
            getUtility(IPersonSet).setUsernameFromSSO,
            self.sso, u'openid-taken', u'username', dry_run=dry_run)

    def test_validation_dry_run(self):
        self.test_validation(dry_run=True)


class TestPersonGetSSHKeysForSSO(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonGetSSHKeysForSSO, self).setUp()
        self.sso = getUtility(IPersonSet).getByName(u'ubuntu-sso')

    def test_restricted_to_sso(self):
        # Only the ubuntu-sso celebrity can invoke this
        # privileged method.
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')

        def do_it():
            return getUtility(IPersonSet).getUsernameForSSO(
                getUtility(ILaunchBag).user, u'openid')
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName(u'admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(self.sso):
            self.assertEqual('username', do_it())


class TestPersonAddSSHKeyFromSSO(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonAddSSHKeyFromSSO, self).setUp()
        self.sso = getUtility(IPersonSet).getByName(u'ubuntu-sso')

    def test_restricted_to_sso(self):
        # Only the ubuntu-sso celebrity can invoke this
        # privileged method.
        key_text = 'ssh-rsa keytext keycomment'
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')

        def do_it():
            return getUtility(IPersonSet).addSSHKeyForPersonFromSSO(
                getUtility(ILaunchBag).user, u'openid', key_text, False)
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName(u'admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(self.sso):
            self.assertEqual(None, do_it())

    def test_adds_new_ssh_key(self):
        key_text = 'ssh-rsa keytext keycomment'
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')

        with person_logged_in(self.sso):
            getUtility(IPersonSet).addSSHKeyForPersonFromSSO(
                self.sso, u'openid', key_text, False)

        with person_logged_in(target):
            [key] = target.sshkeys
            self.assertEqual(key.keytype, SSHKeyType.RSA)
            self.assertEqual(key.keytext, 'keytext')
            self.assertEqual(key.comment, 'keycomment')

    def test_does_not_add_new_ssh_key_with_dry_run(self):
        key_text = 'ssh-rsa keytext keycomment'
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')

        with person_logged_in(self.sso):
            getUtility(IPersonSet).addSSHKeyForPersonFromSSO(
                self.sso, u'openid', key_text, True)

        with person_logged_in(target):
            self.assertEqual(0, target.sshkeys.count())

    def test_raises_with_nonexisting_account(self):
        with person_logged_in(self.sso):
            self.assertRaises(
                NoSuchAccount,
                getUtility(IPersonSet).addSSHKeyForPersonFromSSO,
                self.sso, u'doesnotexist', 'ssh-rsa key comment', True)


class TestPersonDeleteSSHKeyFromSSO(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonDeleteSSHKeyFromSSO, self).setUp()
        self.sso = getUtility(IPersonSet).getByName(u'ubuntu-sso')

    def test_restricted_to_sso(self):
        # Only the ubuntu-sso celebrity can invoke this
        # privileged method.
        target = self.factory.makePerson(name='username')
        with person_logged_in(target):
            key = self.factory.makeSSHKey(target)
        key_text = key.getFullKeyText()
        make_openid_identifier(target.account, u'openid')

        def do_it():
            return getUtility(IPersonSet).deleteSSHKeyFromSSO(
                getUtility(ILaunchBag).user, u'openid', key_text, False)
        random = self.factory.makePerson()
        admin = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName(u'admins')])

        # Anonymous, random or admin users can't invoke the method.
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(random):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(admin):
            self.assertRaises(Unauthorized, do_it)
        with person_logged_in(self.sso):
            self.assertEqual(None, do_it())

    def test_deletes_ssh_key(self):
        target = self.factory.makePerson(name='username')
        with person_logged_in(target):
            key = self.factory.makeSSHKey(target)
        make_openid_identifier(target.account, u'openid')

        with person_logged_in(self.sso):
            getUtility(IPersonSet).deleteSSHKeyFromSSO(
                self.sso, u'openid', key.getFullKeyText(), False)

        with person_logged_in(target):
            self.assertEqual(0, target.sshkeys.count())

    def test_does_not_delete_ssh_key_with_dry_run(self):
        target = self.factory.makePerson(name='username')
        with person_logged_in(target):
            key = self.factory.makeSSHKey(target)
        make_openid_identifier(target.account, u'openid')

        with person_logged_in(self.sso):
            getUtility(IPersonSet).deleteSSHKeyFromSSO(
                self.sso, u'openid', key.getFullKeyText(), True)

        with person_logged_in(target):
            self.assertEqual([key], list(target.sshkeys))

    def test_raises_with_nonexisting_account(self):
        with person_logged_in(self.sso):
            self.assertRaises(
                NoSuchAccount,
                getUtility(IPersonSet).deleteSSHKeyFromSSO,
                self.sso, u'doesnotexist', 'ssh-rsa key comment', False)

    def test_raises_with_bad_key_type(self):
        target = self.factory.makePerson(name='username')
        make_openid_identifier(target.account, u'openid')
        with person_logged_in(self.sso):
            self.assertRaises(
                SSHKeyAdditionError,
                getUtility(IPersonSet).deleteSSHKeyFromSSO,
                self.sso, u'openid', 'badtype key comment', False)
