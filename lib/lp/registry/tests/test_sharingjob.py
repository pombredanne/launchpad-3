# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SharingJobs."""
from lp.services.database.lpstorm import IStore
from lp.services.job.interfaces.job import JobStatus

__metaclass__ = type

import transaction

from testtools.content import Content
from testtools.content_type import UTF8_TEXT
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import (
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.registry.enums import InformationType
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactSource,
    IAccessArtifactGrantSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.registry.interfaces.sharingjob import (
    IRemoveBugSubscriptionsJobSource,
    IRemoveGranteeSubscriptionsJobSource,
    ISharingJob,
    ISharingJobSource,
    )
from lp.registry.model.sharingjob import (
    RemoveBugSubscriptionsJob,
    RemoveGranteeSubscriptionsJob,
    SharingJob,
    SharingJobDerived,
    SharingJobType,
    )
from lp.services.features.testing import FeatureFixture
from lp.services.job.tests import block_on_job
from lp.services.mail.sendmail import format_address_for_person
from lp.testing import (
    login_person,
    person_logged_in,
    run_script,
    TestCaseWithFactory,
    )
from lp.testing.fixture import DisableTriggerFixture
from lp.testing.layers import (
    CeleryJobLayer,
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class SharingJobTestCase(TestCaseWithFactory):
    """Test case for basic SharingJob class."""

    layer = LaunchpadZopelessLayer

    def test_init(self):
        pillar = self.factory.makeProduct()
        grantee = self.factory.makePerson()
        metadata = ('some', 'arbitrary', 'metadata')
        sharing_job = SharingJob(
            SharingJobType.REMOVE_GRANTEE_SUBSCRIPTIONS,
            pillar, grantee, metadata)
        self.assertEqual(
            SharingJobType.REMOVE_GRANTEE_SUBSCRIPTIONS, sharing_job.job_type)
        self.assertEqual(pillar, sharing_job.product)
        self.assertEqual(grantee, sharing_job.grantee)
        expected_json_data = '["some", "arbitrary", "metadata"]'
        self.assertEqual(expected_json_data, sharing_job._json_data)

    def test_metadata(self):
        # The python structure stored as json is returned as python.
        metadata = {
            'a_list': ('some', 'arbitrary', 'metadata'),
            'a_number': 1,
            'a_string': 'string',
            }
        pillar = self.factory.makeProduct()
        grantee = self.factory.makePerson()
        sharing_job = SharingJob(
            SharingJobType.REMOVE_GRANTEE_SUBSCRIPTIONS,
            pillar, grantee, metadata)
        metadata['a_list'] = list(metadata['a_list'])
        self.assertEqual(metadata, sharing_job.metadata)


class SharingJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the SharingJobDerived class."""

    layer = DatabaseFunctionalLayer

    def _makeJob(self, prod_name=None, grantee_name=None):
        pillar = self.factory.makeProduct(name=prod_name)
        grantee = self.factory.makePerson(name=grantee_name)
        requestor = self.factory.makePerson()
        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, requestor)
        return job

    def test_repr(self):
        job = self._makeJob('prod', 'fred')
        self.assertEqual(
            '<REMOVE_GRANTEE_SUBSCRIPTIONS job for Fred and Prod>',
            repr(job))

    def test_create_success(self):
        # Create an instance of SharingJobDerived that delegates to SharingJob.
        self.assertIs(True, ISharingJobSource.providedBy(SharingJobDerived))
        job = self._makeJob()
        self.assertIsInstance(job, SharingJobDerived)
        self.assertIs(True, ISharingJob.providedBy(job))
        self.assertIs(True, ISharingJob.providedBy(job.context))

    def test_create_raises_error(self):
        # SharingJobDerived.create() raises an error because it
        # needs to be subclassed to work properly.
        pillar = self.factory.makeProduct()
        grantee = self.factory.makePerson()
        self.assertRaises(
            AttributeError, SharingJobDerived.create, pillar, grantee, {})

    def test_iterReady(self):
        # iterReady finds job in the READY status that are of the same type.
        job_1 = self._makeJob()
        job_2 = self._makeJob()
        job_2.start()
        jobs = list(RemoveGranteeSubscriptionsJob.iterReady())
        self.assertEqual(1, len(jobs))
        self.assertEqual(job_1, jobs[0])

    def test_log_name(self):
        # The log_name is the name of the implementing class.
        job = self._makeJob()
        self.assertEqual('RemoveGranteeSubscriptionsJob', job.log_name)

    def test_getOopsVars(self):
        # The pillar and grantee name are added to the oops vars.
        pillar = self.factory.makeDistribution()
        grantee = self.factory.makePerson()
        requestor = self.factory.makePerson()
        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, requestor)
        oops_vars = job.getOopsVars()
        self.assertIs(True, len(oops_vars) > 4)
        self.assertIn(('distro', pillar.name), oops_vars)
        self.assertIn(('grantee', grantee.name), oops_vars)


def disable_trigger_fixture():
    # XXX 2012-05-22 wallyworld bug=1002596
    # No need to use this fixture when triggers are removed.
    return DisableTriggerFixture(
            {'bugsubscription':
                 'bugsubscription_mirror_legacy_access_t',
             'bug': 'bug_mirror_legacy_access_t',
             'bugtask': 'bugtask_mirror_legacy_access_t',
        })


class RemoveGranteeSubscriptionsJobTestCase(TestCaseWithFactory):
    """Test case for the RemoveGranteeSubscriptionsJob class."""

    layer = CeleryJobLayer

    def setUp(self):
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes':
                'xRemoveGranteeSubscriptionsJob',
        }))
        super(RemoveGranteeSubscriptionsJobTestCase, self).setUp()

    def test_create(self):
        # Create an instance of RemoveGranteeSubscriptionsJob that stores
        # the information type and artifact information.
        self.assertIs(
            True,
            IRemoveGranteeSubscriptionsJobSource.providedBy(
                RemoveGranteeSubscriptionsJob))
        self.assertEqual(
            SharingJobType.REMOVE_GRANTEE_SUBSCRIPTIONS,
            RemoveGranteeSubscriptionsJob.class_job_type)
        pillar = self.factory.makeProduct()
        grantee = self.factory.makePerson()
        requestor = self.factory.makePerson()
        bug = self.factory.makeBug(product=pillar)
        branch = self.factory.makeBranch(product=pillar)
        info_type = InformationType.USERDATA
        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, requestor, [info_type], [bug], [branch])
        naked_job = removeSecurityProxy(job)
        self.assertIsInstance(job, RemoveGranteeSubscriptionsJob)
        self.assertEqual(pillar, job.pillar)
        self.assertEqual(grantee, job.grantee)
        self.assertEqual(requestor.id, naked_job.requestor_id)
        self.assertContentEqual([info_type], naked_job.information_types)
        self.assertContentEqual([bug.id], naked_job.bug_ids)
        self.assertContentEqual([branch.unique_name], naked_job.branch_names)

    def test_getErrorRecipients(self):
        # The pillar owner and job requestor are the error recipients.
        pillar = self.factory.makeDistribution()
        grantee = self.factory.makePerson()
        requestor = self.factory.makePerson()
        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, requestor)
        expected_emails = [
            format_address_for_person(person)
            for person in (pillar.owner, requestor)]
        self.assertContentEqual(
            expected_emails, job.getErrorRecipients())

    def test_create_no_pillar(self):
        # Create an instance of RemoveGranteeSubscriptionsJob that stores
        # the information type and artifact information but with no pillar.
        grantee = self.factory.makePerson()
        requestor = self.factory.makePerson()
        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            None, grantee, requestor)
        naked_job = removeSecurityProxy(job)
        self.assertIsInstance(job, RemoveGranteeSubscriptionsJob)
        self.assertEqual(None, job.pillar)
        self.assertEqual(grantee, job.grantee)
        self.assertEqual(requestor.id, naked_job.requestor_id)
        self.assertIn('all pillars', repr(job))
        self.assertEqual(1, len(job.getErrorRecipients()))

    def _make_subscribed_bug(self, grantee, product=None, distribution=None,
                             information_type=InformationType.USERDATA):
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, product=product, distribution=distribution,
            information_type=information_type)
        with person_logged_in(owner):
            bug.subscribe(grantee, owner)
        return bug, owner

    def test_unsubscribe_bugs(self):
        # The requested bug subscriptions are removed.
        pillar = self.factory.makeDistribution()
        grantee = self.factory.makePerson()
        owner = self.factory.makePerson()
        bug, ignored = self._make_subscribed_bug(grantee, distribution=pillar)
        getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, owner, bugs=[bug])
        with block_on_job(self):
            transaction.commit()
        self.assertNotIn(
            grantee, removeSecurityProxy(bug).getDirectSubscribers())

    def _make_subscribed_branch(self, pillar, grantee, private=False):
        owner = self.factory.makePerson()
        branch = self.factory.makeBranch(
            owner=owner, product=pillar, private=private)
        with person_logged_in(owner):
            branch.subscribe(grantee,
                BranchSubscriptionNotificationLevel.NOEMAIL, None,
                CodeReviewNotificationLevel.NOEMAIL, owner)
        return branch

    def test_unsubscribe_branches(self):
        # The requested branch subscriptions are removed.
        owner = self.factory.makePerson()
        pillar = self.factory.makeProduct(owner=owner)
        grantee = self.factory.makePerson()
        branch = self._make_subscribed_branch(pillar, grantee)
        getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, owner, branches=[branch])
        with block_on_job(self):
            transaction.commit()
        self.assertNotIn(
            grantee, list(removeSecurityProxy(branch).subscribers))

    def _assert_unsubscribe_pillar_artifacts_direct_bugs(self,
                                                         pillar=None):
        # All direct pillar bug subscriptions are removed.
        grantee = self.factory.makePerson()

        # Make some bugs subscribed to by grantee.
        bug1, ignored = self._make_subscribed_bug(
            grantee, product=pillar,
            information_type=InformationType.EMBARGOEDSECURITY)
        bug2, ignored = self._make_subscribed_bug(
            grantee, product=pillar,
            information_type=InformationType.USERDATA)

        # Subscribing grantee to bugs creates an access grant so we need to
        # revoke those for our test.
        accessartifact_source = getUtility(IAccessArtifactSource)
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        accessartifact_grant_source.revokeByArtifact(
            accessartifact_source.find([bug1, bug2]), [grantee])

        # Now run the job.
        requestor = self.factory.makePerson()
        getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, grantee, requestor)
        with block_on_job(self):
            transaction.commit()

        self.assertNotIn(
            grantee, removeSecurityProxy(bug1).getDirectSubscribers())
        self.assertNotIn(
            grantee, removeSecurityProxy(bug2).getDirectSubscribers())

    def test_unsubscribe_pillar_artifacts_direct_bugs(self):
        pillar = self.factory.makeProduct()
        self._assert_unsubscribe_pillar_artifacts_direct_bugs(pillar)

    def test_unsubscribe_artifacts_direct_bugs_unspecified_pillar(self):
        self._assert_unsubscribe_pillar_artifacts_direct_bugs()

    def _assert_unsubscribe_pillar_artifacts_indirect_bugs(self,
                                                           pillar=None):
        # Do not delete subscriptions to bugs a user has indirect access to
        # because they belong to a team which has an artifact grant on the bug.

        person_grantee = self.factory.makePerson(name='grantee')

        # Make a bug the person_grantee is subscribed to.
        bug1, ignored = self._make_subscribed_bug(
            person_grantee, product=pillar,
            information_type=InformationType.USERDATA)

        # Make another bug and grant access to a team.
        team_owner = self.factory.makePerson(name='teamowner')
        team_grantee = self.factory.makeTeam(
            owner=team_owner,
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED,
            members=[person_grantee])
        bug2, bug2_owner = self._make_subscribed_bug(
            team_grantee, product=pillar,
            information_type=InformationType.EMBARGOEDSECURITY)
        # Add a subscription for the person_grantee.
        with person_logged_in(bug2_owner):
            bug2.subscribe(person_grantee, bug2_owner)

        # Subscribing person_grantee to bugs creates an access grant so we
        # need to revoke those for our test.
        accessartifact_source = getUtility(IAccessArtifactSource)
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        accessartifact_grant_source.revokeByArtifact(
            accessartifact_source.find([bug1, bug2]), [person_grantee])

        # Now run the job.
        requestor = self.factory.makePerson()
        getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, person_grantee, requestor)
        with block_on_job(self):
            transaction.commit()

        # person_grantee is not longer subscribed to bug1.
        self.assertNotIn(
            person_grantee, removeSecurityProxy(bug1).getDirectSubscribers())
        # person_grantee is still subscribed to bug2 because they have access
        # via a team.
        self.assertIn(
            person_grantee, removeSecurityProxy(bug2).getDirectSubscribers())

    def test_unsubscribe_pillar_artifacts_indirect_bugs(self):
        pillar = self.factory.makeProduct()
        self._assert_unsubscribe_pillar_artifacts_indirect_bugs(pillar)

    def test_unsubscribe_artifacts_indirect_bugs_unspecified_pillar(self):
        self._assert_unsubscribe_pillar_artifacts_indirect_bugs()

    def test_unsubscribe_pillar_artifacts_specific_info_types(self):
        # Only delete pillar artifacts of the specified info type.

        owner = self.factory.makePerson(name='pillarowner')
        pillar = self.factory.makeProduct(owner=owner)
        person_grantee = self.factory.makePerson(name='grantee')

        # Make bugs the person_grantee is subscribed to.
        bug1, ignored = self._make_subscribed_bug(
            person_grantee, product=pillar,
            information_type=InformationType.USERDATA)

        bug2, ignored = self._make_subscribed_bug(
            person_grantee, product=pillar,
            information_type=InformationType.EMBARGOEDSECURITY)

        # Subscribing grantee to bugs creates an access grant so we
        # need to revoke those for our test.
        accessartifact_source = getUtility(IAccessArtifactSource)
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        accessartifact_grant_source.revokeByArtifact(
            accessartifact_source.find([bug1, bug2]), [person_grantee])

        # Now run the job, removing access to userdata artifacts.
        getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            pillar, person_grantee, owner, [InformationType.USERDATA])
        with block_on_job(self):
            transaction.commit()

        self.assertNotIn(
            person_grantee, removeSecurityProxy(bug1).getDirectSubscribers())
        self.assertIn(
            person_grantee, removeSecurityProxy(bug2).getDirectSubscribers())


class TestRunViaCron(TestCaseWithFactory):
    """Sharing jobs run via cron."""

    layer = DatabaseFunctionalLayer

    def test_run_remove_grantee_subscriptions_cronscript(self):
        # The cronscript is configured: schema-lazr.conf and security.cfg.
        # The job runs correctly and the requested bug subscriptions are
        # removed.
        distro = self.factory.makeDistribution()
        grantee = self.factory.makePerson()
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, distribution=distro,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.subscribe(grantee, owner)

        job = getUtility(IRemoveGranteeSubscriptionsJobSource).create(
            distro, grantee, owner, bugs=[bug])
        transaction.commit()

        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IRemoveGranteeSubscriptionsJobSource.getName()))
        self.addDetail("stdout", Content(UTF8_TEXT, lambda: out))
        self.addDetail("stderr", Content(UTF8_TEXT, lambda: err))
        self.assertEqual(0, exit_code)
        self.assertTrue(
            'Traceback (most recent call last)' not in err)
        IStore(job.job).invalidate()
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertNotIn(
            grantee, removeSecurityProxy(bug).getDirectSubscribers())

    def test_run_remove_bug_subscriptions_cronscript(self):
        # The cronscript is configured: schema-lazr.conf and security.cfg.
        # The job runs correctly and the requested bug subscriptions are
        # removed.
        distro = self.factory.makeDistribution()
        grantee = self.factory.makePerson()
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, distribution=distro,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.subscribe(grantee, owner)

        job = getUtility(IRemoveBugSubscriptionsJobSource).create([bug], owner)
        removeSecurityProxy(bug).information_type = (
                    InformationType.EMBARGOEDSECURITY)
        transaction.commit()

        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IRemoveBugSubscriptionsJobSource.getName()))
        self.addDetail("stdout", Content(UTF8_TEXT, lambda: out))
        self.addDetail("stderr", Content(UTF8_TEXT, lambda: err))
        self.assertEqual(0, exit_code)
        self.assertTrue(
            'Traceback (most recent call last)' not in err)
        IStore(job.job).invalidate()
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertNotIn(
            grantee, removeSecurityProxy(bug).getDirectSubscribers())


class RemoveBugSubscriptionsJobTestCase(TestCaseWithFactory):
    """Test case for the RemoveBugSubscriptionsJob class."""

    layer = CeleryJobLayer

    def setUp(self):
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes':
                'RemoveBugSubscriptionsJob',
            'disclosure.access_mirror_triggers.removed': 'true',
        }))
        self.useFixture(disable_trigger_fixture())
        super(RemoveBugSubscriptionsJobTestCase, self).setUp()

    def test_create(self):
        # Create an instance of RemoveBugSubscriptionsJob.
        self.assertIs(
            True,
            IRemoveBugSubscriptionsJobSource.providedBy(
                RemoveBugSubscriptionsJob))
        self.assertEqual(
            SharingJobType.REMOVE_BUG_SUBSCRIPTIONS,
            RemoveBugSubscriptionsJob.class_job_type)
        requestor = self.factory.makePerson()
        bug = self.factory.makeBug()
        job = getUtility(IRemoveBugSubscriptionsJobSource).create(
            [bug], requestor)
        naked_job = removeSecurityProxy(job)
        self.assertIsInstance(job, RemoveBugSubscriptionsJob)
        self.assertEqual(requestor.id, naked_job.requestor_id)
        self.assertContentEqual([bug.id], naked_job.bug_ids)

    def test_getErrorRecipients(self):
        # The pillar owner and job requestor are the error recipients.
        requestor = self.factory.makePerson()
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        job = getUtility(IRemoveBugSubscriptionsJobSource).create(
            [bug], requestor)
        expected_emails = [
            format_address_for_person(person)
            for person in (product.owner, requestor)]
        self.assertContentEqual(
            expected_emails, job.getErrorRecipients())

    def _assert_bug_change_unsubscribes(self, change_callback):
        # Subscribers are unsubscribed if the bug becomes invisible due to a
        # change in information_type.
        product = self.factory.makeProduct()
        owner = self.factory.makePerson()
        [policy] = getUtility(IAccessPolicySource).find(
            [(product, InformationType.USERDATA)])
        # The policy grantees will lose access.
        policy_indirect_grantee = self.factory.makePerson()
        policy_team_grantee = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED,
            members=[policy_indirect_grantee])

        self.factory.makeAccessPolicyGrant(policy, policy_team_grantee, owner)
        login_person(owner)
        bug = self.factory.makeBug(
            owner=owner, product=product,
            information_type=InformationType.USERDATA)

        # The artifact grantees will not lose access when the job is run.
        artifact_indirect_grantee = self.factory.makePerson()
        artifact_team_grantee = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED,
            members=[artifact_indirect_grantee])

        bug.subscribe(policy_team_grantee, owner)
        bug.subscribe(policy_indirect_grantee, owner)
        bug.subscribe(artifact_team_grantee, owner)
        bug.subscribe(artifact_indirect_grantee, owner)
        # Subscribing policy_team_grantee has created an artifact grant so we
        # need to revoke that to test the job.
        getUtility(IAccessArtifactGrantSource).revokeByArtifact(
            getUtility(IAccessArtifactSource).find(
                [bug]), [policy_team_grantee])

        # policy grantees are subscribed because the job has not been run yet.
        subscribers = removeSecurityProxy(bug).getDirectSubscribers()
        self.assertIn(policy_team_grantee, subscribers)
        self.assertIn(policy_indirect_grantee, subscribers)

        # Change bug bug attributes so that it can become inaccessible for
        # some users.
        removeSecurityProxy(bug).information_type = (
            InformationType.EMBARGOEDSECURITY)

        getUtility(IRemoveBugSubscriptionsJobSource).create([bug], owner)
        with block_on_job(self):
            transaction.commit()

        # Check the result. Policy grantees will be unsubscribed.
        subscribers = removeSecurityProxy(bug).getDirectSubscribers()
        self.assertNotIn(policy_team_grantee, subscribers)
        self.assertNotIn(policy_indirect_grantee, subscribers)
        self.assertIn(artifact_team_grantee, subscribers)
        self.assertIn(artifact_indirect_grantee, subscribers)

    def test_change_information_type(self):
        # Changing the information type of a bug unsubscribes users who can no
        # longer see the bug.
        def change_information_type(bug):
            # Set the info_type attribute directly since
            # transitionToInformationType queues a job.
            removeSecurityProxy(bug).information_type = (
                InformationType.EMBARGOEDSECURITY)

        self._assert_bug_change_unsubscribes(change_information_type)

    def test_change_target(self):
        # Changing the target of a bug unsubscribes users who can no
        # longer see the bug.
        def change_target(bug):
            # Set the new target directly since transitionToTarget queues a job
            another_product = self.factory.makeProduct()
            removeSecurityProxy(bug).default_bugtask.product = another_product

        self._assert_bug_change_unsubscribes(change_target)
