# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

"""Tests for BinaryPackageBuildBehavior."""

__metaclass__ = type

import transaction

from twisted.internet import defer
from twisted.trial import unittest as trialtest

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing import TwistedLaunchpadZopelessLayer

from lp.buildmaster.tests.mock_slaves import OkSlave
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    )
from lp.testing import (
    ANONYMOUS,
    login_as,
    logout,
    )
from lp.testing.factory import LaunchpadObjectFactory


class TestBinaryBuildPackageBehavior(trialtest.TestCase):
    """Tests for the BinaryPackageBuildBehavior.

    In particular, these tests are about how the BinaryPackageBuildBehavior
    interacts with the build slave.  We test this by using a test double that
    implements the same interface as `BuilderSlave` but instead of actually
    making XML-RPC calls, just records any method invocations along with
    interesting parameters.
    """

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        super(TestBinaryBuildPackageBehavior, self).setUp()
        self.factory = LaunchpadObjectFactory()
        login_as(ANONYMOUS)
        self.addCleanup(logout)
        self.layer.switchDbUser('testadmin')

    def assertExpectedInteraction(self, ignored, call_log, builder, build,
                                  chroot, archive, archive_purpose, component,
                                  extra_urls=None, filemap_names=None):
        expected = self.makeExpectedInteraction(
            builder, build, chroot, archive, archive_purpose, component,
            extra_urls, filemap_names)
        self.assertEqual(call_log, expected)

    def makeExpectedInteraction(self, builder, build, chroot, archive,
                                archive_purpose, component,
                                extra_urls=None, filemap_names=None):
        """Build the log of calls that we expect to be made to the slave.

        :param builder: The builder we are using to build the binary package.
        :param build: The build being done on the builder.
        :param chroot: The `LibraryFileAlias` for the chroot in which we are
            building.
        :param archive: The `IArchive` into which we are building.
        :param archive_purpose: The ArchivePurpose we are sending to the
            builder. We specify this separately from the archive because
            sometimes the behavior object has to give a different purpose
            in order to trick the slave into building correctly.
        :return: A list of the calls we expect to be made.
        """
        job = removeSecurityProxy(builder.current_build_behavior).buildfarmjob
        build_id = job.generateSlaveBuildCookie()
        ds_name = build.distro_arch_series.distroseries.name
        suite = ds_name + pocketsuffix[build.pocket]
        archives = get_sources_list_for_building(
            build, build.distro_arch_series,
            build.source_package_release.name)
        arch_indep = build.distro_arch_series.isNominatedArchIndep
        if filemap_names is None:
            filemap_names = []
        if extra_urls is None:
            extra_urls = []

        upload_logs = [
            ('ensurepresent', url, '', '')
            for url in [chroot.http_url] + extra_urls]

        extra_args = {
            'arch_indep': arch_indep,
            'arch_tag': build.distro_arch_series.architecturetag,
            'archive_private': archive.private,
            'archive_purpose': archive_purpose.name,
            'archives': archives,
            'build_debug_symbols': archive.build_debug_symbols,
            'ogrecomponent': component,
            'suite': suite,
            }
        build_log = [
            ('build', build_id, 'binarypackage', chroot.content.sha1,
             filemap_names, extra_args)]
        return upload_logs + build_log

    def startBuild(self, builder, candidate):
        builder = removeSecurityProxy(builder)
        candidate = removeSecurityProxy(candidate)
        return defer.maybeDeferred(
            builder.startBuild, candidate, QuietFakeLogger())

    def test_non_virtual_ppa_dispatch(self):
        # When the BinaryPackageBuildBehavior dispatches PPA builds to
        # non-virtual builders, it stores the chroot on the server and
        # requests a binary package build, lying to say that the archive
        # purpose is "PRIMARY" because this ensures that the package mangling
        # tools will run over the built packages.
        archive = self.factory.makeArchive(virtualized=False)
        slave = OkSlave()
        builder = self.factory.makeBuilder(virtualized=False)
        builder.setSlaveForTesting(slave)
        build = self.factory.makeBinaryPackageBuild(
            builder=builder, archive=archive)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        d = self.startBuild(builder, candidate)
        d.addCallback(
            self.assertExpectedInteraction, slave.call_log,
            builder, build, lf, archive, ArchivePurpose.PRIMARY, 'universe')
        return d

    def test_partner_dispatch_no_publishing_history(self):
        archive = self.factory.makeArchive(
            virtualized=False, purpose=ArchivePurpose.PARTNER)
        slave = OkSlave()
        builder = self.factory.makeBuilder(virtualized=False)
        builder.setSlaveForTesting(slave)
        build = self.factory.makeBinaryPackageBuild(
            builder=builder, archive=archive)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        d = self.startBuild(builder, candidate)
        d.addCallback(
            self.assertExpectedInteraction, slave.call_log,
            builder, build, lf, archive,
            ArchivePurpose.PARTNER, build.current_component.name)
        return d

    def test_dont_dispatch_release_builds(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        builder = self.factory.makeBuilder()
        distroseries = self.factory.makeDistroSeries(
            status=SeriesStatus.CURRENT, distribution=archive.distribution)
        distro_arch_series = self.factory.makeDistroArchSeries(
            distroseries=distroseries)
        build = self.factory.makeBinaryPackageBuild(
            builder=builder, archive=archive,
            distroarchseries=distro_arch_series,
            pocket=PackagePublishingPocket.RELEASE)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        behavior = candidate.required_build_behavior
        behavior.setBuilder(build)
        e = self.assertRaises(
            AssertionError, behavior.verifyBuildRequest, QuietFakeLogger())
        expected_message = (
            "%s (%s) can not be built for pocket %s: invalid pocket due "
            "to the series status of %s." % (
                build.title, build.id, build.pocket.name,
                build.distro_series.name))
        self.assertEqual(expected_message, str(e))

    def test_dont_dispatch_security_builds(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        builder = self.factory.makeBuilder()
        build = self.factory.makeBinaryPackageBuild(
            builder=builder, archive=archive,
            pocket=PackagePublishingPocket.SECURITY)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        behavior = candidate.required_build_behavior
        behavior.setBuilder(build)
        e = self.assertRaises(
            AssertionError, behavior.verifyBuildRequest, QuietFakeLogger())
        self.assertEqual(
            'Soyuz is not yet capable of building SECURITY uploads.',
            str(e))
