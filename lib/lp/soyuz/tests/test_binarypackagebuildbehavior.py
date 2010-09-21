# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

"""Tests for BinaryPackageBuildBehavior."""

__metaclass__ = type

from twisted.trial import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing import TwistedLaunchpadZopelessLayer

from lp.registry.interfaces.pocket import pocketsuffix
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.tests.soyuzbuilddhelpers import OkSlave
from lp.testing import (
    ANONYMOUS,
    login_as,
    logout,
    )
from lp.testing.factory import LaunchpadObjectFactory


class TestBinaryBuildPackageBehavior(unittest.TestCase):
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

    def assertSlaveInteraction(self, ignored, call_log, builder, build,
                               chroot, archive, archive_purpose):
        """Assert that 'call_log' matches our expectations of interaction.

        'call_log' is expected to be a recording from a test double slave like
        OkSlave or one its subclasses.  We assert that the calls in call_log
        match our expectations, thus showing that the binary package behaviour
        interacts with the slave in the way we expect.

        :param ignored: Ignored. This parameter here only to make it easier
            to use the assertion as a Twisted callback.
        :param call_log: A list of calls to a `BuilderSlave`-like object.
        :param builder: The builder we are using to build the binary package.
        :param build: The build being done on the builder.
        :param chroot: The `LibraryFileAlias` for the chroot in which we are
            building.
        :param archive: The `IArchive` into which we are building.
        :param archive_purpose: The ArchivePurpose we are sending to the
            builder. We specify this separately from the archive because
            sometimes the behavior object has to give a different purpose
            in order to trick the slave into building correctly.
        """
        job = removeSecurityProxy(builder.current_build_behavior).buildfarmjob
        build_id = job.generateSlaveBuildCookie()
        ds_name = build.distro_arch_series.distroseries.name
        suite = ds_name + pocketsuffix[build.pocket]
        archives = get_sources_list_for_building(
            build, build.distro_arch_series,
            build.source_package_release.name)
        expected = [
            'cacheFile',
            'sendFileToSlave',
            ('ensurepresent', chroot.http_url, '', ''),
            ('build', build_id, 'binarypackage', chroot.content.sha1, {},
             {'arch_indep': None,
              'arch_tag': build.distro_arch_series.architecturetag,
              'archive_private': archive.private,
              'archive_purpose': archive_purpose.name,
              'archives': archives,
              'build_debug_symbols': archive.build_debug_symbols,
              'ogrecomponent': 'universe',
              'suite': suite})]
        self.assertEqual(call_log, expected)

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
        self.layer.txn.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        # XXX: Maybe we should add Deferred to the zope.security.checkers.
        d = removeSecurityProxy(builder).startBuild(
            removeSecurityProxy(candidate), QuietFakeLogger())
        d.addCallback(
            self.assertSlaveInteraction,
            slave.call_log, builder, build, lf, archive,
            ArchivePurpose.PRIMARY)
        return d
