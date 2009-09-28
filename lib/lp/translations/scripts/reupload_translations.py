__metaclass__ = type

__all__ = [
	'ReuploadPackageTranslations',
	]

import logging
import operator
import re
import sys

from zope.component import getUtility

from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet, PackageUploadCustomFormat)
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue)


class ReuploadPackageTranslations(LaunchpadScript):
    """Re-upload latest translations for given distribution packages."""

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option('-d', '--distribution', dest='distro',
            help="Distribution to upload for.", default='ubuntu')
        self.parser.add_option('-s', '--series', dest='distroseries',
            help="Distribution release series to upload for.")
        self.parser.add_option('-p', '--package', action='append',
            dest='packages', default=[],
            help="Name(s) of source package(s) to re-upload.")
        self.parser.add_option('-l', '--dry-run', dest='dryrun',
            action='store_true', default=False,
            help="Pretend to upload, but make no actual changes.")
 
    def main(self):
        """See `LaunchpadScript`."""
        self._setDistroDetails()

        if len(self.options.packages) == 0:
            raise LaunchpadScriptFailure("No packages specified.")

        if self.options.dryrun:
            self.logger.info("Dry run.  Not really uploading anything.")

        for package_name in self.options.packages:
            self._processPackage(self._findPackage(package_name))
            self._commit()

        self.logger.info("Done.")

    def _commit(self):
        """Commit transaction (or abort if dry run)."""
        if self.txn:
            if self.options.dryrun:
                self.txn.abort()
            else:
                self.txn.commit()

    def _setDistroDetails(self):
        """Figure out the `Distribution`/`DistroSeries` to act upon."""
        # Avoid circular imports.
        from lp.registry.interfaces.distribution import IDistributionSet

        distroset = getUtility(IDistributionSet)
        self.distro = distroset.getByName(self.options.distro)

        if not self.options.distroseries:
            raise LaunchpadScriptFailure(
                "Specify a distribution release series.")

        self.distroseries = self.distro.getSeries(self.options.distroseries)

    def _findPackage(self, name):
        """Find `SourcePackage` of given name."""
        # Avoid circular imports.
        from lp.registry.interfaces.sourcepackage import ISourcePackageFactory

        factory = getUtility(ISourcePackageFactory)
        nameset = getUtility(ISourcePackageNameSet)

        sourcepackagename = nameset.queryByName(name)

        return factory.new(sourcepackagename, self.distroseries)

    def _getUploadAliases(self, package):
        """Get `LibraryFileAlias`es for package's translation upload(s)."""
        # Avoid circular imports.
        from lp.soyuz.interfaces.publishing import PackagePublishingStatus

        our_format = PackageUploadCustomFormat.ROSETTA_TRANSLATIONS
        uploadset = getUtility(IPackageUploadSet)

        packagename = package.sourcepackagename.name
        displayname = package.displayname

        histories = self.distro.main_archive.getPublishedSources(
            name=packagename, distroseries=self.distroseries,
            status=PackagePublishingStatus.PUBLISHED, exact_match=True)
        histories = list(histories)
        assert len(histories) <= 1, "Found multiple published histories."
        if len(histories) == 0:
            self.logger.info(
                "No published history entry for %s." % displayname)
            return []

        history = histories[0]
        release = history.sourcepackagerelease
        uploadsources = list(uploadset.getSourceBySourcePackageReleaseIDs(
            [release.id]))
        assert len(uploadsources) <= 1, "Found multiple upload sources."
        if len(uploadsources) == 0:
            self.logger.info("No upload source for %s." % displayname)
            return []

        upload = uploadsources[0].packageupload
        custom_files = [
            custom
            for custom in upload.customfiles if
            custom.format == our_format
            ]

        if len(custom_files) == 0:
            self.logger.info("No translations upload for %s." % displayname)
        elif len(custom_files) > 1:
            self.logger.info("Found %d uploads for %s" % (
                len(custom_files), displayname))

        custom_files.sort(key=operator.attrgetter('date_created'))

        return [custom.libraryfilealias for custom in custom_files]

    def _processPackage(self, package):
        """Get translations for `package` re-uploaded."""
        self.logger.info("Processing %s" % package.displayname)
        tarball_aliases = self._getUploadAliases(package)
        queue = getUtility(ITranslationImportQueue)
        rosetta_team = getUtility(ILaunchpadCelebrities).rosetta_experts

        for alias in tarball_aliases:
            self.logger.debug("Uploading file '%s' for %s." % (
                alias.filename, package.displayname))
            queue.addOrUpdateEntriesFromTarball(
                alias.content, True, rosetta_team,
                sourcepackagename=package.sourcepackagename,
                distroseries=self.distroseries)
