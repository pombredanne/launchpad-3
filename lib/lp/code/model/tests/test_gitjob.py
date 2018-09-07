# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `GitJob`s."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import hashlib

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
import pytz
from testtools.matchers import (
    ContainsDict,
    Equals,
    MatchesDict,
    MatchesSetwise,
    MatchesStructure,
    )
import transaction
from zope.event import notify
from zope.interface import providedBy
from zope.security.proxy import removeSecurityProxy

from lp.code.adapters.gitrepository import GitRepositoryDelta
from lp.code.enums import (
    GitGranteeType,
    GitObjectType,
    )
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG,
    )
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    IReclaimGitRepositorySpaceJob,
    )
from lp.code.model.gitjob import (
    describe_repository_delta,
    GitJob,
    GitJobDerived,
    GitJobType,
    GitRefScanJob,
    ReclaimGitRepositorySpaceJob,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.job.runner import JobRunner
from lp.services.webapp import canonical_url
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )


class TestGitJob(TestCaseWithFactory):
    """Tests for `GitJob`."""

    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        # `GitJob` objects provide `IGitJob`.
        repository = self.factory.makeGitRepository()
        self.assertProvides(
            GitJob(repository, GitJobType.REF_SCAN, {}), IGitJob)


class TestGitJobDerived(TestCaseWithFactory):
    """Tests for `GitJobDerived`."""

    layer = ZopelessDatabaseLayer

    def test_getOopsMailController(self):
        """By default, no mail is sent about failed BranchJobs."""
        repository = self.factory.makeGitRepository()
        job = GitJob(repository, GitJobType.REF_SCAN, {})
        derived = GitJobDerived(job)
        self.assertIsNone(derived.getOopsMailController("x"))


