# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type

from datetime import datetime

import pytz
from testtools.matchers import (
    LessThan,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.tests.helpers import remove_all_sample_data_branches
from lp.registry.errors import (
    InvalidName,
    NameAlreadyTaken,
    )
from lp.registry.interfaces.accesspolicy import IAccessPolicyGrantSource
from lp.registry.interfaces.karma import IKarmaCacheManager
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy,
    )
from lp.registry.interfaces.nameblacklist import INameBlacklistSet
from lp.registry.interfaces.person import (
    IPersonSet,
    PersonCreationRationale,
    TeamEmailAddressError,
    TeamMembershipStatus,
    )
from lp.registry.interfaces.personnotification import IPersonNotificationSet
from lp.registry.model.person import (
    Person,
    PersonSet,
    )
from lp.registry.tests.test_person import KarmaTestMixin
from lp.services.config import config
from lp.services.database.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.services.database.sqlbase import cursor
from lp.services.identity.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    AccountSuspendedError,
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
from lp.soyuz.enums import ArchiveStatus
from lp.testing import (
    ANONYMOUS,
    celebrity_logged_in,
    login,
    login_person,
    logout,
    person_logged_in,
    StormStatementRecorder,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


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
        person_ids = [
            self.factory.makePerson().id
            for i in range(3)]

        with StormStatementRecorder() as recorder:
            persons = list(self.person_set.getPrecachedPersonsFromIDs(
                person_ids, need_karma=True, need_ubuntu_coc=True,
                need_location=True, need_archive=True,
                need_preferred_email=True, need_validity=True))
        self.assertThat(recorder, HasQueryCount(LessThan(2)))

        with StormStatementRecorder() as recorder:
            for person in persons:
                person.is_valid_person
                person.karma
                person.is_ubuntu_coc_signer
                person.location,
                person.archive
                person.preferredemail
        self.assertThat(recorder, HasQueryCount(LessThan(1)))

    def test_getByOpenIDIdentifier_returns_person(self):
        # getByOpenIDIdentifier takes a full OpenID identifier and
        # returns the corresponding person.
        person = self.factory.makePerson()
        with person_logged_in(person):
            identifier = person.account.openid_identifiers.one().identifier
        self.assertEqual(
            person,
            self.person_set.getByOpenIDIdentifier(
                u'http://openid.launchpad.dev/+id/%s' % identifier))
        self.assertEqual(
            person,
            self.person_set.getByOpenIDIdentifier(
                u'http://ubuntu-openid.launchpad.dev/+id/%s' % identifier))

    def test_getByOpenIDIdentifier_for_nonexistent_identifier_is_none(self):
        # None is returned if there's no matching person.
        self.assertIs(
            None,
            self.person_set.getByOpenIDIdentifier(
                u'http://openid.launchpad.dev/+id/notanid'))

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


class TestPersonSetMergeMailingListSubscriptions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        # Use the unsecured PersonSet so that private methods can be tested.
        self.person_set = PersonSet()
        self.from_person = self.factory.makePerson()
        self.to_person = self.factory.makePerson()
        self.cur = cursor()

    def test__mergeMailingListSubscriptions_no_subscriptions(self):
        self.person_set._mergeMailingListSubscriptions(
            self.cur, self.from_person.id, self.to_person.id)
        self.assertEqual(0, self.cur.rowcount)

    def test__mergeMailingListSubscriptions_with_subscriptions(self):
        naked_person = removeSecurityProxy(self.from_person)
        naked_person.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'test-mailinglist', 'team-owner')
        with person_logged_in(self.team.teamowner):
            self.team.addMember(
                self.from_person, reviewer=self.team.teamowner)
        transaction.commit()
        self.person_set._mergeMailingListSubscriptions(
            self.cur, self.from_person.id, self.to_person.id)
        self.assertEqual(1, self.cur.rowcount)


