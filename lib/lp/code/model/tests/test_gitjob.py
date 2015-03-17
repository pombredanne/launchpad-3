# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `GitJob`s."""

__metaclass__ = type

import hashlib

from testtools.matchers import (
    MatchesSetwise,
    MatchesStructure,
    )

from lp.code.enums import GitObjectType
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    )
from lp.code.interfaces.gitrepository import GIT_FEATURE_FLAG
from lp.code.model.gitjob import (
    GitJob,
    GitJobDerived,
    GitJobType,
    GitRefScanJob,
    )
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestGitJob(TestCaseWithFactory):
    """Tests for `GitJob`."""

    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        # `GitJob` objects provide `IGitJob`.
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
        repository = self.factory.makeGitRepository()
        self.assertProvides(
            GitJob(repository, GitJobType.REF_SCAN, {}), IGitJob)


class TestGitJobDerived(TestCaseWithFactory):
    """Tests for `GitJobDerived`."""

    layer = LaunchpadZopelessLayer

    def test_getOopsMailController(self):
        """By default, no mail is sent about failed BranchJobs."""
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
        repository = self.factory.makeGitRepository()
        job = GitJob(repository, GitJobType.REF_SCAN, {})
        derived = GitJobDerived(job)
        self.assertIsNone(derived.getOopsMailController("x"))


class TestGitRefScanJobMixin:

    @staticmethod
    def makeFakeRefs(paths):
        return dict(
            (path, {"object": {
                "sha1": hashlib.sha1(path).hexdigest(),
                "type": "commit",
                }})
            for path in paths)

    def assertRefsMatch(self, refs, repository, paths):
        matchers = [
            MatchesStructure.byEquality(
                repository=repository,
                path=path,
                commit_sha1=unicode(hashlib.sha1(path).hexdigest()),
                object_type=GitObjectType.COMMIT)
            for path in paths]
        self.assertThat(refs, MatchesSetwise(*matchers))


class TestGitRefScanJob(TestGitRefScanJobMixin, TestCaseWithFactory):
    """Tests for `GitRefScanJob`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGitRefScanJob, self).setUp()
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))

    def test_provides_interface(self):
        # `GitRefScanJob` objects provide `IGitRefScanJob`.
        repository = self.factory.makeGitRepository()
        self.assertProvides(GitRefScanJob.create(repository), IGitRefScanJob)

    def test_run(self):
        # Ensure the job scans the repository.
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        paths = (u"refs/heads/master", u"refs/tags/1.0")
        job._hosting_client.get_refs = FakeMethod(
            result=self.makeFakeRefs(paths))
        with dbuser("branchscanner"):
            job.run()
        self.assertRefsMatch(repository.refs, repository, paths)

    def test_logs_bad_ref_info(self):
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        job._hosting_client.get_refs = FakeMethod(
            result={u"refs/heads/master": {}})
        expected_message = (
            'Unconvertible ref refs/heads/master {}: '
            'ref info does not contain "object" key')
        with self.expectedLog(expected_message):
            with dbuser("branchscanner"):
                job.run()
        self.assertEqual([], repository.refs)


# XXX cjwatson 2015-03-12: We should test that the job works via Celery too,
# but that isn't feasible until we have a proper turnip fixture.