class TestGitRefScanJob(TestCaseWithFactory):
    """Tests for `GitRefScanJob`."""

    layer = ZopelessDatabaseLayer

    @staticmethod
    def makeFakeRefs(paths):
        return {
            path: {"object": {
                "sha1": hashlib.sha1(path).hexdigest(),
                "type": "commit",
                }}
            for path in paths}

    @staticmethod
    def makeFakeCommits(author, author_date_gen, paths):
        epoch = datetime.fromtimestamp(0, tz=pytz.UTC)
        dates = {path: next(author_date_gen) for path in paths}
        return [{
            "sha1": unicode(hashlib.sha1(path).hexdigest()),
            "message": "tip of %s" % path,
            "author": {
                "name": author.displayname,
                "email": author.preferredemail.email,
                "time": int((dates[path] - epoch).total_seconds()),
                },
            "committer": {
                "name": author.displayname,
                "email": author.preferredemail.email,
                "time": int((dates[path] - epoch).total_seconds()),
                },
            "parents": [],
            "tree": unicode(hashlib.sha1("").hexdigest()),
            } for path in paths]

    def assertRefsMatch(self, refs, repository, paths):
        matchers = [
            MatchesStructure.byEquality(
                repository=repository,
                path=path,
                commit_sha1=unicode(hashlib.sha1(path).hexdigest()),
                object_type=GitObjectType.COMMIT)
            for path in paths]
        self.assertThat(refs, MatchesSetwise(*matchers))

    def test_provides_interface(self):
        # `GitRefScanJob` objects provide `IGitRefScanJob`.
        repository = self.factory.makeGitRepository()
        self.assertProvides(GitRefScanJob.create(repository), IGitRefScanJob)

    def test___repr__(self):
        # `GitRefScanJob` objects have an informative __repr__.
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        self.assertEqual(
            "<GitRefScanJob for %s>" % repository.unique_name, repr(job))

    def test_run(self):
        # Ensure the job scans the repository.
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        paths = ("refs/heads/master", "refs/tags/1.0")
        author = repository.owner
        author_date_start = datetime(2015, 1, 1, tzinfo=pytz.UTC)
        author_date_gen = time_counter(author_date_start, timedelta(days=1))
        self.useFixture(GitHostingFixture(
            refs=self.makeFakeRefs(paths),
            commits=self.makeFakeCommits(author, author_date_gen, paths)))
        with dbuser("branchscanner"):
            JobRunner([job]).runAll()
        self.assertRefsMatch(repository.refs, repository, paths)
        self.assertEqual("refs/heads/master", repository.default_branch)

    def test_logs_bad_ref_info(self):
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        self.useFixture(GitHostingFixture(refs={"refs/heads/master": {}}))
        expected_message = (
            'Unconvertible ref refs/heads/master {}: '
            'ref info does not contain "object" key')
        with self.expectedLog(expected_message):
            with dbuser("branchscanner"):
                JobRunner([job]).runAll()
        self.assertEqual([], list(repository.refs))

    def test_triggers_webhooks(self):
        # Jobs trigger any relevant webhooks when they're enabled.
        self.useFixture(FeatureFixture({'code.git.webhooks.enabled': 'on'}))
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository, paths=['refs/heads/master', 'refs/tags/1.0'])
        hook = self.factory.makeWebhook(
            target=repository, event_types=['git:push:0.1'])
        job = GitRefScanJob.create(repository)
        paths = ('refs/heads/master', 'refs/tags/2.0')
        self.useFixture(GitHostingFixture(refs=self.makeFakeRefs(paths)))
        with dbuser('branchscanner'):
            JobRunner([job]).runAll()
        delivery = hook.deliveries.one()
        sha1 = lambda s: hashlib.sha1(s).hexdigest()
        self.assertThat(
            delivery,
            MatchesStructure(
                event_type=Equals('git:push:0.1'),
                payload=MatchesDict({
                    'git_repository': Equals('/' + repository.unique_name),
                    'git_repository_path': Equals(repository.unique_name),
                    'ref_changes': Equals({
                        'refs/tags/1.0': {
                            'old': {'commit_sha1': sha1('refs/tags/1.0')},
                            'new': None},
                        'refs/tags/2.0': {
                            'old': None,
                            'new': {'commit_sha1': sha1('refs/tags/2.0')}},
                    })})))
        with dbuser(config.IWebhookDeliveryJobSource.dbuser):
            self.assertEqual(
                "<WebhookDeliveryJob for webhook %d on %r>" % (
                    hook.id, hook.target),
                repr(delivery))

    def test_merge_detection_triggers_webhooks(self):
        self.useFixture(FeatureFixture(
            {BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG: 'on'}))
        repository = self.factory.makeGitRepository()
        target, source = self.factory.makeGitRefs(
            repository, paths=['refs/heads/target', 'refs/heads/source'])
        bmp = self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=source)
        hook = self.factory.makeWebhook(
            target=repository, event_types=['merge-proposal:0.1'])
        new_refs = {
            target.path: {'object': {
                'sha1': '0' * 40,
                'type': 'commit',
                }},
            source.path: {'object': {
                'sha1': source.commit_sha1,
                'type': 'commit',
                }},
            }
        new_merges = {source.commit_sha1: '0' * 40}
        self.useFixture(GitHostingFixture(refs=new_refs, merges=new_merges))
        job = GitRefScanJob.create(repository)
        with dbuser('branchscanner'):
            JobRunner([job]).runAll()
        delivery = hook.deliveries.one()
        self.assertThat(
            delivery,
            MatchesStructure(
                event_type=Equals('merge-proposal:0.1'),
                payload=MatchesDict({
                    'merge_proposal': Equals(
                        canonical_url(bmp, force_local_path=True)),
                    'action': Equals('modified'),
                    'old': ContainsDict(
                        {'queue_status': Equals('Work in progress')}),
                    'new': ContainsDict({'queue_status': Equals('Merged')}),
                    })))
        with dbuser(config.IWebhookDeliveryJobSource.dbuser):
            self.assertEqual(
                "<WebhookDeliveryJob for webhook %d on %r>" % (
                    hook.id, hook.target),
                repr(delivery))

    def test_composeWebhookPayload(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository, paths=['refs/heads/master', 'refs/tags/1.0'])

        sha1 = lambda s: hashlib.sha1(s).hexdigest()
        new_refs = {
            'refs/heads/master': {
                'sha1': sha1('master-ng'),
                'type': 'commit'},
            'refs/tags/2.0': {
                'sha1': sha1('2.0'),
                'type': 'commit'},
            }
        removed_refs = ['refs/tags/1.0']
        payload = GitRefScanJob.composeWebhookPayload(
            repository, new_refs, removed_refs)
        self.assertEqual(
            {'git_repository': '/' + repository.unique_name,
             'git_repository_path': repository.unique_name,
             'ref_changes': {
                'refs/heads/master': {
                    'old': {'commit_sha1': sha1('refs/heads/master')},
                    'new': {'commit_sha1': sha1('master-ng')}},
                'refs/tags/1.0': {
                    'old': {'commit_sha1': sha1('refs/tags/1.0')},
                    'new': None},
                'refs/tags/2.0': {
                    'old': None,
                    'new': {'commit_sha1': sha1('2.0')}}}},
            payload)


