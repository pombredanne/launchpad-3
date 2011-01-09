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

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.enums import (
    BinaryPackageFormat,
    PackagePublishingPriority,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestBuild(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuild, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self.pf = self.factory.makeProcessorFamily()
        pf_proc = self.pf.addProcessor(self.factory.getUniqueString(), '', '')
        self.distroseries = self.factory.makeDistroSeries()
        self.das = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf,
            supports_virtualized=True)
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder = self.factory.makeBuilder(processor=pf_proc)

    def test_title(self):
        # A build has a title which describes the context source version and
        # in which series and architecture it is targeted for.
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        expected_title = '%s build of %s %s in %s %s RELEASE' % (
            self.das.architecturetag, spph.source_package_name,
            spph.source_package_version, self.distroseries.distribution.name,
            self.distroseries.name)
        self.assertEquals(build.title, expected_title)

    def test_linking(self):
        # A build directly links to the archive, distribution, distroseries,
        # distroarchseries, pocket in its context and also the source version
        # that generated it.
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        self.assertEquals(build.archive, self.distroseries.main_archive)
        self.assertEquals(build.distribution, self.distroseries.distribution)
        self.assertEquals(build.distro_series, self.distroseries)
        self.assertEquals(build.distro_arch_series, self.das)
        self.assertEquals(build.pocket, PackagePublishingPocket.RELEASE)
        self.assertEquals(build.arch_tag, self.das.architecturetag)
        self.assertTrue(build.is_virtualized)
        self.assertEquals(
            build.source_package_release.title, '%s - %s' % (
                spph.source_package_name, spph.source_package_version))

    def test_processed_builds(self):
        # Builds which were already processed also offer additional
        # information about its process such as the time it was started and
        # finished and its 'log' and 'upload_changesfile' as librarian files.
        spn=self.factory.getUniqueString()
        version="%s.1" % self.factory.getUniqueInteger()
        spph = self.publisher.getPubSource(
            sourcename=spn, version=version,
            distroseries=self.distroseries,
            status=PackagePublishingStatus.PUBLISHED)
        with person_logged_in(self.admin):
            binary = self.publisher.getPubBinaries(binaryname=spn,
                distroseries=self.distroseries, pub_source=spph,
                version=version, builder=self.builder)
        build = binary[0].binarypackagerelease.build
        self.assertTrue(build.was_built)
        self.assertEquals(
            build.package_upload.status, PackageUploadStatus.DONE)
        self.assertEquals(
            build.date_started, datetime(
                2008, 01, 01, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEquals(
            build.date_finished, datetime(
                2008, 01, 01, 0, 5, 0, tzinfo=pytz.UTC))
        self.assertEquals(build.duration, timedelta(minutes=5))
        expected_buildlog = 'buildlog_%s-%s-%s.%s_%s_FULLYBUILT.txt.gz' % (
            self.distroseries.distribution.name, self.distroseries.name,
            self.das.architecturetag, spn, version)
        self.assertEquals(build.log.filename, expected_buildlog)
        url_start = (
            'http://launchpad.dev/%s/+source/%s/%s/+build/%s/+files' % (
                self.distroseries.distribution.name, spn, version, build.id))
        expected_buildlog_url = '%s/%s' % (url_start, expected_buildlog)
        self.assertEquals(build.log_url, expected_buildlog_url)
        expected_changesfile = '%s_%s_%s.changes' % (
            spn, version, self.das.architecturetag)
        self.assertEquals(
            build.upload_changesfile.filename, expected_changesfile)
        expected_changesfile_url = '%s/%s' % (url_start, expected_changesfile)
        self.assertEquals(build.changesfile_url, expected_changesfile_url)
        # Since this build was sucessful, it can not be retried
        self.assertFalse(build.can_be_retried)

    def test_current_component(self):
        # The currently published component is provided via the
        # 'current_component' property.  It looks over the publishing records
        # and finds the current publication of the source in question.
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        self.assertEquals(build.current_component.name, 'main')
        # It may not be the same as
        self.assertEquals(build.source_package_release.component.name, 'main')
        # If the package has no uploads, its package_upload is None
        self.assertEquals(build.package_upload, None)

    def test_retry_for_released_series(self):
        # Builds can not be retried for released distroseries
        distroseries = self.factory.makeDistroSeries()
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, processorfamily=self.pf,
            supports_virtualized=True)
        with person_logged_in(self.admin):
            distroseries.nominatedarchindep = das
            distroseries.status = SeriesStatus.OBSOLETE
            self.publisher.addFakeChroots(distroseries=distroseries)
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=distroseries)
        [build] = spph.createMissingBuilds()
        self.assertFalse(build.can_be_retried)

    def test_retry(self):
        # Test retry functionality
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        with person_logged_in(self.admin):
            build.status = BuildStatus.FAILEDTOBUILD
        self.assertTrue(build.can_be_retried)

    def test_uploadlog(self):
        # Test if the upload log can be attached to a build.
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        self.assertEquals(build.upload_log, None)
        self.assertEquals(build.upload_log_url, None)
        build.storeUploadLog('sample upload log')
        expected_filename = 'upload_%s_log.txt' % build.id
        self.assertEquals(build.upload_log.filename, expected_filename)
        url_start = (
            'http://launchpad.dev/%s/+source/%s/%s/+build/%s/+files' % (
                self.distroseries.distribution.name, spph.source_package_name,
                spph.source_package_version, build.id))
        expected_url = '%s/%s' % (url_start, expected_filename)
        self.assertEquals(build.upload_log_url, expected_url)
        
    def test_retry_does_not_modify_first_dispatch(self):
        # Retrying a build does not modify the first dispatch time of the
        # build
        spph = self.publisher.getPubSource(
            sourcename=self.factory.getUniqueString(),
            version="%s.1" % self.factory.getUniqueInteger(),
            distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        now = datetime.now(pytz.UTC)
        with person_logged_in(self.admin):
            build.status = BuildStatus.FAILEDTOBUILD
            # The build can't be queued if we're going to retry it
            build.buildqueue_record.destroySelf()
        removeSecurityProxy(build).date_first_dispatched = now
        with person_logged_in(self.admin):
            build.retry()
        self.assertEquals(build.status, BuildStatus.NEEDSBUILD)
        self.assertEquals(build.date_first_dispatched, now)
        self.assertEquals(build.log, None)
        self.assertEquals(build.upload_log, None)

    def test_create_bpr(self):
        # Test that we can create a BPR from a given build.
        spn = self.factory.getUniqueString()
        version = "%s.1" % self.factory.getUniqueInteger()
        bpn = self.factory.makeBinaryPackageName(name=spn)
        spph = self.publisher.getPubSource(
            sourcename=spn, version=version, distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        binary = build.createBinaryPackageRelease(
            binarypackagename=bpn, version=version, summary='',
            description='', binpackageformat=BinaryPackageFormat.DEB,
            component=spph.sourcepackagerelease.component.id,
            section=spph.sourcepackagerelease.section.id,
            priority=PackagePublishingPriority.STANDARD, installedsize=0,
            architecturespecific=False)
        self.assertEquals(build.binarypackages.count(), 1)
        self.assertEquals(list(build.binarypackages), [binary])

    def test_multiple_create_bpr(self):
        # Test that we can create multiple BPRs from a given build
        spn = self.factory.getUniqueString()
        version = "%s.1" % self.factory.getUniqueInteger()
        spph = self.publisher.getPubSource(
            sourcename=spn, version=version, distroseries=self.distroseries)
        [build] = spph.createMissingBuilds()
        expected_names = []
        for i in range(15):
            bpn_name = '%s-%s' % (spn, i)
            bpn = self.factory.makeBinaryPackageName(bpn_name)
            expected_names.append(bpn_name)
            binary = build.createBinaryPackageRelease(
                binarypackagename=bpn, version=str(i), summary='',
                description='', binpackageformat=BinaryPackageFormat.DEB,
                component=spph.sourcepackagerelease.component.id,
                section=spph.sourcepackagerelease.section.id,
                priority=PackagePublishingPriority.STANDARD, installedsize=0,
                architecturespecific=False)
        self.assertEquals(build.binarypackages.count(), 15)
        bin_names = [b.name for b in build.binarypackages]
        # Verify .binarypackages returns sorted by name
        expected_names.sort()
        self.assertEquals(bin_names, expected_names)
