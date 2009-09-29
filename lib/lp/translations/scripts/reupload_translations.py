__metaclass__ = type

__all__ = [
	'ReuploadPackageTranslations',
	]

from StringIO import StringIO

from zope.component import getUtility

from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
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

    def _processPackage(self, package):
        """Get translations for `package` re-uploaded."""
        self.logger.info("Processing %s" % package.displayname)
        tarball_aliases = package.getLatestTranslationsUploads()
        queue = getUtility(ITranslationImportQueue)
        rosetta_team = getUtility(ILaunchpadCelebrities).rosetta_experts

        for alias in tarball_aliases:
            self.logger.debug("Uploading file '%s' for %s." % (
                alias.filename, package.displayname))
            queue.addOrUpdateEntriesFromTarball(
                StringIO(alias.read()), True, rosetta_team,
                sourcepackagename=package.sourcepackagename,
                distroseries=self.distroseries)
