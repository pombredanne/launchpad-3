# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
from StringIO import StringIO

from storm.expr import (
    Desc,
    Join,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.command_spawner import (
    CommandSpawner,
    OutputLineHandler,
    ReturnCodeReceiver,
    )
from lp.services.database.stormexpr import Concatenate
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.files import BinaryPackageFile
from lp.soyuz.model.publishing import BinaryPackagePublishingHistory
from lp.soyuz.model.section import Section
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


def package_name(filename):
    """Extract a package name from a debian package filename."""
    return (os.path.basename(filename).split("_"))[0]


def f_touch(*parts):
    """Touch the file named by the arguments concatenated as a path."""
    fname = os.path.join(*parts)
    open(fname, "w").close()


def safe_mkdir(path):
    """Ensures the path exists, creating it if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path, 0755)


DEFAULT_COMPONENT = "main"

CONFIG_HEADER = """
Dir
{
    ArchiveDir "%s";
    OverrideDir "%s";
    CacheDir "%s";
};

Default
{
    Packages::Compress ". gzip bzip2";
    Sources::Compress ". gzip bzip2";
    Contents::Compress "gzip";
    Translation::Compress ". gzip bzip2";
    DeLinkLimit 0;
    MaxContentsChange 12000;
    FileMode 0644;
}

TreeDefault
{
    Contents::Header "%s/contents.header";
};

"""

STANZA_TEMPLATE = """
tree "%(DISTS)s/%(DISTRORELEASEONDISK)s"
{
    FileList "%(LISTPATH)s/%(DISTRORELEASEBYFILE)s_$(SECTION)_binary-$(ARCH)";
    SourceFileList "%(LISTPATH)s/%(DISTRORELEASE)s_$(SECTION)_source";
    Sections "%(SECTIONS)s";
    Architectures "%(ARCHITECTURES)s";
    BinOverride "override.%(DISTRORELEASE)s.$(SECTION)";
    SrcOverride "override.%(DISTRORELEASE)s.$(SECTION).src";
    %(HIDEEXTRA)sExtraOverride "override.%(DISTRORELEASE)s.extra.$(SECTION)";
    Packages::Extensions "%(EXTENSIONS)s";
    BinCacheDB "packages-%(CACHEINSERT)s$(ARCH).db";
    Contents " ";
    LongDescription "%(LONGDESCRIPTION)s";
}

"""


class AptFTPArchiveFailure(Exception):
    """Failure while running apt-ftparchive."""


class FTPArchiveHandler:
    """Produces Sources and Packages files via apt-ftparchive.

    Generates file lists and configuration for apt-ftparchive, and kicks
    off generation of the Sources and Releases files.
    """

    def __init__(self, log, config, diskpool, distro, publisher):
        self.log = log
        self._config = config
        self._diskpool = diskpool
        self.distro = distro
        self.publisher = publisher

        # We need somewhere to note down where the debian-installer
        # components came from. in _di_release_components we store
        # sets, keyed by distroseries name of the component names
        # which contain debian-installer binaries.  This is filled out
        # when generating overrides and file lists, and then consumed
        # when generating apt-ftparchive configuration.
        self._di_release_components = {}

    def run(self, is_careful):
        """Do the entire generation and run process."""
        self.createEmptyPocketRequests(is_careful)
        self.log.debug("Preparing file lists and overrides.")
        self.generateOverrides(is_careful)
        self.log.debug("Generating overrides for the distro.")
        self.generateFileLists(is_careful)
        self.log.debug("Doing apt-ftparchive work.")
        apt_config_filename = self.generateConfig(is_careful)
        self.runApt(apt_config_filename)

    def _getArchitectureTags(self):
        """List tags of all architectures enabled in this distro."""
        archs = set()
        for series in self.distro.series:
            archs.update(set([
                distroarchseries.architecturetag
                for distroarchseries in series.enabled_architectures]))
        return archs

    def runApt(self, apt_config_filename):
        """Run apt-ftparchive in subprocesses.

        :raise: AptFTPArchiveFailure if any of the apt-ftparchive
            commands failed.
        """
        self.log.debug("Filepath: %s" % apt_config_filename)

        stdout_handler = OutputLineHandler(self.log.debug, "a-f: ")
        stderr_handler = OutputLineHandler(self.log.info, "a-f: ")
        base_command = [
            "apt-ftparchive",
            "--no-contents",
            "generate",
            apt_config_filename,
            ]
        spawner = CommandSpawner()

        returncodes = {}
        completion_handler = ReturnCodeReceiver()
        returncodes['all'] = completion_handler
        spawner.start(
            base_command, stdout_handler=stdout_handler,
            stderr_handler=stderr_handler,
            completion_handler=completion_handler)

        spawner.complete()
        stdout_handler.finalize()
        stderr_handler.finalize()
        failures = sorted([
            (tag, receiver.returncode)
            for tag, receiver in returncodes.iteritems()
                if receiver.returncode != 0])
        if len(failures) > 0:
            by_arch = ["%s (returned %d)" % failure for failure in failures]
            raise AptFTPArchiveFailure(
                "Failure(s) from apt-ftparchive: %s" % ", ".join(by_arch))

    #
    # Empty Pocket Requests
    #
    def createEmptyPocketRequests(self, fullpublish=False):
        """Write out empty file lists etc for pockets.

        We do this to have Packages or Sources for them even if we lack
        anything in them currently.
        """
        for distroseries in self.distro.series:
            components = [
                comp.name for comp in
                self.publisher.archive.getComponentsForSeries(distroseries)]
            for pocket in PackagePublishingPocket.items:
                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        continue
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                self.publisher.release_files_needed.add(
                    (distroseries.name, pocket))

                for comp in components:
                    self.createEmptyPocketRequest(distroseries, pocket, comp)

    def createEmptyPocketRequest(self, distroseries, pocket, comp):
        """Creates empty files for a release pocket and distroseries"""
        if pocket == PackagePublishingPocket.RELEASE:
            # organize distroseries and component pair as
            # debian-installer -> distroseries_component
            # internal map. Only the main pocket actually
            # needs these, though.
            self._di_release_components.setdefault(
                distroseries.name, set()).add(comp)
            f_touch(self._config.overrideroot,
                    ".".join(["override", distroseries.name, comp,
                              "debian-installer"]))

        suite = distroseries.getSuite(pocket)

        # Create empty override lists.
        for path in ((comp, ), ("extra", comp), (comp, "src")):
            f_touch(os.path.join(
                self._config.overrideroot,
                ".".join(("override", suite) + path)))

        # Create empty file lists.
        def touch_list(*parts):
            f_touch(os.path.join(
                self._config.overrideroot,
                "_".join((suite, ) + parts)))
        touch_list(comp, "source")

        arch_tags = [
            a.architecturetag for a in distroseries.enabled_architectures]
        for arch in arch_tags:
            # Touch more file lists for the archs.
            touch_list(comp, "binary-" + arch)
            touch_list(comp, "debian-installer", "binary-" + arch)

    #
    # Override Generation
    #
    def getSourcesForOverrides(self, distroseries, pocket):
        """Fetch override information about all published sources.

        The override information consists of tuples with 'sourcename',
        'component' and 'section' strings, in this order.

        :param distroseries: target `IDistroSeries`
        :param pocket: target `PackagePublishingPocket`

        :return: a `DecoratedResultSet` with the source override information
            tuples
        """
        # Avoid cicular imports.
        from lp.soyuz.model.publishing import SourcePackagePublishingHistory

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origins = (
            SourcePackagePublishingHistory,
            Join(Component,
                 Component.id == SourcePackagePublishingHistory.componentID),
            Join(Section,
                 Section.id == SourcePackagePublishingHistory.sectionID),
            Join(SourcePackageRelease,
                 SourcePackageRelease.id ==
                     SourcePackagePublishingHistory.sourcepackagereleaseID),
            Join(SourcePackageName,
                 SourcePackageName.id ==
                     SourcePackageRelease.sourcepackagenameID),
            )

        result_set = store.using(*origins).find(
            (SourcePackageName.name, Component.name, Section.name),
            SourcePackagePublishingHistory.archive == self.publisher.archive,
            SourcePackagePublishingHistory.distroseries == distroseries,
            SourcePackagePublishingHistory.pocket == pocket,
            SourcePackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED)

        suite = distroseries.getSuite(pocket)

        def add_suite(result):
            name, component, section = result
            return (name, suite, component, section)

        result_set.order_by(
            Desc(SourcePackagePublishingHistory.id))
        return DecoratedResultSet(result_set, add_suite)

    def getBinariesForOverrides(self, distroseries, pocket):
        """Fetch override information about all published binaries.

        The override information consists of tuples with 'binaryname',
        'component', 'section' and 'priority' strings, in this order.

        :param distroseries: target `IDistroSeries`
        :param pocket: target `PackagePublishingPocket`

        :return: a `DecoratedResultSet` with the binary override information
            tuples
        """
        # Avoid cicular imports.
        from lp.soyuz.model.binarypackagename import BinaryPackageName

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origins = (
            BinaryPackagePublishingHistory,
            Join(Component,
                 Component.id == BinaryPackagePublishingHistory.componentID),
            Join(Section,
                 Section.id == BinaryPackagePublishingHistory.sectionID),
            Join(BinaryPackageRelease,
                 BinaryPackageRelease.id ==
                     BinaryPackagePublishingHistory.binarypackagereleaseID),
            Join(BinaryPackageName,
                 BinaryPackageName.id ==
                     BinaryPackageRelease.binarypackagenameID),
            )

        architectures_ids = [arch.id for arch in distroseries.architectures]
        if len(architectures_ids) == 0:
            return EmptyResultSet()

        result_set = store.using(*origins).find(
            (BinaryPackageName.name, Component.name, Section.name,
             BinaryPackagePublishingHistory.priority),
            BinaryPackagePublishingHistory.archive == self.publisher.archive,
            BinaryPackagePublishingHistory.distroarchseriesID.is_in(
                architectures_ids),
            BinaryPackagePublishingHistory.pocket == pocket,
            BinaryPackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED)

        suite = distroseries.getSuite(pocket)

        def add_suite(result):
            name, component, section, priority = result
            return (name, suite, component, section, priority.title.lower())

        result_set.order_by(
            Desc(BinaryPackagePublishingHistory.id))
        return DecoratedResultSet(result_set, add_suite)

    def generateOverrides(self, fullpublish=False):
        """Collect packages that need overrides, and generate them."""
        for distroseries in self.distro.series:
            for pocket in PackagePublishingPocket.items:
                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        continue
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                spphs = self.getSourcesForOverrides(distroseries, pocket)
                bpphs = self.getBinariesForOverrides(distroseries, pocket)
                self.publishOverrides(spphs, bpphs)

    def publishOverrides(self, source_publications, binary_publications):
        """Output a set of override files for use in apt-ftparchive.

        Given the provided sourceoverrides and binaryoverrides, do the
        override file generation. The files will be written to
        overrideroot with filenames of the form:

            override.<distroseries>.<component>[.src]

        Attributes which must be present in sourceoverrides are:
            drname, spname, cname, sname
        Attributes which must be present in binaryoverrides are:
            drname, spname, cname, sname, priority

        The binary priority will be mapped via the values in
        dbschema.py.
        """
        # This code is tested in soyuz-set-of-uploads, and in
        # test_ftparchive.

        # overrides[distroseries][component][src/bin] = sets of tuples
        overrides = {}

        def updateOverride(packagename, suite, component, section,
                           priority=None):
            """Generates and packs tuples of data required for overriding.

            If priority is provided, it's a binary tuple; otherwise,
            it's a source tuple.

            Note that these tuples must contain /strings/, and not
            objects, because they will be printed out verbatim into the
            override files. This is why we use priority_displayed here,
            and why we get the string names of the publication's foreign
            keys to component, section, etc.
            """
            if component != DEFAULT_COMPONENT:
                section = "%s/%s" % (component, section)

            override = overrides.setdefault(suite, {})
            suboverride = override.setdefault(component, {})
            # We use sets in this structure to avoid generating
            # duplicated overrides. This issue is an outcome of the fact
            # that the PublishingHistory views select across all
            # architectures -- and therefore we have N binaries for N
            # archs.
            suboverride.setdefault('src', set())
            suboverride.setdefault('bin', set())
            suboverride.setdefault('d-i', set())
            if priority:
                # We pick up debian-installer packages here
                if section.endswith("debian-installer"):
                    # XXX: kiko 2006-08-24: This is actually redundant with
                    # what is done in createEmptyPocketRequests. However,
                    # this code does make it possible to unit test this
                    # method, so I'm sure if it should be removed.
                    self._di_release_components.setdefault(
                        suite, set()).add(component)
                    suboverride['d-i'].add((packagename, priority, section))
                else:
                    suboverride['bin'].add((packagename, priority, section))
            else:
                suboverride['src'].add((packagename, section))

        # Process huge iterations (more than 200k records) in batches.
        # See `PublishingTunableLoop`.
        self.log.debug("Calculating source overrides")

        for pub in source_publications:
            updateOverride(*pub)

        self.log.debug("Calculating binary overrides")

        for pub in binary_publications:
            updateOverride(*pub)

        # Now generate the files on disk...
        for distroseries in overrides:
            for component in overrides[distroseries]:
                self.log.debug("Generating overrides for %s/%s..." % (
                    distroseries, component))
                self.generateOverrideForComponent(overrides, distroseries,
                                                  component)

    def generateOverrideForComponent(self, overrides, distroseries,
                                     component):
        """Generates overrides for a specific component."""
        src_overrides = list(overrides[distroseries][component]['src'])
        src_overrides.sort()
        bin_overrides = list(overrides[distroseries][component]['bin'])
        bin_overrides.sort()
        di_overrides = list(overrides[distroseries][component]['d-i'])
        di_overrides.sort()

        # Set up filepaths for the overrides we read
        extra_extra_overrides = os.path.join(self._config.miscroot,
            "more-extra.override.%s.%s" % (distroseries, component))
        if not os.path.exists(extra_extra_overrides):
            unpocketed_series = "-".join(distroseries.split('-')[:-1])
            extra_extra_overrides = os.path.join(self._config.miscroot,
                "more-extra.override.%s.%s" % (unpocketed_series, component))
        # And for the overrides we write out
        main_override = os.path.join(self._config.overrideroot,
                                     "override.%s.%s" %
                                     (distroseries, component))
        ef_override = os.path.join(self._config.overrideroot,
                                   "override.%s.extra.%s" %
                                   (distroseries, component))
        di_override = os.path.join(self._config.overrideroot,
                                   "override.%s.%s.debian-installer" %
                                   (distroseries, component))
        source_override = os.path.join(self._config.overrideroot,
                                       "override.%s.%s.src" %
                                       (distroseries, component))

        # Start to write the files out
        ef = open(ef_override, "w")
        f = open(main_override, "w")
        for package, priority, section in bin_overrides:
            origin = "\t".join([package, "Origin", "Ubuntu"])
            bugs = "\t".join([package, "Bugs",
                        "https://bugs.launchpad.net/ubuntu/+filebug"])

            f.write("\t".join((package, priority, section)))
            f.write("\n")
            # XXX: dsilvers 2006-08-23 bug=3900:
            # This needs to be made databaseish and be actually managed within
            # Launchpad. (Or else we need to change the ubuntu as appropriate
            # and look for bugs addresses etc in launchpad.
            ef.write(origin)
            ef.write("\n")
            ef.write(bugs)
            ef.write("\n")
        f.close()

        if os.path.exists(extra_extra_overrides):
            # XXX kiko 2006-08-24: This is untested.
            eef = open(extra_extra_overrides, "r")
            extras = {}
            for line in eef:
                line = line.strip()
                if not line:
                    continue
                (package, header, value) = line.split(None, 2)
                pkg_extras = extras.setdefault(package, {})
                header_values = pkg_extras.setdefault(header, [])
                header_values.append(value)
            eef.close()
            for pkg, headers in extras.items():
                for header, values in headers.items():
                    ef.write("\t".join([pkg, header, ", ".join(values)]))
                    ef.write("\n")
            # XXX: dsilvers 2006-08-23 bug=3900: As above,
            # this needs to be integrated into the database at some point.
        ef.close()

        def _outputSimpleOverrides(filename, overrides):
            sf = open(filename, "w")
            for tup in overrides:
                sf.write("\t".join(tup))
                sf.write("\n")
            sf.close()

        _outputSimpleOverrides(source_override, src_overrides)
        if di_overrides:
            _outputSimpleOverrides(di_override, di_overrides)

    #
    # File List Generation
    #
    def getSourceFiles(self, distroseries, pocket):
        """Fetch publishing information about all published source files.

        The publishing information consists of tuples with 'sourcename',
        'filename' and 'component' strings, in this order.

        :param distroseries: target `IDistroSeries`
        :param pocket: target `PackagePublishingPocket`

        :return: a `DecoratedResultSet` with the source files information
            tuples.
        """

        # Avoid circular imports.
        from lp.soyuz.model.publishing import SourcePackageFilePublishing

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.using(SourcePackageFilePublishing).find(
            (SourcePackageFilePublishing.sourcepackagename,
             SourcePackageFilePublishing.libraryfilealiasfilename,
             SourcePackageFilePublishing.componentname),
            SourcePackageFilePublishing.distribution == self.distro,
            SourcePackageFilePublishing.archive == self.publisher.archive,
            SourcePackageFilePublishing.distroseriesname == distroseries.name,
            SourcePackageFilePublishing.pocket == pocket,
            SourcePackageFilePublishing.publishingstatus ==
                PackagePublishingStatus.PUBLISHED)

        suite = distroseries.getSuite(pocket)

        def add_suite(result):
            name, filename, component = result
            return (name, suite, filename, component)

        result_set.order_by(
            Desc(SourcePackageFilePublishing.id))
        return DecoratedResultSet(result_set, add_suite)

    def getBinaryFiles(self, distroseries, pocket):
        """Fetch publishing information about all published binary files.

        The publishing information consists of tuples with 'sourcename',
        'filename', 'component' and 'architecture' strings, in this order.

        :param distroseries: target `IDistroSeries`
        :param pocket: target `PackagePublishingPocket`

        :return: a `DecoratedResultSet` with the binary files information
            tuples.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        columns = (
            SourcePackageName.name,
            LibraryFileAlias.filename,
            Component.name,
            Concatenate("binary-", DistroArchSeries.architecturetag),
            )
        join_conditions = [
            BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID,
            BinaryPackageFile.binarypackagereleaseID ==
                BinaryPackagePublishingHistory.binarypackagereleaseID,
            BinaryPackageBuild.id == BinaryPackageRelease.buildID,
            SourcePackageRelease.id ==
                BinaryPackageBuild.source_package_release_id,
            SourcePackageName.id == SourcePackageRelease.sourcepackagenameID,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            DistroArchSeries.id ==
                BinaryPackagePublishingHistory.distroarchseriesID,
            Component.id == BinaryPackagePublishingHistory.componentID,
            ]
        select_conditions = [
            BinaryPackagePublishingHistory.dateremoved == None,
            DistroArchSeries.distroseriesID == distroseries.id,
            BinaryPackagePublishingHistory.archive == self.publisher.archive,
            BinaryPackagePublishingHistory.pocket == pocket,
            BinaryPackagePublishingHistory.status ==
                PackagePublishingStatus.PUBLISHED,
            ]

        suite = distroseries.getSuite(pocket)

        def add_suite(result):
            name, filename, component, architecture = result
            return (name, suite, filename, component, architecture)

        result_set = store.find(
            columns, *(join_conditions + select_conditions))
        result_set.order_by(
            BinaryPackagePublishingHistory.id, BinaryPackageFile.id)
        return DecoratedResultSet(result_set, add_suite)

    def generateFileLists(self, fullpublish=False):
        """Collect currently published FilePublishings and write filelists."""
        for distroseries in self.distro.series:
            for pocket in PackagePublishingPocket.items:
                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        continue
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue
                spps = self.getSourceFiles(distroseries, pocket)
                pps = self.getBinaryFiles(distroseries, pocket)
                self.publishFileLists(spps, pps)

    def publishFileLists(self, sourcefiles, binaryfiles):
        """Collate the set of source files and binary files provided and
        write out all the file list files for them.

        listroot/distroseries_component_source
        listroot/distroseries_component_binary-archname
        """
        filelist = {}

        def updateFileList(sourcepackagename, suite, filename, component,
                           architecturetag=None):
            ondiskname = self._diskpool.pathFor(
                            component, sourcepackagename, filename)
            this_file = filelist.setdefault(suite, {})
            this_file.setdefault(component, {})
            if architecturetag is None:
                architecturetag = "source"
            this_file[component].setdefault(architecturetag, [])
            this_file[component][architecturetag].append(ondiskname)

        # Process huge iterations (more than 200K records) in batches.
        # See `PublishingTunableLoop`.
        self.log.debug("Calculating source filelist.")

        for file_details in sourcefiles:
            updateFileList(*file_details)

        self.log.debug("Calculating binary filelist.")

        for file_details in binaryfiles:
            updateFileList(*file_details)

        for suite, components in filelist.iteritems():
            self.log.debug("Writing file lists for %s" % suite)
            series, pocket = self.distro.getDistroSeriesAndPocket(suite)
            for component, architectures in components.iteritems():
                for architecture, file_names in architectures.iteritems():
                    # XXX wgrant 2010-10-06: There must be a better place to
                    # do this.
                    if architecture == "source":
                        enabled = True
                    else:
                        # The "[7:]" strips the "binary-" prefix off the
                        # architecture names we get here.
                        das = series.getDistroArchSeries(architecture[7:])
                        enabled = das.enabled
                    if enabled:
                        self.writeFileList(
                            architecture, file_names, suite, component)

    def writeFileList(self, arch, file_names, dr_pocketed, component):
        """Outputs a file list for a series and architecture.

        Also outputs a debian-installer file list if necessary.
        """
        files = []
        di_files = []
        f_path = os.path.join(self._config.overrideroot,
                              "%s_%s_%s" % (dr_pocketed, component, arch))
        f = file(f_path, "w")
        for name in file_names:
            if name.endswith(".udeb"):
                # Once again, note that this component in this
                # distroseries has d-i elements
                self._di_release_components.setdefault(
                    dr_pocketed, set()).add(component)
                # And note the name for output later
                di_files.append(name)
            else:
                files.append(name)
        files.sort(key=package_name)
        f.write("\n".join(files))
        f.write("\n")
        f.close()

        if len(di_files):
            # Once again, some d-i stuff to write out...
            self.log.debug("Writing d-i file list for %s/%s/%s" % (
                dr_pocketed, component, arch))
            di_overrides = os.path.join(self._config.overrideroot,
                                        "%s_%s_debian-installer_%s" %
                                        (dr_pocketed, component, arch))
            f = open(di_overrides, "w")
            di_files.sort(key=package_name)
            f.write("\n".join(di_files))
            f.write("\n")
            f.close()

    #
    # Config Generation
    #
    def generateConfig(self, fullpublish=False):
        """Generate an APT FTPArchive configuration from the provided
        config object and the paths we either know or have given to us.

        If fullpublish is true, we generate config for everything.

        Otherwise, we aim to limit our config to certain distroseries
        and pockets. By default, we will exclude release pockets for
        released series, and in addition we exclude any pocket not
        explicitly marked as dirty. dirty_pockets must be a nested
        dictionary of booleans, keyed by distroseries.name then pocket.
        """
        apt_config = StringIO()
        apt_config.write(CONFIG_HEADER % (self._config.archiveroot,
                                          self._config.overrideroot,
                                          self._config.cacheroot,
                                          self._config.miscroot))

        # confixtext now contains a basic header. Add a dists entry for
        # each of the distroseries we've touched
        for distroseries in self.distro.series:
            for pocket in PackagePublishingPocket.items:

                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        self.log.debug("Skipping a-f stanza for %s/%s" %
                                           (distroseries.name, pocket.name))
                        continue
                    self.publisher.checkDirtySuiteBeforePublishing(
                        distroseries, pocket)
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                self.generateConfigForPocket(apt_config, distroseries, pocket)

        # And now return that string.
        s = apt_config.getvalue()
        apt_config.close()

        apt_config_filename = os.path.join(self._config.miscroot, "apt.conf")
        fp = file(apt_config_filename, "w")
        fp.write(s)
        fp.close()
        return apt_config_filename

    def generateConfigForPocket(self, apt_config, distroseries, pocket):
        """Generates the config stanza for an individual pocket."""
        suite = distroseries.getSuite(pocket)

        archs = [
            a.architecturetag for a in distroseries.enabled_architectures]
        comps = [
            comp.name for comp in
            self.publisher.archive.getComponentsForSeries(distroseries)]

        self.log.debug("Generating apt config for %s" % suite)
        apt_config.write(STANZA_TEMPLATE % {
                         "LISTPATH": self._config.overrideroot,
                         "DISTRORELEASE": suite,
                         "DISTRORELEASEBYFILE": suite,
                         "DISTRORELEASEONDISK": suite,
                         "ARCHITECTURES": " ".join(archs + ["source"]),
                         "SECTIONS": " ".join(comps),
                         "EXTENSIONS": ".deb",
                         "CACHEINSERT": "",
                         "DISTS": os.path.basename(self._config.distsroot),
                         "HIDEEXTRA": "",
                         "LONGDESCRIPTION":
                             "true" if distroseries.include_long_descriptions
                                    else "false",
                         })

        if archs and suite in self._di_release_components:
            for component in self._di_release_components[suite]:
                apt_config.write(STANZA_TEMPLATE % {
                    "LISTPATH": self._config.overrideroot,
                    "DISTRORELEASEONDISK": "%s/%s" % (suite, component),
                    "DISTRORELEASEBYFILE": "%s_%s" % (suite, component),
                    "DISTRORELEASE": "%s.%s" % (suite, component),
                    "ARCHITECTURES": " ".join(archs),
                    "SECTIONS": "debian-installer",
                    "EXTENSIONS": ".udeb",
                    "CACHEINSERT": "debian-installer-",
                    "DISTS": os.path.basename(self._config.distsroot),
                    "HIDEEXTRA": "// ",
                    "LONGDESCRIPTION": "true",
                    })

        # XXX: 2006-08-24 kiko: Why do we do this directory creation here?
        for comp in comps:
            component_path = os.path.join(
                self._config.distsroot, suite, comp)
            base_paths = [component_path]
            if suite in self._di_release_components:
                if comp in self._di_release_components[suite]:
                    base_paths.append(os.path.join(component_path,
                                                   "debian-installer"))
            for base_path in base_paths:
                if "debian-installer" not in base_path:
                    safe_mkdir(os.path.join(base_path, "source"))
                    if not distroseries.include_long_descriptions:
                        safe_mkdir(os.path.join(base_path, "i18n"))
                for arch in archs:
                    safe_mkdir(os.path.join(base_path, "binary-" + arch))