class TestPersonSetMerge(TestCaseWithFactory, KarmaTestMixin):
    """Test cases for PersonSet merge."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetMerge, self).setUp()
        self.person_set = getUtility(IPersonSet)

    def _do_premerge(self, from_person, to_person):
        # Do the pre merge work performed by the LoginToken.
        with celebrity_logged_in('admin'):
            email = from_person.preferredemail
            email.status = EmailAddressStatus.NEW
            email.person = to_person
        transaction.commit()

    def _do_merge(self, from_person, to_person, reviewer=None):
        # Perform the merge as the db user that will be used by the jobs.
        with dbuser(config.IPersonMergeJobSource.dbuser):
            self.person_set.merge(from_person, to_person, reviewer=reviewer)
        return from_person, to_person

    def _get_testable_account(self, person, date_created, openid_identifier):
        # Return a naked account with predictable attributes.
        account = removeSecurityProxy(person.account)
        account.date_created = date_created
        account.openid_identifier = openid_identifier
        return account

    def test_delete_no_notifications(self):
        team = self.factory.makeTeam()
        owner = team.teamowner
        transaction.commit()
        with dbuser(config.IPersonMergeJobSource.dbuser):
            self.person_set.delete(team, owner)
        notification_set = getUtility(IPersonNotificationSet)
        notifications = notification_set.getNotificationsToSend()
        self.assertEqual(0, notifications.count())

    def test_openid_identifiers(self):
        # Verify that OpenId Identifiers are merged.
        duplicate = self.factory.makePerson()
        duplicate_identifier = removeSecurityProxy(
            duplicate.account).openid_identifiers.any().identifier
        person = self.factory.makePerson()
        person_identifier = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        self.assertEqual(
            0,
            removeSecurityProxy(duplicate.account).openid_identifiers.count())

        merged_identifiers = [
            identifier.identifier for identifier in
                removeSecurityProxy(person.account).openid_identifiers]

        self.assertIn(duplicate_identifier, merged_identifiers)
        self.assertIn(person_identifier, merged_identifiers)

    def test_karmacache_transferred_to_user_has_no_karma(self):
        # Verify that the merged user has no KarmaCache entries,
        # and the karma total was transfered.
        self.cache_manager = getUtility(IKarmaCacheManager)
        product = self.factory.makeProduct()
        duplicate = self.factory.makePerson()
        self._makeKarmaCache(
            duplicate, product, [('bugs', 10)])
        self._makeKarmaTotalCache(duplicate, 15)
        # The karma changes invalidated duplicate instance.
        duplicate = self.person_set.get(duplicate.id)
        person = self.factory.makePerson()
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        self.assertEqual([], duplicate.karma_category_caches)
        self.assertEqual(0, duplicate.karma)
        self.assertEqual(15, person.karma)

    def test_karmacache_transferred_to_user_has_karma(self):
        # Verify that the merged user has no KarmaCache entries,
        # and the karma total was summed.
        self.cache_manager = getUtility(IKarmaCacheManager)
        product = self.factory.makeProduct()
        duplicate = self.factory.makePerson()
        self._makeKarmaCache(
            duplicate, product, [('bugs', 10)])
        self._makeKarmaTotalCache(duplicate, 15)
        person = self.factory.makePerson()
        self._makeKarmaCache(
            person, product, [('bugs', 9)])
        self._makeKarmaTotalCache(person, 13)
        # The karma changes invalidated duplicate and person instances.
        duplicate = self.person_set.get(duplicate.id)
        person = self.person_set.get(person.id)
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        self.assertEqual([], duplicate.karma_category_caches)
        self.assertEqual(0, duplicate.karma)
        self.assertEqual(28, person.karma)

    def test_person_date_created_preserved(self):
        # Verify that the oldest datecreated is merged.
        person = self.factory.makePerson()
        duplicate = self.factory.makePerson()
        oldest_date = datetime(
            2005, 11, 25, 0, 0, 0, 0, pytz.timezone('UTC'))
        removeSecurityProxy(duplicate).datecreated = oldest_date
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        self.assertEqual(oldest_date, person.datecreated)

    def test_team_with_active_mailing_list_raises_error(self):
        # A team with an active mailing list cannot be merged.
        target_team = self.factory.makeTeam()
        test_team = self.factory.makeTeam()
        self.factory.makeMailingList(
            test_team, test_team.teamowner)
        self.assertRaises(
            AssertionError, self.person_set.merge, test_team, target_team)

    def test_team_with_inactive_mailing_list(self):
        # A team with an inactive mailing list can be merged.
        target_team = self.factory.makeTeam()
        test_team = self.factory.makeTeam()
        mailing_list = self.factory.makeMailingList(
            test_team, test_team.teamowner)
        mailing_list.deactivate()
        mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        test_team, target_team = self._do_merge(
            test_team, target_team, test_team.teamowner)
        self.assertEqual(target_team, test_team.merged)
        self.assertEqual(
            MailingListStatus.PURGED, test_team.mailing_list.status)
        emails = getUtility(IEmailAddressSet).getByPerson(target_team).count()
        self.assertEqual(0, emails)

    def test_team_with_purged_mailing_list(self):
        # A team with a purges mailing list can be merged.
        target_team = self.factory.makeTeam()
        test_team = self.factory.makeTeam()
        mailing_list = self.factory.makeMailingList(
            test_team, test_team.teamowner)
        mailing_list.deactivate()
        mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        mailing_list.purge()
        test_team, target_team = self._do_merge(
            test_team, target_team, test_team.teamowner)
        self.assertEqual(target_team, test_team.merged)

    def test_team_with_members(self):
        # Team members are removed before merging.
        target_team = self.factory.makeTeam()
        test_team = self.factory.makeTeam()
        former_member = self.factory.makePerson()
        with person_logged_in(test_team.teamowner):
            test_team.addMember(former_member, test_team.teamowner)
        test_team, target_team = self._do_merge(
            test_team, target_team, test_team.teamowner)
        self.assertEqual(target_team, test_team.merged)
        self.assertEqual([], list(former_member.super_teams))

    def test_team_without_super_teams_is_fine(self):
        # A team with no members and no super teams
        # merges without errors.
        test_team = self.factory.makeTeam()
        target_team = self.factory.makeTeam()
        login_person(test_team.teamowner)
        self._do_merge(test_team, target_team, test_team.teamowner)

    def test_team_with_super_teams(self):
        # A team with superteams can be merged, but the memberships
        # are not transferred.
        test_team = self.factory.makeTeam()
        super_team = self.factory.makeTeam()
        target_team = self.factory.makeTeam()
        login_person(test_team.teamowner)
        test_team.join(super_team, test_team.teamowner)
        test_team, target_team = self._do_merge(
            test_team, target_team, test_team.teamowner)
        self.assertEqual(target_team, test_team.merged)
        self.assertEqual([], list(target_team.super_teams))

    def test_merge_moves_branches(self):
        # When person/teams are merged, branches owned by the from person
        # are moved.
        person = self.factory.makePerson()
        branch = self.factory.makeBranch()
        duplicate = branch.owner
        self._do_premerge(branch.owner, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        branches = person.getBranches()
        self.assertEqual(1, branches.count())

    def test_merge_with_duplicated_branches(self):
        # If both the from and to people have branches with the same name,
        # merging renames the duplicate from the from person's side.
        product = self.factory.makeProduct()
        from_branch = self.factory.makeBranch(name='foo', product=product)
        to_branch = self.factory.makeBranch(name='foo', product=product)
        mergee = to_branch.owner
        duplicate = from_branch.owner
        self._do_premerge(duplicate, mergee)
        login_person(mergee)
        duplicate, mergee = self._do_merge(duplicate, mergee)
        branches = [b.name for b in mergee.getBranches()]
        self.assertEqual(2, len(branches))
        self.assertContentEqual([u'foo', u'foo-1'], branches)

    def test_merge_moves_recipes(self):
        # When person/teams are merged, recipes owned by the from person are
        # moved.
        person = self.factory.makePerson()
        recipe = self.factory.makeSourcePackageRecipe()
        duplicate = recipe.owner
        # Delete the PPA, which is required for the merge to work.
        with person_logged_in(duplicate):
            recipe.owner.archive.status = ArchiveStatus.DELETED
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        self.assertEqual(1, person.recipes.count())

    def test_merge_with_duplicated_recipes(self):
        # If both the from and to people have recipes with the same name,
        # merging renames the duplicate from the from person's side.
        merge_from = self.factory.makeSourcePackageRecipe(
            name=u'foo', description=u'FROM')
        merge_to = self.factory.makeSourcePackageRecipe(
            name=u'foo', description=u'TO')
        duplicate = merge_from.owner
        mergee = merge_to.owner
        # Delete merge_from's PPA, which is required for the merge to work.
        with person_logged_in(merge_from.owner):
            merge_from.owner.archive.status = ArchiveStatus.DELETED
        self._do_premerge(merge_from.owner, mergee)
        login_person(mergee)
        duplicate, mergee = self._do_merge(duplicate, mergee)
        recipes = mergee.recipes
        self.assertEqual(2, recipes.count())
        descriptions = [r.description for r in recipes]
        self.assertEqual([u'TO', u'FROM'], descriptions)
        self.assertEqual(u'foo-1', recipes[1].name)

    def assertSubscriptionMerges(self, target):
        # Given a subscription target, we want to make sure that subscriptions
        # that the duplicate person made are carried over to the merged
        # account.
        duplicate = self.factory.makePerson()
        with person_logged_in(duplicate):
            target.addSubscription(duplicate, duplicate)
        person = self.factory.makePerson()
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        # The merged person has the subscription, and the duplicate person
        # does not.
        self.assertTrue(target.getSubscription(person) is not None)
        self.assertTrue(target.getSubscription(duplicate) is None)

    def assertConflictingSubscriptionDeletes(self, target):
        # Given a subscription target, we want to make sure that subscriptions
        # that the duplicate person made that conflict with existing
        # subscriptions in the merged account are deleted.
        duplicate = self.factory.makePerson()
        person = self.factory.makePerson()
        with person_logged_in(duplicate):
            target.addSubscription(duplicate, duplicate)
        with person_logged_in(person):
            # The description lets us show that we still have the right
            # subscription later.
            target.addBugSubscriptionFilter(person, person).description = (
                u'a marker')
        self._do_premerge(duplicate, person)
        login_person(person)
        duplicate, person = self._do_merge(duplicate, person)
        # The merged person still has the original subscription, as shown
        # by the marker name.
        self.assertEqual(
            target.getSubscription(person).bug_filters[0].description,
            u'a marker')
        # The conflicting subscription on the duplicate has been deleted.
        self.assertTrue(target.getSubscription(duplicate) is None)

    def test_merge_with_product_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeProduct())

    def test_merge_with_conflicting_product_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(self.factory.makeProduct())

    def test_merge_with_project_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeProject())

    def test_merge_with_conflicting_project_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(self.factory.makeProject())

    def test_merge_with_distroseries_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeDistroSeries())

    def test_merge_with_conflicting_distroseries_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(
            self.factory.makeDistroSeries())

    def test_merge_with_milestone_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeMilestone())

    def test_merge_with_conflicting_milestone_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(
            self.factory.makeMilestone())

    def test_merge_with_productseries_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeProductSeries())

    def test_merge_with_conflicting_productseries_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(
            self.factory.makeProductSeries())

    def test_merge_with_distribution_subscription(self):
        # See comments in assertSubscriptionMerges.
        self.assertSubscriptionMerges(self.factory.makeDistribution())

    def test_merge_with_conflicting_distribution_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        self.assertConflictingSubscriptionDeletes(
            self.factory.makeDistribution())

    def test_merge_with_sourcepackage_subscription(self):
        # See comments in assertSubscriptionMerges.
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertSubscriptionMerges(dsp)

    def test_merge_with_conflicting_sourcepackage_subscription(self):
        # See comments in assertConflictingSubscriptionDeletes.
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertConflictingSubscriptionDeletes(dsp)

    def test_merge_accesspolicygrants(self):
        # AccessPolicyGrants are transferred from the duplicate.
        person = self.factory.makePerson()
        grant = self.factory.makeAccessPolicyGrant()
        self._do_premerge(grant.grantee, person)

        source = getUtility(IAccessPolicyGrantSource)
        self.assertEqual(
            grant.grantee, source.findByPolicy([grant.policy]).one().grantee)
        with person_logged_in(person):
            self._do_merge(grant.grantee, person)
        self.assertEqual(
            person, source.findByPolicy([grant.policy]).one().grantee)

    def test_merge_accesspolicygrants_conflicts(self):
        # Conflicting AccessPolicyGrants are deleted.
        policy = self.factory.makeAccessPolicy()

        person = self.factory.makePerson()
        person_grantor = self.factory.makePerson()
        person_grant = self.factory.makeAccessPolicyGrant(
            grantee=person, grantor=person_grantor, policy=policy)
        person_grant_date = person_grant.date_created

        duplicate = self.factory.makePerson()
        duplicate_grantor = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(
            grantee=duplicate, grantor=duplicate_grantor, policy=policy)

        self._do_premerge(duplicate, person)
        with person_logged_in(person):
            self._do_merge(duplicate, person)

        # Only one grant for the policy exists: the retained person's.
        source = getUtility(IAccessPolicyGrantSource)
        self.assertThat(
            source.findByPolicy([policy]).one(),
            MatchesStructure.byEquality(
                policy=policy,
                grantee=person,
                date_created=person_grant_date))

    def test_mergeAsync(self):
        # mergeAsync() creates a new `PersonMergeJob`.
        from_person = self.factory.makePerson()
        to_person = self.factory.makePerson()
        login_person(from_person)
        job = self.person_set.mergeAsync(from_person, to_person, from_person)
        self.assertEqual(from_person, job.from_person)
        self.assertEqual(to_person, job.to_person)
        self.assertEqual(from_person, job.requester)

    def test_mergeProposedInvitedTeamMembership(self):
        # Proposed and invited memberships are declined.
        TMS = TeamMembershipStatus
        dupe_team = self.factory.makeTeam()
        test_team = self.factory.makeTeam()
        inviting_team = self.factory.makeTeam()
        proposed_team = self.factory.makeTeam()
        with celebrity_logged_in('admin'):
            # Login as a user who can work with all these teams.
            inviting_team.addMember(
                dupe_team, inviting_team.teamowner)
            proposed_team.addMember(
                dupe_team, dupe_team.teamowner, status=TMS.PROPOSED)
            self._do_merge(dupe_team, test_team, test_team.teamowner)
            self.assertEqual(0, inviting_team.invited_member_count)
            self.assertEqual(0, proposed_team.proposed_member_count)


class TestPersonSetCreateByOpenId(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSetCreateByOpenId, self).setUp()
        self.person_set = getUtility(IPersonSet)
        self.store = IMasterStore(Account)

        # Generate some valid test data.
        self.account = self.makeAccount()
        self.identifier = self.makeOpenIdIdentifier(self.account, u'whatever')
        self.person = self.makePerson(self.account)
        self.email = self.makeEmailAddress(
            email='whatever@example.com', person=self.person)

    def makeAccount(self):
        return self.store.add(Account(
            displayname='Displayname',
            creation_rationale=AccountCreationRationale.UNKNOWN,
            status=AccountStatus.ACTIVE))

    def makeOpenIdIdentifier(self, account, identifier):
        openid_identifier = OpenIdIdentifier()
        openid_identifier.identifier = identifier
        openid_identifier.account = account
        return self.store.add(openid_identifier)

    def makePerson(self, account):
        return self.store.add(Person(
            name='acc%d' % account.id, account=account,
            displayname='Displayname',
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

    def testNewEmailAddress(self):
        # Account looked up by OpenId identifier and new EmailAddress
        # attached. We can do this because we trust our OpenId Provider.
        new_email = u'new_email@example.com'
        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, new_email, 'Ignored Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertIs(True, updated)
        self.assertIs(self.person, found)
        self.assertIs(self.account, found.account)
        self.assertEqual(
            [self.identifier], list(self.account.openid_identifiers))

        # The old email address is still there and correctly linked.
        self.assertIs(self.email, found.preferredemail)
        self.assertIs(self.email.person, self.person)

        # The new email address is there too and correctly linked.
        new_email = self.store.find(EmailAddress, email=new_email).one()
        self.assertIs(new_email.person, self.person)
        self.assertEqual(EmailAddressStatus.NEW, new_email.status)

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

        self.assertIs(True, updated)

        self.assertIsNot(None, found.account)
        self.assertEqual(
            new_identifier, found.account.openid_identifiers.any().identifier)
        self.assertIs(self.email.person, found)
        self.assertEqual(EmailAddressStatus.PREFERRED, self.email.status)

    def testMovedEmailAddress(self):
        # The EmailAddress and OpenId Identifier are both in the
        # database, but they are not linked to the same account. The
        # identifier needs to be relinked to the correct account - the
        # user able to log into the trusted SSO with that email address
        # should be able to log into Launchpad with that email address.
        # This lets us cope with the SSO migrating email addresses
        # between SSO accounts.
        self.identifier.account = self.store.find(
            Account, displayname='Foo Bar').one()

        found, updated = self.person_set.getOrCreateByOpenIDIdentifier(
            self.identifier.identifier, self.email.email, 'New Name',
            PersonCreationRationale.UNKNOWN, 'No Comment')
        found = removeSecurityProxy(found)

        self.assertIs(True, updated)
        self.assertIs(self.person, found)

        self.assertIs(found.account, self.identifier.account)
        self.assertIn(self.identifier, list(found.account.openid_identifiers))

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
        self.assertEqual(
            "when purchasing an application via Software Center.",
            removeSecurityProxy(person.account).status_comment)

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
