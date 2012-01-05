# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test notification behaviour for cross-distro package syncs."""

__metaclass__ = type

import os.path

from zope.component import getUtility

from lp.archiveuploader.nascentupload import (
    NascentUpload,
    UploadError,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import (
    ArchivePermissionType,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.soyuz.scripts.packagecopier import do_copy
from lp.testing import (
    login,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications


class FakeUploadPolicy:
    def __init__(self, spph):
        self.distroseries = spph.distroseries
        self.archive = spph.distroseries.main_archive
        self.pocket = spph.pocket

    setDistroSeriesAndPocket = FakeMethod()
    validateUploadType = FakeMethod()
    checkUpload = FakeMethod()


class FakeChangesFile:
    def __init__(self, spph, file_path, maintainer_key):
        self.files = []
        self.filepath = file_path
        self.filename = os.path.basename(file_path)
        self.architectures = ['i386']
        self.suite_name = '-'.join([spph.distroseries.name, spph.pocket.name])
        self.raw_content = open(file_path).read()
        self.signingkey = maintainer_key

    checkFileName = FakeMethod([])
    processAddresses = FakeMethod([])
    processFiles = FakeMethod([])
    verify = FakeMethod([UploadError("Deliberately broken")])


class TestSyncNotification(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def makePersonWithEmail(self):
        """Create a person; return (person, email)."""
        address = "%s@example.com" % self.factory.getUniqueString()
        person = self.factory.makePerson(email=address)
        return person, address

    def makeSPPH(self, distroseries, maintainer_address):
        """Create a `SourcePackagePublishingHistory`."""
        return self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, pocket=PackagePublishingPocket.RELEASE,
            dsc_maintainer_rfc822=maintainer_address)

    def makeUploader(self, archive, component):
        """Create a person with upload privileges for archive/component."""
        uploader = self.factory.makePerson()
        ArchivePermission(
            person=uploader, archive=archive, component=component,
            permission=ArchivePermissionType.UPLOAD)
        return uploader

    def syncSource(self, spph, target_distroseries):
        """Sync `spph` into `target_distroseries`."""
        getUtility(ISourcePackageFormatSelectionSet).add(
            target_distroseries, SourcePackageFormat.FORMAT_1_0)
        target_archive = target_distroseries.main_archive
        [synced_spph] = do_copy(
            [spph], target_archive, target_distroseries,
            pocket=spph.pocket,
            person=self.makeUploader(target_archive, spph.component),
            allow_delayed_copies=False, close_bugs=False)
        return synced_spph

    def makeChangesFile(self, spph, maintainer, maintainer_address):
        maintainer_key = self.factory.makeGPGKey(maintainer)
        temp_dir = self.makeTemporaryDirectory()
        changes_file = os.path.join(
            temp_dir, "%s.changes" % spph.source_package_name)
        open(changes_file, 'w').write(
            "Maintainer: %s <%s>\n" % (maintainer.name, maintainer_address))
        return FakeChangesFile(spph, changes_file, maintainer_key)

    def makeNascentUpload(self, spph, maintainer, maintainer_address):
        """Create a `NascentUpload` for `spph`."""
        return NascentUpload(
            self.makeChangesFile(spph, maintainer, maintainer_address),
            FakeUploadPolicy(spph), DevNullLogger())

    def processAndRejectUpload(self, nascent_upload):
        nascent_upload.process()
        # Obtain the required privileges for do_reject.
        login('foo.bar@canonical.com')
        nascent_upload.do_reject(notify=True)

    def getNotifiedAddresses(self):
        """Get email addresses that were notified."""
        return [message['to'] for message in pop_notifications()]

    def test_maintainer_not_notified_about_build_failure_elsewhere(self):
        """No mail to maintainers about builds they're not responsible for.


        We import Debian source packages, then sync them into Ubuntu (and
        from there, into Ubuntu-derived distros).  Those syncs then trigger
        builds that the original Debian maintainers are not responsible for.

        In a situation like that, we should not bother the maintainer with
        the failure.

        This test guards against bug 876594.
        """
        maintainer, maintainer_address = self.makePersonWithEmail()
        dsp = self.factory.makeDistroSeriesParent()
        original_spph = self.makeSPPH(dsp.parent_series, maintainer_address)
        synced_spph = self.syncSource(original_spph, dsp.derived_series)
        nascent_upload = self.makeNascentUpload(
            synced_spph, maintainer, maintainer_address)
        pop_notifications()
        self.processAndRejectUpload(nascent_upload)

        self.assertNotIn(
            maintainer_address, '\n'.join(self.getNotifiedAddresses()))
