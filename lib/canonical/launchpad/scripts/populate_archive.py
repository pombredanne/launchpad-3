# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Create a copy archive (if needed) and populate it with packages."""


__metaclass__ = type
__all__ = [
    'ArchivePopulator',
    ]


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.components.packagelocation import (
    build_package_location)
from canonical.launchpad.interfaces import PackagePublishingStatus
from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, IArchiveSet)
from canonical.launchpad.interfaces.archivearch import IArchiveArchSet
from canonical.launchpad.interfaces.component import IComponentSet
from canonical.launchpad.interfaces.packagecloner import IPackageCloner
from canonical.launchpad.interfaces.packagecopyrequest import (
    IPackageCopyRequestSet)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.processor import IProcessorFamilySet
from canonical.launchpad.scripts.ftpmasterbase import (
    SoyuzScript, SoyuzScriptError)
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.webapp.interfaces import NotFoundError


class ArchivePopulator(SoyuzScript):
    """
    Create a copy archive and populate it with packages.

    The logic needed to create a copy archive, populate it with source
    packages and instantiate the builds required.

    Please note: the destination copy archive must not exist yet. Otherwise
    the script will abort with an error.
    """

    usage = __doc__
    description = (
        'Create a copy archive and populate it with packages and build '
        'records.')

    def populateArchive(
        self, from_archive, from_distribution, from_suite, from_user,
        component, to_distribution, to_suite, to_archive, to_user, reason,
        include_binaries, proc_families):
        """Create archive, populate it with packages and builds.

        Please note: if a component was specified for the origin then the
        same component must be used for the destination.

        :param from_archive: the (optional) origin archive name.
        :param from_distribution: the origin's distribution.
        :param from_suite: the origin's suite.
        :param from_user: the name of the origin PPA's owner.
        :param component: the origin's component.

        :param to_distribution: destination distribution.
        :param to_suite: destination suite.

        :param to_archive: destination copy archive name.
        :param to_user: destination archive owner name.
        :param reason: reason for the package copy operation.

        :param include_binaries: whether binaries should be copied as well.
        :param proc_families: processor families for which to create builds.
        """
        def loadProcessorFamilies(proc_family_names):
            """Load processor families for specified family names."""
            proc_family_set = getUtility(IProcessorFamilySet)
            proc_families = set()
            for name in proc_family_names:
                proc_family = proc_family_set.getByName(name)
                if proc_family is None:
                    raise SoyuzScriptError(
                        "Invalid processor family: '%s'" % name)
                else:
                    proc_families.add(proc_family)

            return proc_families

        def set_archive_architectures(archive, proc_families):
            """Associate the archive with the processor families."""
            aa_set = getUtility(IArchiveArchSet)
            for proc_family in proc_families:
                ignore_this = aa_set.new(archive, proc_family)

        def build_location(distro, suite, component):
            """Build and return package location."""
            location = build_package_location(distro, suite=suite)
            if component is not None:
                try:
                    the_component = getUtility(IComponentSet)[component]
                except NotFoundError, e:
                    raise SoyuzScriptError(
                        "Invalid component name: '%s'" % component)
                location.component = the_component
            return location

        archive_set = getUtility(IArchiveSet)
        # Build the origin package location.
        the_origin = build_location(from_distribution, from_suite, component)
        # Use an origin archive if specified and existent.
        if from_archive is not None:
            origin_archive = archive_set.getByDistroAndName(
                the_origin.distribution, from_archive)
            if origin_archive is not None:
                the_origin.archive = origin_archive
            else:
                raise SoyuzScriptError(
                    "Origin archive does not exist: '%s'" % from_archive)
        # Use a PPA if specified and existent.
        if from_user is not None:
            origin_archive = archive_set.getPPAByDistributionAndOwnerName(
                the_origin.distribution, from_user)
            if origin_archive is not None:
                the_origin.archive = origin_archive
            else:
                raise SoyuzScriptError(
                    "No PPA for user: '%s'" % from_user)

        # Build the destination package location.
        the_destination = build_location(to_distribution, to_suite, component)

        registrant = getUtility(IPersonSet).getByName(to_user)
        if registrant is None:
            raise SoyuzScriptError("Invalid user name: '%s'" % to_user)

        # First try to access the destination copy archive.
        copy_archive = getUtility(IArchiveSet).getByDistroAndName(
            the_destination.distribution, to_archive)

        merge_copy = False
        # No copy archive with the specified name found, create one.
        if copy_archive is None:
            # First load the processor families for the specified family names
            # from the database. This will fail if an invalid processor family
            # name was specified on the command line; that's why it should be
            # done before creating the copy archive.
            proc_families = loadProcessorFamilies(self.options.proc_families)
            copy_archive = getUtility(IArchiveSet).new(
                ArchivePurpose.COPY, registrant, to_archive,
                the_destination.distribution, reason)
            the_destination.archive = copy_archive
            # Associate the newly created copy archive with the processor
            # families specified by the user.
            set_archive_architectures(copy_archive, proc_families)
        else:
            # The copy archive exists already, get the associated processor
            # families.
            def get_family(archivearch):
                """Extract the processor family from an `IArchiveArch`."""
                return removeSecurityProxy(archivearch).processorfamily

            proc_families = [
                get_family(archivearch) for archivearch
                in getUtility(IArchiveArchSet).getByArchive(copy_archive)]
            merge_copy = True

        the_destination.archive = copy_archive
        # Now instantiate the package copy request that will capture the
        # archive population parameters in the database.
        getUtility(IPackageCopyRequestSet).new(
            the_origin, the_destination, registrant,
            copy_binaries=include_binaries, reason=unicode(reason))

        # Clone the source packages. We currently do not support the copying
        # of binary packages. It's a forthcoming feature.
        pkg_cloner = getUtility(IPackageCloner)

        if merge_copy == True:
            pkg_cloner.mergeCopy(the_origin, the_destination)
        else:
            pkg_cloner.clonePackages(the_origin, the_destination)

        # Create builds for the cloned packages.
        self._createMissingBuilds(
            the_destination.distroseries, the_destination.archive,
            proc_families)

    def mainTask(self):
        """Main function entry point."""
        def not_specified(option):
            return (option is None or option == '')
        def specified(option):
            return not (option is None or option == '')

        options = self.options

        if not_specified(options.proc_families):
            raise SoyuzScriptError(
                "error: processor families not specified.")

        if not_specified(options.from_distribution):
            raise SoyuzScriptError(
                "error: origin distribution not specified.")

        if not_specified(options.to_distribution):
            raise SoyuzScriptError(
                "error: destination distribution not specified.")

        if not_specified(options.to_user):
            raise SoyuzScriptError("error: copy archive owner not specified.")
        if not_specified(options.to_archive):
            raise SoyuzScriptError(
                "error: destination copy archive not specified.")
        if not valid_name(options.to_archive):
            raise SoyuzScriptError(
                "Invalid archive name: '%s'" % options.to_archive)
        if not_specified(options.reason):
            raise SoyuzScriptError(
                "error: reason for copy operation not specified.")

        if options.include_binaries == True:
            raise SoyuzScriptError(
                "error: copying of binary packages is not supported yet.")

        if specified(options.from_user) and specified(options.from_archive):
            raise SoyuzScriptError(
                "error: cannot specify both the origin PPA owner and name")

        self.populateArchive(
            options.from_archive, options.from_distribution,
            options.from_suite, options.from_user, options.component,
            options.to_distribution, options.to_suite, options.to_archive,
            options.to_user, options.reason, options.include_binaries,
            options.proc_families)

    def add_my_options(self):
        """Parse command line arguments for copy archive creation/population.
        """
        SoyuzScript.add_my_options(self)

        self.parser.remove_option('-a')

        self.parser.add_option(
            "-a", "--architecture", dest="proc_families", action="append",
            help="The processor families for which to create build "
                 "records, repeat for each architecture required.")
        self.parser.add_option(
            "-b", "--include-binaries", dest="include_binaries",
            default=False, action="store_true",
            help='Whether to copy related binaries or not.')

        self.parser.add_option(
            '--from-archive', dest='from_archive', default=None,
            action='store', help='Origin archive name.')
        self.parser.add_option(
            '--from-distribution', dest='from_distribution',
            default='ubuntu', action='store',
            help='Origin distribution name.')
        self.parser.add_option(
            '--from-suite', dest='from_suite', default=None,
            action='store', help='Origin suite name.')
        self.parser.add_option(
            '--from-user', dest='from_user', default=None,
            action='store', help='Origin PPA owner name.')

        self.parser.add_option(
            '--to-distribution', dest='to_distribution',
            default='ubuntu', action='store',
            help='Destination distribution name.')
        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Destination suite name.')

        self.parser.add_option(
            '--to-archive', dest='to_archive', default=None,
            action='store', help='Destination archive name.')

        self.parser.add_option(
            '--to-user', dest='to_user', default=None,
            action='store', help='Destination user name.')

        self.parser.add_option(
            "--reason", dest="reason",
            help="The reason for this packages copy operation.")

    def _createMissingBuilds(
        self, distroseries, archive, proc_families):
        """Create builds for all cloned source packages.

        :param distroseries: the distro series for which to create builds.
        :param archive: the archive for which to create builds.
        :param proc_families: the list of processor families for
            which to create builds (optional).
        """
        self.logger.info("Processing %s." % distroseries.name)

        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        architectures = list(distroseries.architectures)

        # Filter the list of DistroArchSeries so that only the ones
        # specified on the command line remain.
        architectures = [architecture for architecture in architectures
             if architecture.processorfamily in proc_families]

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
            """Return the source package name for a publishing record."""
            return pub.sourcepackagerelease.sourcepackagename.name

        for pubrec in sources_published:
            builds = pubrec.createMissingBuilds(
                architectures_available=architectures, logger=self.logger)
            if len(builds) == 0:
                self.logger.info("%s has no builds." % get_spn(pubrec))
            else:
                self.logger.info(
                    "%s has %s build(s)." % (get_spn(pubrec), len(builds)))
            self.txn.commit()
