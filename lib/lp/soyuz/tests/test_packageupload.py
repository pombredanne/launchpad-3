# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

from datetime import timedelta
from email import message_from_string
import os
import shutil

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archiveuploader.tests import datadir
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.job.interfaces.job import JobStatus
from lp.services.log.logger import BufferLogger
from lp.services.mail import stub
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet,
    QueueInconsistentStateError,
    )
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.matchers import Provides


class PackageUploadTestCase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        super(PackageUploadTestCase, self).setUp()
        self.test_publisher = SoyuzTestPublisher()

    def createEmptyDelayedCopy(self):
        ubuntutest = getUtility(IDistributionSet).getByName('ubuntutest')
        return getUtility(IPackageUploadSet).createDelayedCopy(
            ubuntutest.main_archive,
            ubuntutest.getSeries('breezy-autotest'),
            PackagePublishingPocket.SECURITY,
            None)

    def test_acceptFromUpload_refuses_delayed_copies(self):
        # Delayed-copies cannot be accepted via acceptFromUploader.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Cannot process delayed copies.',
            delayed_copy.acceptFromUploader, 'some-path')

    def test_acceptFromQueue_refuses_delayed_copies(self):
        # Delayed-copies cannot be accepted via acceptFromQueue.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Cannot process delayed copies.', delayed_copy.acceptFromQueue)

    def test_acceptFromCopy_refuses_empty_copies(self):
        # Empty delayed-copies cannot be accepted.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Source is mandatory for delayed copies.',
            delayed_copy.acceptFromCopy)

    def createDelayedCopy(self, source_only=False):
        """Return a delayed-copy targeted to ubuntutest/breezy-autotest.

        The delayed-copy is targeted to the SECURITY pocket with:

          * source foo - 1.1

        And if 'source_only' is False, the default behavior, also attach:

          * binaries foo - 1.1 in i386 and hppa
          * a DIST_UPGRADER custom file

        All files are restricted.
        """
        self.test_publisher.prepareBreezyAutotest()
        ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        ppa.buildd_secret = 'x'
        ppa.private = True

        changesfile_path = (
            'lib/lp/archiveuploader/tests/data/suite/'
            'foocomm_1.0-2_binary/foocomm_1.0-2_i386.changes')

        changesfile_content = ''
        handle = open(changesfile_path, 'r')
        try:
            changesfile_content = handle.read()
        finally:
            handle.close()

        source = self.test_publisher.getPubSource(
            sourcename='foocomm', archive=ppa, version='1.0-2',
            changes_file_content=changesfile_content)
        delayed_copy = getUtility(IPackageUploadSet).createDelayedCopy(
            self.test_publisher.ubuntutest.main_archive,
            self.test_publisher.breezy_autotest,
            PackagePublishingPocket.SECURITY,
            self.test_publisher.person.gpg_keys[0])

        delayed_copy.addSource(source.sourcepackagerelease)

        announce_list = delayed_copy.distroseries.changeslist
        if announce_list is None or len(announce_list.strip()) == 0:
            announce_list = ('%s-changes@lists.ubuntu.com' %
                             delayed_copy.distroseries.name)
            delayed_copy.distroseries.changeslist = announce_list

        if not source_only:
            self.test_publisher.getPubBinaries(pub_source=source)
            custom_path = datadir(
                'dist-upgrader/dist-upgrader_20060302.0120_all.tar.gz')
            custom_file = self.factory.makeLibraryFileAlias(
                filename='dist-upgrader_20060302.0120_all.tar.gz',
                content=open(custom_path).read(), restricted=True)
            [build] = source.getBuilds()
            build.package_upload.addCustom(
                custom_file, PackageUploadCustomFormat.DIST_UPGRADER)
            for build in source.getBuilds():
                delayed_copy.addBuild(build)
                for custom in build.package_upload.customfiles:
                    delayed_copy.addCustom(
                        custom.libraryfilealias, custom.customformat)

        # Commit for using just-created library files.
        self.layer.txn.commit()

        return delayed_copy

    def checkDelayedCopyPubRecord(self, pub_record, archive, pocket,
                                  component, restricted):
        """Ensure the given publication are in the expected state.

        It should be a PENDING publication to the specified context and
        its files should match the specifed privacy.
        """
        self.assertEquals(PackagePublishingStatus.PENDING, pub_record.status)
        self.assertEquals(archive, pub_record.archive)
        self.assertEquals(pocket, pub_record.pocket)
        self.assertEquals(component, pub_record.component)
        for pub_file in pub_record.files:
            self.assertEqual(
                restricted, pub_file.libraryfilealias.restricted)

    def removeRepository(self, distro):
        """Remove the testing repository root if it exists."""
        root = getUtility(
            IPublisherConfigSet).getByDistribution(distro).root_dir
        if os.path.exists(root):
            shutil.rmtree(root)

    def test_realiseUpload_for_delayed_copies(self):
        # Delayed-copies result in published records that were overridden
        # and has their files privacy adjusted according test destination
        # context.

        # Create the default delayed-copy context.
        delayed_copy = self.createDelayedCopy()

        # Add a cleanup for removing the repository where the custom upload
        # was published.
        self.addCleanup(
            self.removeRepository,
            self.test_publisher.breezy_autotest.distribution)

        # Delayed-copies targeted to unreleased pockets cannot be accepted.
        self.assertRaisesWithContent(
            AssertionError,
            "Not permitted acceptance in the SECURITY pocket in a series "
            "in the 'EXPERIMENTAL' state.",
            delayed_copy.acceptFromCopy)

        # Release ubuntutest/breezy-autotest, so delayed-copies to
        # SECURITY pocket can be accepted.
        self.test_publisher.breezy_autotest.status = (
            SeriesStatus.CURRENT)

        # Create an ancestry publication in 'multiverse'.
        ancestry_source = self.test_publisher.getPubSource(
            sourcename='foocomm', version='1.0', component='multiverse',
            status=PackagePublishingStatus.PUBLISHED)
        self.test_publisher.getPubBinaries(
            pub_source=ancestry_source,
            status=PackagePublishingStatus.PUBLISHED)
        package_diff = ancestry_source.sourcepackagerelease.requestDiffTo(
            requester=self.test_publisher.person,
            to_sourcepackagerelease=delayed_copy.sourcepackagerelease)
        package_diff.diff_content = self.factory.makeLibraryFileAlias(
            restricted=True)

        # Accept and publish the delayed-copy.
        delayed_copy.acceptFromCopy()
        self.assertEquals(
            PackageUploadStatus.ACCEPTED, delayed_copy.status)

        # Make sure no announcement email was sent at this point.
        self.assertEquals(len(stub.test_emails), 0)

        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)

        logger = BufferLogger()
        # realiseUpload() assumes a umask of 022, which is normally true in
        # production.  The user's environment might have a different umask, so
        # just force it to what the test expects.
        old_umask = os.umask(022)

        try:
            pub_records = delayed_copy.realiseUpload(logger=logger)
        finally:
            os.umask(old_umask)
        self.assertEquals(
            PackageUploadStatus.DONE, delayed_copy.status)

        self.layer.txn.commit()

        # Check the announcement email.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = message_from_string(raw_msg)
        body = msg.get_payload(0)
        body = body.get_payload(decode=True)

        self.assertEquals(
            str(to_addrs), "['breezy-autotest-changes@lists.ubuntu.com']")

        expected_subject = (
            '[ubuntutest/breezy-autotest-security]\n\t'
            'dist-upgrader_20060302.0120_all.tar.gz, '
            'foocomm 1.0-2 (Accepted)')
        self.assertEquals(msg['Subject'], expected_subject)

        self.assertEquals(body,
            'foocomm (1.0-2) breezy; urgency=low\n\n'
            '  * Initial version\n\n'
            'Date: Thu, 16 Feb 2006 15:34:09 +0000\n'
            'Changed-By: Foo Bar <foo.bar@canonical.com>\n'
            'Maintainer: Launchpad team <launchpad@lists.canonical.com>\n'
            'http://launchpad.dev/ubuntutest/breezy-autotest/+source/'
            'foocomm/1.0-2\n')

        self.layer.switchDbUser('launchpad')

        # One source and 2 binaries are pending publication. They all were
        # overridden to multiverse and had their files moved to the public
        # librarian.
        self.assertEquals(3, len(pub_records))
        self.assertEquals(
            set([
                u'foocomm 1.0-2 in breezy-autotest',
                u'foo-bin 1.0-2 in breezy-autotest hppa',
                u'foo-bin 1.0-2 in breezy-autotest i386']),
            set([pub.displayname for pub in pub_records]))

        for pub_record in pub_records:
            self.checkDelayedCopyPubRecord(
                pub_record, delayed_copy.archive, delayed_copy.pocket,
                ancestry_source.component, False)

        # The package diff file is now public.
        self.assertFalse(package_diff.diff_content.restricted)

        # The custom file was also published.
        root_dir = getUtility(IPublisherConfigSet).getByDistribution(
            self.test_publisher.breezy_autotest.distribution).root_dir
        custom_path = os.path.join(
            root_dir,
            'ubuntutest/dists/breezy-autotest-security',
            'main/dist-upgrader-all')
        self.assertEquals(
            ['20060302.0120', 'current'], sorted(os.listdir(custom_path)))

        # The custom files were also copied to the public librarian
        for customfile in delayed_copy.customfiles:
            self.assertFalse(customfile.libraryfilealias.restricted)

    def test_realiseUpload_for_source_only_delayed_copies(self):
        # Source-only delayed-copies results in the source published
        # in the destination archive and its corresponding build
        # recors ready to be dispatched.

        # Create the default delayed-copy context.
        delayed_copy = self.createDelayedCopy(source_only=True)
        self.test_publisher.breezy_autotest.status = (
            SeriesStatus.CURRENT)
        self.layer.txn.commit()

        # Accept and publish the delayed-copy.
        delayed_copy.acceptFromCopy()
        logger = BufferLogger()
        pub_records = delayed_copy.realiseUpload(logger=logger)

        # Only the source is published and the needed builds are created
        # in the destination archive.
        self.assertEquals(1, len(pub_records))
        [pub_record] = pub_records
        [build] = pub_record.getBuilds()
        self.assertEquals(
            BuildStatus.NEEDSBUILD, build.status)

    def test_realiseUpload_for_overridden_component_archive(self):
        # If the component of an upload is overridden to 'Partner' for
        # example, then the new publishing record should be for the
        # partner archive.
        self.test_publisher.prepareBreezyAutotest()

        # Get some sample changes file content for the new upload.
        changes_file = open(
            datadir('suite/bar_1.0-1/bar_1.0-1_source.changes'))
        changes_file_content = changes_file.read()
        changes_file.close()

        main_upload_release = self.test_publisher.getPubSource(
            sourcename='main-upload', spr_only=True,
            component='main', changes_file_content=changes_file_content)
        package_upload = main_upload_release.package_upload

        self.assertEqual("primary", main_upload_release.upload_archive.name)

        # Override the upload to partner and verify the change.
        partner_component = getUtility(IComponentSet)['partner']
        main_component = getUtility(IComponentSet)['main']
        package_upload.overrideSource(
            partner_component, None, [partner_component, main_component])
        self.assertEqual(
            "partner", main_upload_release.upload_archive.name)

        # Now realise the upload and verify that the publishing is for
        # the partner archive.
        pub = package_upload.realiseUpload()[0]
        self.assertEqual("partner", pub.archive.name)

    def test_package_name_and_version(self):
        # The PackageUpload knows the name and version of the package
        # being uploaded.  Internally, it gets this information from the
        # SourcePackageRelease.
        upload = self.factory.makePackageUpload()
        spr = self.factory.makeSourcePackageRelease()
        upload.addSource(spr)
        self.assertEqual(spr.sourcepackagename.name, upload.package_name)
        self.assertEqual(spr.version, upload.package_version)


class TestPackageUploadWithPackageCopyJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def makeUploadWithPackageCopyJob(self, sourcepackagename=None):
        """Create a `PackageUpload` plus attached `PlainPackageCopyJob`."""
        from lp.soyuz.model.packagecopyjob import IPackageCopyJobSource
        upload = self.factory.makeCopyJobPackageUpload(
            sourcepackagename=sourcepackagename)
        return upload, getUtility(IPackageCopyJobSource).wrap(
            upload.package_copy_job)

    def test_package_copy_job_property(self):
        # Test that we can set and get package_copy_job.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        self.assertEqual(
            removeSecurityProxy(pcj).context, pu.package_copy_job)

    def test_getByPackageCopyJobIDs(self):
        # getByPackageCopyJobIDs retrieves the right PackageCopyJob.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        result = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [pcj.id])
        self.assertEqual(pu, result.one())

    def test_overrideSource_with_copy_job(self):
        # The overrides should be stored in the job's metadata.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        old_component = getUtility(IComponentSet)[pcj.component_name]
        component = getUtility(IComponentSet)['restricted']
        section = getUtility(ISectionSet)['games']

        expected_metadata = {}
        expected_metadata.update(pcj.metadata)
        expected_metadata.update({
            'component_override': component.name,
            'section_override': section.name,
            })

        result = pu.overrideSource(
            component, section, allowed_components=[component, old_component])

        self.assertTrue(result)
        self.assertEqual(expected_metadata, pcj.metadata)

    def test_overrideSource_checks_permission_for_old_component(self):
        pu = self.factory.makeCopyJobPackageUpload()
        only_allowed_component = self.factory.makeComponent()
        section = self.factory.makeSection()
        self.assertRaises(
            QueueInconsistentStateError,
            pu.overrideSource,
            only_allowed_component, section, [only_allowed_component])

    def test_overrideSource_checks_permission_for_new_component(self):
        pu, pcj = self.makeUploadWithPackageCopyJob()
        current_component = getUtility(IComponentSet)[pcj.component_name]
        disallowed_component = self.factory.makeComponent()
        section = self.factory.makeSection()
        self.assertRaises(
            QueueInconsistentStateError,
            pu.overrideSource,
            disallowed_component, section, [current_component])

    def test_overrideSource_ignores_None_component_change(self):
        # overrideSource accepts None as a component; it will not object
        # based on permissions for the new component.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        current_component = getUtility(IComponentSet)[pcj.component_name]
        new_section = self.factory.makeSection()
        pu.overrideSource(None, new_section, [current_component])
        self.assertEqual(current_component.name, pcj.component_name)
        self.assertEqual(new_section.name, pcj.section_name)

    def test_acceptFromQueue_with_copy_job(self):
        # acceptFromQueue should accept the upload and resume the copy
        # job.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        pu.pocket = PackagePublishingPocket.RELEASE
        self.assertEqual(PackageUploadStatus.NEW, pu.status)

        pu.acceptFromQueue()

        self.assertEqual(PackageUploadStatus.ACCEPTED, pu.status)
        self.assertEqual(JobStatus.WAITING, pcj.status)

    def test_rejectFromQueue_with_copy_job(self):
        # rejectFromQueue will reject the upload and fail the copy job.
        pu, pcj = self.makeUploadWithPackageCopyJob()

        pu.rejectFromQueue()

        self.assertEqual(PackageUploadStatus.REJECTED, pu.status)
        self.assertEqual(JobStatus.FAILED, pcj.status)

        # It cannot be resurrected after rejection.
        self.assertRaises(
            QueueInconsistentStateError, pu.acceptFromQueue, None)

    def test_package_name_and_version_are_as_in_job(self):
        # The PackageUpload knows the name and version of the package
        # being uploaded.  It gets this information from the
        # PlainPackageCopyJob.
        upload, job = self.makeUploadWithPackageCopyJob()
        self.assertEqual(job.package_name, upload.package_name)
        self.assertEqual(job.package_version, upload.package_version)

    def test_displayarchs_for_copy_job_is_sync(self):
        # For copy jobs, displayarchs is "source."
        upload, job = self.makeUploadWithPackageCopyJob()
        self.assertEqual('sync', upload.displayarchs)

    def test_component_and_section_name(self):
        # An upload with a copy job takes its component and section
        # names from the job.
        spn = self.factory.makeSourcePackageName()
        upload, pcj = self.makeUploadWithPackageCopyJob(sourcepackagename=spn)
        component = self.factory.makeComponent()
        section = self.factory.makeSection()
        pcj.addSourceOverride(SourceOverride(spn, component, section))
        self.assertEqual(component.name, upload.component_name)

    def test_displayname_is_package_name(self):
        # An upload with a copy job uses the package name for its
        # display name.
        spn = self.factory.makeSourcePackageName()
        upload, job = self.makeUploadWithPackageCopyJob(sourcepackagename=spn)
        self.assertEqual(spn.name, upload.displayname)

    def test_upload_with_copy_job_has_no_source_package_release(self):
        # A copy job does not provide the upload with a
        # SourcePackageRelease.
        pu, pcj = self.makeUploadWithPackageCopyJob()
        self.assertIs(None, pu.sourcepackagerelease)


