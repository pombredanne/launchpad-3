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
    MatchesSetwise,
    MatchesStructure,
    )

from lp.code.enums import GitObjectType
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    )
from lp.code.model.gitjob import (
    GitJob,
    GitJobDerived,
    GitJobType,
    GitRefScanJob,
    )
from lp.testing import (
    TestCaseWithFactory,
    time_counter,
    )
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


class TestGitRefScanJobMixin:

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


class TestGitRefScanJob(TestGitRefScanJobMixin, TestCaseWithFactory):
    """Tests for `GitRefScanJob`."""

    layer = LaunchpadZopelessLayer

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
        job._hosting_client.getRefs = FakeMethod(
            result=self.makeFakeRefs(paths))
        author = repository.owner
        author_date_start = datetime(2015, 01, 01, tzinfo=pytz.UTC)
        author_date_gen = time_counter(author_date_start, timedelta(days=1))
        job._hosting_client.getCommits = FakeMethod(
            result=self.makeFakeCommits(author, author_date_gen, paths))
        with dbuser("branchscanner"):
            job.run()
        self.assertRefsMatch(repository.refs, repository, paths)

    def test_logs_bad_ref_info(self):
        repository = self.factory.makeGitRepository()
        job = GitRefScanJob.create(repository)
        job._hosting_client.getRefs = FakeMethod(
            result={u"refs/heads/master": {}})
        job._hosting_client.getCommits = FakeMethod(result=[])
        expected_message = (
            'Unconvertible ref refs/heads/master {}: '
            'ref info does not contain "object" key')
        with self.expectedLog(expected_message):
            with dbuser("branchscanner"):
                job.run()
        self.assertEqual([], list(repository.refs))


# XXX cjwatson 2015-03-12: We should test that the job works via Celery too,
# but that isn't feasible until we have a proper turnip fixture.
