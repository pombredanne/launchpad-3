# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of Rosetta translations tarballs.

ROSETTA-TRANSLATIONS is a custom format upload supported by Launchpad
infrastructure to enable developers to publish translations.
"""

__metaclass__ = type

__all__ = [
    'RosettaTranslationsUpload',
    'process_rosetta_translations',
    ]

from zope.component import getUtility

from lp.archivepublisher.customupload import CustomUpload
from lp.archivepublisher.debversion import Version
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.interfaces.packagetranslationsuploadjob import (
    IPackageTranslationsUploadJobSource,
    )


def debug(logger, msg):
    if logger is not None:
        logger.debug(msg)


class RosettaTranslationsUpload(CustomUpload):
    """Rosetta Translations tarball upload.

    All other CustomUploads extract and copy files when processed,
    RosettaTranslationsUpload is a special case that involves more than
    copying the files, so it triggers a job that processes them accordingly.
    For this reason, all methods from CustomUpload that deal with files are
    bypassed.
    """
    custom_type = "rosetta-translations"

    def process(self, packageupload, libraryfilealias):
        sourcepackagerelease = packageupload.sourcepackagerelease

        # Ignore translations not with main distribution purposes.
        if packageupload.archive.purpose not in MAIN_ARCHIVE_PURPOSES:
            debug(self.logger,
                  "Skipping translations since its purpose is not "
                  "in MAIN_ARCHIVE_PURPOSES.")
            return

        # If the distroseries is 11.10 (oneiric) or later, the valid names
        # check is not required.  (See bug 788685.)
        distroseries = sourcepackagerelease.upload_distroseries
        do_names_check = Version(distroseries.version) < Version('11.10')

        valid_pockets = (
            PackagePublishingPocket.RELEASE, PackagePublishingPocket.SECURITY,
            PackagePublishingPocket.UPDATES, PackagePublishingPocket.PROPOSED)
        valid_components = ('main', 'restricted')
        if (packageupload.pocket not in valid_pockets or
            (do_names_check and
            sourcepackagerelease.component.name not in valid_components)):
            # XXX: CarlosPerelloMarin 2006-02-16 bug=31665:
            # This should be implemented using a more general rule to accept
            # different policies depending on the distribution.
            # Ubuntu's MOTU told us that they are not able to handle
            # translations like we do in main. We are going to import only
            # packages in main.
            return

        blamee = packageupload.findPersonToNotify()
        getUtility(IPackageTranslationsUploadJobSource).create(
                            sourcepackagerelease, libraryfilealias,
                            blamee)

    @staticmethod
    def parsePath(tarfile_path):
        pass

    def setComponents(self, tarfile_path):
        pass

    def setTargetDirectory(self, pubconf, tarfile_path, distroseries):
        pass

    @classmethod
    def getSeriesKey(cls, tarfile_path):
        pass

    def shouldInstall(self, filename):
        pass


def process_rosetta_translations(packageupload, libraryfilealias, logger=None):
    """Process a Rosetta translation upload."""
    upload = RosettaTranslationsUpload(logger)
    upload.process(packageupload, libraryfilealias)
