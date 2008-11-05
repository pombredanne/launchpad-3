# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Create a copy archive (if needed) and populate it with packages."""


__metaclass__ = type
__all__ = [
    'ArchivePopulator',
    ]


from zope.component import getUtility

from canonical.launchpad.components.packagelocation import (
    build_package_location)
from canonical.launchpad.interfaces import PackagePublishingStatus
from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, IArchiveSet)
from canonical.launchpad.interfaces.packagecloner import IPackageCloner
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.scripts.ftpmasterbase import (
    SoyuzScript, SoyuzScriptError)
from canonical.launchpad.validators.name import valid_name


class ArchivePopulator(SoyuzScript):
    """
    Create a copy archive and populate it with packages.

    The logic needed to create a copy archive, populate it with source
    packages and instantiate the builds required.

    Please note: the destination copy archive must not exist yet. Otherwise
    the script will abort with an error."""

    usage = __doc__
    description = (
        'Create a copy archive and populate it with packages and build '
        'records.')

    def populateArchive(self, origin, destination, 
                        dest_archive_desc, arch_tags=None):
        """Create archive (if needed), populate it with packages and builds.

        :type origin: `dict`
        :param origin: origin data dictionary with the following
            keys: archive-owner, archive-name, distro, suite
        :type destination: `dict`
        :param destination: destination data dictionary with following
            keys: archive-owner, archive-name, distro, suite
        :type dest_archive_desc: `str`
        :param dest_archive_desc: the description of the destination copy
            archive.
        :type arch_tags: list of strings
        :param arch_tags: the list of architecture tags for which to
            create builds (optional).
        """
        if origin['suite'] != '':
            the_origin = build_package_location(
                origin['distro'], suite=origin['suite'])
        else:
            the_origin = build_package_location(origin['distro'])

        the_destination = build_package_location(
            destination['distro'], suite=destination['suite'])

        registrant = getUtility(IPersonSet).getByName(
            destination['archive-owner'])
        if registrant is None:
            raise SoyuzScriptError(
                "Invalid user name: '%s'" % destination['archive-owner'])

        # First try to access the destination copy archive.
        copy_archive = getUtility(IArchiveSet).getByDistroAndName(
            the_destination.distribution, destination['archive-name'])

        # No copy archive with the specified name found, create one.
        if copy_archive is None:
            if dest_archive_desc is None or dest_archive_desc == '':
                raise SoyuzScriptError(
                    "No description provided for new copy archive")
            copy_archive = getUtility(IArchiveSet).new(
                ArchivePurpose.COPY, registrant, destination['archive-name'],
                the_destination.distribution, dest_archive_desc)
            the_destination.archive = copy_archive
        else:
            raise SoyuzScriptError(
                "A copy archive named '%s' exists already" %
                destination['archive-name'])


        # Clone the source packages.
        pkg_cloner = getUtility(IPackageCloner)
        pkg_cloner.clonePackages(the_origin, the_destination)

        # Create builds for the cloned packages.
        self._createMissingBuilds(
            the_destination.distroseries, the_destination.archive, arch_tags)

    def mainTask(self):
        """Main function entry point.
        """
        args_missing = 0

        if self.options.origin_spec is None:
            raise SoyuzScriptError(
                "error: origin of copy operation not specified.")

        if self.options.destination_spec is None:
            raise SoyuzScriptError(
                "error: destination of copy operation not specified.")

        keys = [
            'archive-owner', 'archive-name', 'distro', 'suite']

        # Put the origin values into a dictionary. We want 3 splits at a
        # maximum.
        origin_data = [value.strip() for value in
                       self.options.origin_spec.split(':', 3)]
        origin = dict(zip(keys, origin_data))

        # The distro name must be set.
        if origin['distro'] == '':
            raise SoyuzScriptError(
                "error: distro name not specified for the origin of the "
                "copy operation.")

        # Now put the destination data in a doctionary and make sure that the
        # first three elements (archive owner and name, distro name) were
        # specified.
        destination_data = [value.strip() for value in
                            self.options.destination_spec.split(':', 3)]
        destination = dict(zip(keys, destination_data))

        for key in keys[:3]:
            if destination[key] == '':
                raise SoyuzScriptError(
                    "error: %s not specified for the destination of the "
                    "copy operation." % key.replace('-', ' '))

        if not valid_name(destination['archive-name']):
            raise SoyuzScriptError(
                "Invalid archive name: '%s'" % destination['archive-name'])

        self.populateArchive(
            origin, destination, self.options.dest_archive_desc,
            self.options.arch_tags)

    def add_my_options(self):
        """Parse command line arguments for copy archive creation/population.
        """
        SoyuzScript.add_my_options(self)

        # Remove the options defined by the base class since they'll
        # mean different things to us.
        self.parser.remove_option('-a')
        self.parser.remove_option('-d')

        self.parser.add_option(
            "-a", "--architecture", dest="arch_tags", action="append",
            help="The architecture tag(s) for which to create build "
                 "records, repeat for each architecture required.")
        self.parser.add_option(
            "-d", "--destination", dest="destination_spec",
            help = (
                "The destination of the copy operation, format: "
                "\"archive-owner:archive-name:distro:suite\". "
                "Simply omit the items that are not needed."))
        self.parser.add_option(
            "-o", "--origin", dest="origin_spec",
            help = (
                "The origin of the copy operation, format: "
                "\"archive-owner:archive-name:distro:suite\". "
                "Simply omit the items that are not needed."))
        self.parser.add_option(
            "-t", "--text", dest="dest_archive_desc",
            help="The destination archive's description.")

    def _createMissingBuilds(
        self, distroseries, archive, arch_tags=None):
        """Create builds for all source packages in 'location'.

        :type distroseries: `DistroSeries`
        :param distroseries: the distro series for which to create builds.
        :type archive: `Archive`
        :param archive: the archive for which to create builds.
        :type arch_tags: list of strings
        :param arch_tags: the list of architecture tags for
            which to create builds (optional).
        """
        self.logger.info("Processing %s." % distroseries.name)

        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        architectures = list(distroseries.architectures)
        if arch_tags is not None:
            # Filter the list of DistroArchSeries so that only the ones
            # specified on the command line remain.
            architectures = [architecture for architecture in architectures
                 if architecture.architecturetag in arch_tags]

        if len(architectures) == 0:
            self.logger.info(
                "No DistroArchSeries left for %s, done." % distroseries.name)
            return

        self.logger.info(
            "Supported architectures: %s." %
            " ".join(arch_series.architecturetag
                     for arch_series in architectures))

        # Both, PENDING and PUBLISHED sources will be considered for
        # as PUBLISHED. It's part of the assumptions made in:
        # https://launchpad.net/soyuz/+spec/build-unpublished-source
        pending = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            )
        sources_published = archive.getPublishedSources(
            distroseries=distroseries, status=pending)

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
