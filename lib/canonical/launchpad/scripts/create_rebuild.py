# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Create a rebuild archive."""


__metaclass__ = type
__all__ = ['RebuildArchiveCreator']


import sys

from zope.component import getUtility

from canonical.launchpad.components.packagelocation import (
    build_package_location, PackageLocation)
from canonical.launchpad.interfaces import (NotFoundError,
    PackagePublishingStatus)
from canonical.launchpad.interfaces.archiverebuild import (
    ArchiveRebuildAlreadyExists, IArchiveRebuildSet)
from canonical.launchpad.interfaces.component import IComponentSet
from canonical.launchpad.interfaces.packagecloner import IPackageCloner
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.scripts.ftpmasterbase import (
    SoyuzScript, SoyuzScriptError)
from canonical.launchpad.validators.name import valid_name


class RebuildArchiveCreator(SoyuzScript):
    """Create a rebuild archive and populate it with packages.

    The logic needed to create a rebuild archive, populate it with
    source packages and instantiate the builds required.

    The command line options supported are as follows:

        -c c | --component c : component from which to copy source packages.
            One of: main, restricted, universe, multiverse, partner.
        -d d | --distribution d : the distribution for which the rebuild
            archive is to be created.
        -r n | --rebuildarchive n : the name of the rebuild archive to be
            created.
        -s s | --suite s : the suite (distribution series + publishing pocket)
            for which the rebuild archive is to be created.
        -t t | --text t : the reason for the rebuild
    """

    usage = __doc__
    description = 'Create a rebuild archive.'

    def createRebuildArchive(
        self, component, rebuild_archive_name, suite, distro, rebuild_reason,
        user_name):
        """Create rebuild archive, populate with packages and builds.

        :type component: `str`
        :param component: the component from which to copy source packages.
        :type rebuild_archive_name: `str`
        :param rebuild_archive_name: the name of the rebuild archive that
            is to be created.
        :type suite: `str`
        :param suite: the suite (distro series + publishing pocket) for
            which to create the rebuild archive.
        :type distro: `str`
        :param distro: the distro for which to create the rebuild archive.
        :type rebuild_reason: `str`
        :param rebuild_reason: the reason for the rebuild.
        :type user_name: `str`
        :param user_name: the name of the user who is creating the rebuild
            archive.
        """

        if not valid_name(rebuild_archive_name):
            raise SoyuzScriptError(
                "Invalid rebuild archive name: '%s'" % rebuild_archive_name)

        origin = build_package_location(distro, suite=suite)

        try:
            origin.component = getUtility(IComponentSet)[component]
        except NotFoundError, e:
            raise SoyuzScriptError("Invalid component name: '%s'" % component)

        print origin

        registrant = getUtility(IPersonSet).getByName(user_name)
        if registrant is None:
            raise SoyuzScriptError("Invalid user name: '%s'" % user_name)

        try:
            archive_rebuild = getUtility(IArchiveRebuildSet).new(
                rebuild_archive_name, origin.distroseries, registrant,
                rebuild_reason)
        except ArchiveRebuildAlreadyExists, e:
            raise SoyuzScriptError(str(e))

        destination = PackageLocation(
            archive_rebuild.archive, origin.distribution,
            archive_rebuild.distroseries, origin.pocket, component)

        # Clone the source packages.
        pkg_cloner = getUtility(IPackageCloner)
        pkg_cloner.clonePackages(origin, destination)

        # Create builds for the cloned packages.
        self._createMissingBuilds(
            destination.distroseries, destination.archive)

    def mainTask(self):
        """Main function entry point.
        """
        args_missing = 0

        if self.options.component is None:
            raise SoyuzScriptError("error: component not specified")

        if self.options.distribution_name is None:
            raise SoyuzScriptError("error: distribution not specified")

        if self.options.rebuildarchivename is None:
            raise SoyuzScriptError(
                "error: rebuild archive name not specified")

        if self.options.rebuildreason is None:
            raise SoyuzScriptError("error: rebuild reason not specified")

        if self.options.suite is None:
            raise SoyuzScriptError(
                'error: suite (distribution series + publishing pocket)'
                ' not specified')

        self.createRebuildArchive(
            self.options.component, self.options.rebuildarchivename,
            self.options.suite, self.options.distribution_name,
            self.options.rebuildreason, self.options.username)

    def add_my_options(self):
        """Parse command line arguments and trigger rebuild archive creation.
        """
        SoyuzScript.add_my_options(self)
        self.parser.add_option(
            "-r", "--rebuildarchive", dest="rebuildarchivename",
            help="rebuild archive name")
        self.parser.add_option(
            "-t", "--text", dest="rebuildreason", help="rebuild reason text")
        self.parser.add_option(
            "-u", "--user", dest="username",
            help="the user creating the rebuild archive")

    def _createMissingBuilds(self, distroseries, archive):
        """Create builds for all source packages in 'location'.

        :type distroseries: `DistroSeries`
        :param distroseries: the distro series for which to create builds.
        :type archive: `Archive`
        :param archive: the archive for which to create builds.
        """
        self.logger.info("Processing %s." % distroseries.name)

        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        architectures = list(distroseries.architectures)
        if len(architectures) == 0:
            self.logger.info(
                "No architectures defined for %s, done." % distroseries.name)
            return

        self.logger.info(
            "Supported architectures: %s." %
            " ".join(arch_series.architecturetag
                     for arch_series in architectures))

        sources_published = self._getSourcesPublishedForArchive(
            distroseries, archive)

        self.logger.info(
            "Found %d source(s) published." % sources_published.count())

        def get_spn(pub):
            return pub.sourcepackagerelease.sourcepackagename.name

        for pubrec in sources_published:
            builds = pubrec.createMissingBuilds(
                architectures_available=architectures,
                logger=self.logger)
            if len(builds) == 0:
                self.logger.info("%s has no builds." % get_spn(pubrec))
                continue
            self.logger.info("%s has %s build(s)." %
                             (get_spn(pubrec), len(builds)))
            self.txn.commit()

    def _getSourcesPublishedForArchive(self, distroseries, archive):
        """Get published sources for given distroseries and archive.

        :type distroseries: `DistroSeries`
        :param distroseries: the distro series for which to get
            published sources.
        :type archive: `Archive`
        :param archive: the archive for which to get published
            sources.
        """
        # Both, PENDING and PUBLISHED sources will be considered for
        # as PUBLISHED. It's part of the assumptions made in:
        # https://launchpad.net/soyuz/+spec/build-unpublished-source
        pending = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            )

        return archive.getPublishedSources(
            distroseries=distroseries, status=pending)
