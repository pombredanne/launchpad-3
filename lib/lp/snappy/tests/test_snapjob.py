# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for snap package jobs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from textwrap import dedent

from testtools.matchers import (
    AfterPreprocessing,
    ContainsDict,
    Equals,
    Is,
    MatchesSetwise,
    MatchesStructure,
    )

from lp.code.tests.helpers import GitHostingFixture
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.mail.sendmail import format_address_for_person
from lp.snappy.interfaces.snap import CannotParseSnapcraftYaml
from lp.snappy.interfaces.snapjob import (
    ISnapJob,
    ISnapRequestBuildsJob,
    )
from lp.snappy.model.snapjob import (
    SnapJob,
    SnapJobType,
    SnapRequestBuildsJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import ZopelessDatabaseLayer


class TestSnapJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_provides_interface(self):
        # `SnapJob` objects provide `ISnapJob`.
        snap = self.factory.makeSnap()
        self.assertProvides(
            SnapJob(snap, SnapJobType.REQUEST_BUILDS, {}), ISnapJob)


class TestSnapRequestBuildsJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_provides_interface(self):
        # `SnapRequestBuildsJob` objects provide `ISnapRequestBuildsJob`."""
        snap = self.factory.makeSnap()
        archive = self.factory.makeArchive()
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, archive, PackagePublishingPocket.RELEASE,
            None)
        self.assertProvides(job, ISnapRequestBuildsJob)

    def test___repr__(self):
        # `SnapRequestBuildsJob` objects have an informative __repr__.
        snap = self.factory.makeSnap()
        archive = self.factory.makeArchive()
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, archive, PackagePublishingPocket.RELEASE,
            None)
        self.assertEqual(
            "<SnapRequestBuildsJob for ~%s/+snap/%s>" % (
                snap.owner.name, snap.name),
            repr(job))

    def makeSeriesAndProcessors(self, arch_tags):
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        processors = [
            self.factory.makeProcessor(
                name=arch_tag, supports_virtualized=True)
            for arch_tag in arch_tags]
        for processor in processors:
            das = self.factory.makeDistroArchSeries(
                distroseries=distroseries, architecturetag=processor.name,
                processor=processor)
            das.addOrUpdateChroot(self.factory.makeLibraryFileAlias(
                filename="fake_chroot.tar.gz", db_only=True))
        return distroseries, processors

    def test_run(self):
        # The job requests builds and records the result.
        distroseries, processors = self.makeSeriesAndProcessors(
            ["avr2001", "sparc64", "x32"])
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(
            git_ref=git_ref, distroseries=distroseries, processors=processors)
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, distroseries.main_archive,
            PackagePublishingPocket.RELEASE, {"core": "stable"})
        snapcraft_yaml = dedent("""\
            architectures:
              - build-on: avr2001
              - build-on: x32
            """)
        self.useFixture(GitHostingFixture(blob=snapcraft_yaml))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEmailQueueLength(0)
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.COMPLETED),
            error_message=Is(None),
            builds=AfterPreprocessing(set, MatchesSetwise(*[
                MatchesStructure.byEquality(
                    requester=snap.registrant,
                    snap=snap,
                    archive=distroseries.main_archive,
                    distro_arch_series=distroseries[arch],
                    pocket=PackagePublishingPocket.RELEASE,
                    channels={"core": "stable"})
                for arch in ("avr2001", "x32")]))))

    def test_run_failed(self):
        # A failed run sets the job status to FAILED and records the error
        # message.
        # The job requests builds and records the result.
        distroseries, processors = self.makeSeriesAndProcessors(
            ["avr2001", "sparc64", "x32"])
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(
            git_ref=git_ref, distroseries=distroseries, processors=processors)
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, distroseries.main_archive,
            PackagePublishingPocket.RELEASE, {"core": "stable"})
        self.useFixture(GitHostingFixture()).getBlob.failure = (
            CannotParseSnapcraftYaml("Nonsense on stilts"))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        [notification] = self.assertEmailQueueLength(1)
        self.assertThat(dict(notification), ContainsDict({
            "From": Equals(config.canonical.noreply_from_address),
            "To": Equals(format_address_for_person(snap.registrant)),
            "Subject": Equals(
                "Launchpad error while requesting builds of %s" % snap.name),
            }))
        self.assertEqual(
            "Launchpad encountered an error during the following operation: "
            "requesting builds of %s.  Nonsense on stilts" % snap.name,
            notification.get_payload(decode=True))
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.FAILED),
            error_message=Equals("Nonsense on stilts"),
            builds=AfterPreprocessing(set, MatchesSetwise())))
