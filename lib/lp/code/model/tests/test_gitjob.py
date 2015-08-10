# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `GitJob`s."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import hashlib

import pytz
from testtools.matchers import (
    Equals,
    MatchesDict,
    MatchesSetwise,
    MatchesStructure,
    )
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import GitObjectType
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    IReclaimGitRepositorySpaceJob,
    )
from lp.code.model.gitjob import (
    GitJob,
    GitJobDerived,
    GitJobType,
    GitRefScanJob,
    ReclaimGitRepositorySpaceJob,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.job.runner import JobRunner
from lp.testing import (
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


@implementer(IGitHostingClient)
class FakeGitHostingClient:

    def __init__(self, refs, commits, default_branch=u"refs/heads/master"):
        self._refs = refs
        self._commits = commits
        self._default_branch = default_branch

    def getRefs(self, paths):
        return self._refs

    def getCommits(self, path, commit_oids, logger=None):
        return self._commits

    def getProperties(self, path):
        return {u"default_branch": self._default_branch}


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

    layer = LaunchpadZopelessLayer

    def test_getOopsMailController(self):
        """By default, no mail is sent about failed BranchJobs."""
        repository = self.factory.makeGitRepository()
        job = GitJob(repository, GitJobType.REF_SCAN, {})
        derived = GitJobDerived(job)
        self.assertIsNone(derived.getOopsMailController("x"))


class TestGitRefScanJob(TestCaseWithFactory):
    """Tests for `GitRefScanJob`."""

    layer = LaunchpadZopelessLayer

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
            "sha1": hashlib.sha1(path).hexdigest(),
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
            "tree": hashlib.sha1("").hexdigest(),
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
        paths = (u"refs/heads/master", u"refs/tags/1.0")
        author = repository.owner
        author_date_start = datetime(2015, 01, 01, tzinfo=pytz.UTC)
        author_date_gen = time_counter(author_date_start, timedelta(days=1))
        hosting_client = FakeGitHostingClient(
            self.makeFakeRefs(paths),
            self.makeFakeCommits(author, author_date_gen, paths))
        self.useFixture(ZopeUtilityFixture(hosting_client, IGitHostingClient))
        with dbuser("branchscanner"):
            JobRunner([job]).runAll()
        self.assertRefsMatch(repository.refs, repository, paths)
        self.assertEqual(u"refs/heads/master", repository.default_branch)

    def test_logs_bad_ref_info(self):
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        hosting_client = FakeGitHostingClient({u"refs/heads/master": {}}, [])
        self.useFixture(ZopeUtilityFixture(hosting_client, IGitHostingClient))
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
            repository, paths=[u'refs/heads/master', u'refs/tags/1.0'])
        hook = self.factory.makeWebhook(
            target=repository, event_types=['git:push:0.1'])
        job = GitRefScanJob.create(repository)
        paths = (u'refs/heads/master', u'refs/tags/2.0')
        hosting_client = FakeGitHostingClient(self.makeFakeRefs(paths), [])
        self.useFixture(ZopeUtilityFixture(hosting_client, IGitHostingClient))
        with dbuser('branchscanner'):
            JobRunner([job]).runAll()
        delivery = hook.deliveries.one()
        sha1 = lambda s: hashlib.sha1(s).hexdigest()
        self.assertThat(
            delivery,
            MatchesStructure(
                event_type=Equals('git:push:0.1'),
                payload=MatchesDict({
                    'git_repository': Equals(repository.unique_name),
                    'changes': Equals({
                        'refs/tags/1.0': {
                            'old': {'commit_sha1': sha1('refs/tags/1.0')},
                            'new': None},
                        'refs/tags/2.0': {
                            'old': None,
                            'new': {'commit_sha1': sha1('refs/tags/2.0')}},
                    })})))

    def test_composeWebhookPayload(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository, paths=[u'refs/heads/master', u'refs/tags/1.0'])

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
            {'git_repository': repository.unique_name,
             'changes': {
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

    layer = LaunchpadZopelessLayer

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
        hosting_client = FakeGitHostingClient({}, [])
        self.useFixture(ZopeUtilityFixture(hosting_client, IGitHostingClient))
        name = "/~owner/+git/gone"
        path = "1"
        job = ReclaimGitRepositorySpaceJob.create(name, path)
        self.makeJobReady(job)
        [job] = list(ReclaimGitRepositorySpaceJob.iterReady())
        with dbuser("branchscanner"):
            hosting_client.delete = FakeMethod()
            JobRunner([job]).runAll()
        self.assertEqual([(path,)], hosting_client.delete.extract_args())


# XXX cjwatson 2015-03-12: We should test that the jobs work via Celery too,
# but that isn't feasible until we have a proper turnip fixture.
