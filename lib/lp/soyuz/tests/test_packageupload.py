# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

from email import message_from_string
import os
import shutil

from zope.component import getUtility

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archiveuploader.tests import datadir
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import BufferLogger
from lp.services.mail import stub
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


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
            'Cannot process delayed copies.',
            delayed_copy.acceptFromQueue, 'some-announce-list')

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
            'dist-upgrader_20060302.0120_all.tar.gz (delayed),\n\t'
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