class TestPackageUploadSet(TestCaseWithFactory):
    """Unit tests for `PackageUploadSet`."""

    layer = LaunchpadZopelessLayer

    def test_PackageUploadSet_implements_IPackageUploadSet(self):
        upload_set = getUtility(IPackageUploadSet)
        self.assertThat(upload_set, Provides(IPackageUploadSet))

    def test_getAll_returns_source_upload(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual([upload], upload_set.getAll(distroseries))

    def test_getAll_returns_build_upload(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeBuildPackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual([upload], upload_set.getAll(distroseries))

    def test_getAll_returns_custom_upload(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeCustomPackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual([upload], upload_set.getAll(distroseries))

    def test_getAll_returns_copy_job_upload(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeCopyJobPackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual([upload], upload_set.getAll(distroseries))

    def test_getAll_filters_by_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackageUpload(distroseries)
        other_series = self.factory.makeDistroSeries()
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual([], upload_set.getAll(other_series))

    def test_getAll_matches_created_since_date(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        yesterday = upload.date_created - timedelta(1)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload],
            upload_set.getAll(distroseries, created_since_date=yesterday))

    def test_getAll_filters_by_created_since_date(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        tomorrow = upload.date_created + timedelta(1)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, created_since_date=tomorrow))

    def test_getAll_matches_status(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        status = upload.status
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, status=status))

    def test_getAll_filters_by_status(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackageUpload(distroseries)
        status = PackageUploadStatus.DONE
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, status=status))

    def test_getAll_matches_pocket(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        pocket = upload.pocket
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, pocket=pocket))

    def test_getAll_filters_by_pocket(self):
        def find_different_pocket_than(pocket):
            for other_pocket in PackagePublishingPocket.items:
                if other_pocket != pocket:
                    return other_pocket

        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        pocket = find_different_pocket_than(upload.pocket)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, pocket=pocket))

    def test_getAll_matches_custom_type(self):
        distroseries = self.factory.makeDistroSeries()
        custom_type = PackageUploadCustomFormat.DDTP_TARBALL
        upload = self.factory.makeCustomPackageUpload(
            distroseries, custom_type=custom_type)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload],
            upload_set.getAll(distroseries, custom_type=custom_type))

    def test_getAll_filters_by_custom_type(self):
        distroseries = self.factory.makeDistroSeries()
        one_type = PackageUploadCustomFormat.DIST_UPGRADER
        other_type = PackageUploadCustomFormat.ROSETTA_TRANSLATIONS
        self.factory.makeCustomPackageUpload(
            distroseries, custom_type=one_type)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, custom_type=other_type))

    def test_getAll_matches_source_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        upload = self.factory.makeSourcePackageUpload(
            distroseries, sourcepackagename=spn)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, name=spn.name))

    def test_getAll_filters_source_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackageUpload(distroseries)
        other_name = self.factory.makeSourcePackageName().name
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=other_name))

    def test_getAll_matches_build_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        bpn = self.factory.makeBinaryPackageName()
        upload = self.factory.makeBuildPackageUpload(
            distroseries, binarypackagename=bpn)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, name=bpn.name))

    def test_getAll_filters_build_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeBuildPackageUpload(distroseries)
        other_name = self.factory.makeBinaryPackageName().name
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=other_name))

    def test_getAll_matches_custom_upload_by_file_name(self):
        distroseries = self.factory.makeDistroSeries()
        filename = self.factory.getUniqueUnicode()
        upload = self.factory.makeCustomPackageUpload(
            distroseries, filename=filename)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, name=filename))

    def test_getAll_filters_custom_upload_by_file_name(self):
        distroseries = self.factory.makeDistroSeries()
        filename = self.factory.getUniqueString()
        self.factory.makeCustomPackageUpload(distroseries, filename=filename)
        other_name = self.factory.getUniqueUnicode()
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=other_name))

    def test_getAll_matches_copy_job_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        upload = self.factory.makeCopyJobPackageUpload(
            distroseries, sourcepackagename=spn)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, name=spn.name))

    def test_getAll_filters_copy_job_upload_by_package_name(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeCopyJobPackageUpload(distroseries)
        other_name = self.factory.makeSourcePackageName().name
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=other_name))

    def test_getAll_without_exact_match_matches_substring_of_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        upload = self.factory.makeSourcePackageUpload(
            distroseries, sourcepackagename=spn)
        partial_name = spn.name[:-1]
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, name=partial_name))

    def test_getAll_with_exact_match_matches_exact_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        upload = self.factory.makeSourcePackageUpload(
            distroseries, sourcepackagename=spn)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload],
            upload_set.getAll(distroseries, name=spn.name, exact_match=True))

    def test_getAll_with_exact_match_does_not_match_substring_of_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackageUpload(
            distroseries, sourcepackagename=spn)
        partial_name = spn.name[:-1]
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [],
            upload_set.getAll(
                distroseries, name=partial_name, exact_match=True))

    def test_getAll_without_exact_match_escapes_name(self):
        distroseries = self.factory.makeDistroSeries()
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=u"'"))

    def test_getAll_with_exact_match_escapes_name(self):
        distroseries = self.factory.makeDistroSeries()
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, name=u"'", exact_match=True))

    def test_getAll_matches_source_upload_by_version(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        version = upload.displayversion
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, version=version))

    def test_getAll_filters_source_upload_by_version(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackageUpload(distroseries)
        other_version = self.factory.getUniqueUnicode()
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, version=other_version))

    def test_getAll_matches_build_upload_by_version(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeBuildPackageUpload(distroseries)
        version = upload.displayversion
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, version=version))

    def test_getAll_filters_build_upload_by_version(self):
        distroseries = self.factory.makeDistroSeries()
        other_version = self.factory.getUniqueUnicode()
        self.factory.makeBuildPackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, version=other_version))

    def test_getAll_version_filter_ignores_custom_uploads(self):
        distroseries = self.factory.makeDistroSeries()
        other_version = self.factory.getUniqueUnicode()
        self.factory.makeCustomPackageUpload(distroseries)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, version=other_version))

    def test_getAll_version_filter_ignores_copy_job_uploads(self):
        # Version match for package copy jobs is not implemented at the
        # moment.
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeCopyJobPackageUpload(distroseries)
        version = upload.package_copy_job.package_version
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [], upload_set.getAll(distroseries, version=version))

    def test_getAll_without_exact_match_matches_substring_of_version(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        version = upload.displayversion[1:-1]
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload], upload_set.getAll(distroseries, version=version))

    def test_getAll_with_exact_match_matches_exact_version(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        version = upload.displayversion
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload],
            upload_set.getAll(
                distroseries, version=version, exact_match=True))

    def test_getAll_w_exact_match_does_not_match_substring_of_version(self):
        distroseries = self.factory.makeDistroSeries()
        upload = self.factory.makeSourcePackageUpload(distroseries)
        version = upload.displayversion[1:-1]
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [],
            upload_set.getAll(
                distroseries, version=version, exact_match=True))

    def test_getAll_can_combine_version_and_name(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        upload = self.factory.makeSourcePackageUpload(
            distroseries, sourcepackagename=spn)
        upload_set = getUtility(IPackageUploadSet)
        self.assertContentEqual(
            [upload],
            upload_set.getAll(
                distroseries, name=spn.name, version=upload.displayversion))

    def test_getAll_orders_in_reverse_historical_order(self):
        # The results from getAll are returned in order of creation,
        # newest to oldest, regardless of upload type.
        series = self.factory.makeDistroSeries()
        store = IStore(series)
        ordered_uploads = []
        ordered_uploads.append(self.factory.makeCopyJobPackageUpload(series))
        store.flush()
        ordered_uploads.append(self.factory.makeBuildPackageUpload(series))
        store.flush()
        ordered_uploads.append(self.factory.makeSourcePackageUpload(series))
        store.flush()
        ordered_uploads.append(self.factory.makeCustomPackageUpload(series))
        store.flush()
        ordered_uploads.append(self.factory.makeCopyJobPackageUpload(series))
        store.flush()
        ordered_uploads.append(self.factory.makeSourcePackageUpload(series))
        store.flush()
        self.assertEqual(
            list(reversed(ordered_uploads)),
            list(getUtility(IPackageUploadSet).getAll(series)))

    def test_rejectFromQueue_no_changes_file(self):
        # If the PackageUpload has no changesfile, we can still reject it.
        pu = self.factory.makePackageUpload()
        pu.changesfile = None
        pu.rejectFromQueue()
        self.assertEqual(PackageUploadStatus.REJECTED, pu.status)
