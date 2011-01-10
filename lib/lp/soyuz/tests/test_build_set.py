# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from storm.store import EmptyResultSet

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    IBinaryPackageBuildSet,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL

class TestBuildSet(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildSet, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self.pf_one = self.factory.makeProcessorFamily()
        pf_proc_1 = self.pf_one.addProcessor(
            self.factory.getUniqueString(), '', '')
        self.pf_two = self.factory.makeProcessorFamily()
        pf_proc_2 = self.pf_two.addProcessor(
            self.factory.getUniqueString(), '', '')
        self.distroseries = self.factory.makeDistroSeries()
        self.distribution = self.distroseries.distribution
        self.das_one = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf_one,
            supports_virtualized=True)
        self.das_two = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf_two,
            supports_virtualized=True)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PRIMARY)
        self.arch_ids = [arch.id for arch in self.distroseries.architectures]
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das_one
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder_one = self.factory.makeBuilder(processor=pf_proc_1)
            self.builder_two = self.factory.makeBuilder(processor=pf_proc_2)
        self.builds = []
        for i in range(5):
            # Create some test builds
            spph = self.publisher.getPubSource(
                sourcename=self.factory.getUniqueString(),
                version="%s.%s" % (self.factory.getUniqueInteger(), i),
                distroseries=self.distroseries, architecturehintlist='any')
            builds = spph.createMissingBuilds()
            with person_logged_in(self.admin):
                for b in builds:
                    if i == 4:
                        b.status = BuildStatus.FAILEDTOBUILD
                    else:
                        b.status = BuildStatus.FULLYBUILT
                    b.buildqueue_record.destroySelf()
                    b.date_started = datetime.now(pytz.UTC)
                    b.date_finished = b.date_started + timedelta(minutes=5)
            self.builds += builds

    def test_get_by_spr(self):
        # Test fetching build records via the SPR
        spr = self.builds[0].source_package_release.id
        set = getUtility(IBinaryPackageBuildSet).getBuildBySRAndArchtag(
            spr, self.das_one.architecturetag)
        self.assertEquals(set.count(), 1)
        self.assertEquals(set[0], self.builds[0])

    def test_get_by_arch_ids(self):
        # Test fetching builds via the arch tag
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, self.arch_ids)
        for build in set:
            print build.title
        self.assertEquals(set.count(), 10)

    def test_get_by_no_arch_ids(self):
        # .getBuildsByArchIds still works if the list given is empty, or none
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, [])
        self.assertIsInstance(set, EmptyResultSet)
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, None)
        self.assertIsInstance(set, EmptyResultSet)

    def test_get_by_arch_ids_filter_build_status(self):
        # The result can be filtered based on the build status
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, self.arch_ids, status=BuildStatus.FULLYBUILT)
        self.assertEquals(set.count(), 8)

    def test_get_by_arch_ids_filter_name(self):
        # The result can be filtered based on the name
        spn = self.builds[2].source_package_release.sourcepackagename.name
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, self.arch_ids, name=spn)
        self.assertEquals(set.count(), 2)

    def test_get_by_arch_ids_filter_pocket(self):
        # The result can be filtered based on the pocket of the build
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, self.arch_ids,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEquals(set.count(), 10)
        set = getUtility(IBinaryPackageBuildSet).getBuildsByArchIds(
            self.distribution, self.arch_ids,
            pocket=PackagePublishingPocket.UPDATES)
        self.assertEquals(set.count(), 0)

    def test_get_status_summary_for_builds(self):
        # We can query for the status summary of a number of builds
        relevant_builds = [self.builds[0], self.builds[2], self.builds[-2]]
        summary = getUtility(
            IBinaryPackageBuildSet).getStatusSummaryForBuilds(
                relevant_builds)
        self.assertEquals(summary['status'], BuildSetStatus.FAILEDTOBUILD)
        self.assertEquals(summary['builds'], [self.builds[-2]])

    def test_preload_data(self):
        # The BuildSet class allows data to be preloaded
        # Note, it is an internal method, so we have to push past the security
        # proxy
        build_ids = [self.builds[i] for i in (0, 1, 2, 3)]
        rset = removeSecurityProxy(
            getUtility(IBinaryPackageBuildSet))._prefetchBuildData(build_ids)
        self.assertEquals(len(rset), 4)
