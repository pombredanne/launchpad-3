# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

"""Tests for BinaryPackageBuildBehavior."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from canonical.testing import TwistedLaunchpadZopelessLayer

from twisted.trial.unittest import TestCase


from lp.buildmaster.tests.test_builder import SlaveTestHelpers
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from lp.soyuz.model.publishing import BinaryPackagePublishingHistory
from lp.soyuz.model.queue import PackageUploadBuild
from lp.testing import (
    ANONYMOUS,
    login_as,
    logout,
    )
from lp.testing.factory import LaunchpadObjectFactory


class TestBinaryBuildPackageBehavior(TestCase):
    """Tests for the BinaryPackageBuildBehavior."""

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        super(TestBinaryBuildPackageBehavior, self).setUp()
        self.slave_helper = SlaveTestHelpers()
        self.slave_helper.setUp()
        self.addCleanup(self.slave_helper.cleanUp)
        self.factory = LaunchpadObjectFactory()
        login_as(ANONYMOUS)
        self.addCleanup(logout)
        self.layer.switchDbUser('testadmin')
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        store.find(BinaryPackagePublishingHistory).remove()
        store.find(BuildPackageJob).remove()
        store.find(PackageUploadBuild).remove()
        store.find(BinaryPackageBuild).remove()

    def test_smoke(self):
        self.slave_helper.getServerSlave()
        archive = self.factory.makeArchive(virtualized=False)
        slave = self.slave_helper.getClientSlave()
        builder = self.factory.makeBuilder(virtualized=False)
        builder.setSlaveForTesting(slave)
        build = self.factory.makeBinaryPackageBuild(
            builder=builder, archive=archive)
        lf = self.factory.makeLibraryFileAlias()
        self.layer.txn.commit()
        build.distro_arch_series.addOrUpdateChroot(lf)
        candidate = build.queueBuild()
        # Probably we should call startJob or something. Copy the doctest for
        # now.
        return removeSecurityProxy(builder)._dispatchBuildCandidate(candidate)