class TestReclaimGitRepositorySpaceJob(TestCaseWithFactory):
    """Tests for `ReclaimGitRepositorySpaceJob`."""

    layer = ZopelessDatabaseLayer

    def test_provides_interface(self):
        # `ReclaimGitRepositorySpaceJob` objects provide
        # `IReclaimGitRepositorySpaceJob`.
        self.assertProvides(
            ReclaimGitRepositorySpaceJob.create("/~owner/+git/gone", "1"),
            IReclaimGitRepositorySpaceJob)

    def test___repr__(self):
        # `ReclaimGitRepositorySpaceJob` objects have an informative
        # __repr__.
        name = "/~owner/+git/gone"
        job = ReclaimGitRepositorySpaceJob.create(name, "1")
        self.assertEqual(
            "<ReclaimGitRepositorySpaceJob for %s>" % name, repr(job))

    def test_scheduled_in_future(self):
        # A freshly created ReclaimGitRepositorySpaceJob is scheduled to run
        # in a week's time.
        job = ReclaimGitRepositorySpaceJob.create("/~owner/+git/gone", "1")
        self.assertEqual(
            timedelta(days=7), job.job.scheduled_start - job.job.date_created)

    def test_stores_name_and_path(self):
        # An instance of ReclaimGitRepositorySpaceJob stores the name and
        # path of the repository that has been deleted.
        name = "/~owner/+git/gone"
        path = "1"
        job = ReclaimGitRepositorySpaceJob.create(name, path)
        self.assertEqual(name, job._cached_repository_name)
        self.assertEqual(path, job.repository_path)

    def makeJobReady(self, job):
        """Force `job` to be scheduled to run now.

        New `ReclaimGitRepositorySpaceJob`s are scheduled to run a week
        after creation, so to be able to test running the job we have to
        force them to be scheduled now.
        """
        removeSecurityProxy(job).job.scheduled_start = UTC_NOW

    def test_run(self):
        # Running a job to reclaim space sends a request to the hosting
        # service.
        hosting_fixture = self.useFixture(GitHostingFixture())
        name = "/~owner/+git/gone"
        path = "1"
        job = ReclaimGitRepositorySpaceJob.create(name, path)
        self.makeJobReady(job)
        [job] = list(ReclaimGitRepositorySpaceJob.iterReady())
        with dbuser("branchscanner"):
            JobRunner([job]).runAll()
        self.assertEqual([(path,)], hosting_fixture.delete.extract_args())


class TestDescribeRepositoryDelta(TestCaseWithFactory):
    """Tests for `describe_repository_delta`."""

    layer = ZopelessDatabaseLayer

    def assertDeltaDescriptionEqual(self, expected, snapshot, repository):
        repository_delta = GitRepositoryDelta.construct(
            snapshot, repository, repository.owner)
        self.assertEqual(
            "\n".join("    %s" % line for line in expected),
            describe_repository_delta(repository_delta))

    def test_change_basic_properties(self):
        repository = self.factory.makeGitRepository(name="foo")
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        with person_logged_in(repository.owner):
            repository.setName("bar", repository.owner)
        expected = [
            "Name: foo => bar",
            "Git identity: lp:~{person}/{project}/+git/foo => "
            "lp:~{person}/{project}/+git/bar".format(
                person=repository.owner.name, project=repository.target.name),
            ]
        self.assertDeltaDescriptionEqual(expected, snapshot, repository)

    def test_add_rule(self):
        repository = self.factory.makeGitRepository()
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        with person_logged_in(repository.owner):
            repository.addRule("refs/heads/*", repository.owner)
        self.assertDeltaDescriptionEqual(
            ["Added protected ref: refs/heads/*"], snapshot, repository)

    def test_change_rule(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/foo")
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        rule_snapshot = Snapshot(rule, providing=providedBy(rule))
        with person_logged_in(repository.owner):
            rule.ref_pattern = "refs/heads/bar"
            notify(ObjectModifiedEvent(rule, rule_snapshot, ["ref_pattern"]))
        self.assertDeltaDescriptionEqual(
            ["Changed protected ref: refs/heads/foo => refs/heads/bar"],
            snapshot, repository)

    def test_remove_rule(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        with person_logged_in(repository.owner):
            rule.destroySelf(repository.owner)
        self.assertDeltaDescriptionEqual(
            ["Removed protected ref: refs/heads/*"], snapshot, repository)

    def test_add_grant(self):
        repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        with person_logged_in(repository.owner):
            rule.addGrant(
                GitGranteeType.REPOSITORY_OWNER, repository.owner,
                can_create=True, can_push=True, can_force_push=True)
        self.assertDeltaDescriptionEqual(
            ["Added access for repository owner to refs/heads/*: "
             "create, push, and force-push"],
            snapshot, repository)

    def test_change_grant(self):
        repository = self.factory.makeGitRepository()
        grant = self.factory.makeGitGrant(
            repository=repository, ref_pattern="refs/heads/*",
            can_create=True)
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        grant_snapshot = Snapshot(grant, providing=providedBy(grant))
        with person_logged_in(repository.owner):
            grant.can_push = True
            notify(ObjectModifiedEvent(grant, grant_snapshot, ["can_push"]))
        self.assertDeltaDescriptionEqual(
            ["Changed access for ~{grantee} to refs/heads/*: "
             "create => create and push".format(grantee=grant.grantee.name)],
            snapshot, repository)

    def test_remove_grant(self):
        repository = self.factory.makeGitRepository()
        grant = self.factory.makeGitGrant(
            repository=repository, ref_pattern="refs/heads/*",
            grantee=GitGranteeType.REPOSITORY_OWNER, can_push=True)
        transaction.commit()
        snapshot = Snapshot(repository, providing=providedBy(repository))
        with person_logged_in(repository.owner):
            grant.destroySelf(repository.owner)
        self.assertDeltaDescriptionEqual(
            ["Removed access for repository owner to refs/heads/*: push"],
            snapshot, repository)


# XXX cjwatson 2015-03-12: We should test that the jobs work via Celery too,
# but that isn't feasible until we have a proper turnip fixture.
