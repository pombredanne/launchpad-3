# (C) Canonical Software Ltd. 2004-2006, all rights reserved.

import os
from select import select
import subprocess
from StringIO import StringIO

from canonical.database.sqlbase import expire_from_cache, sqlvalues
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory,
    SourcePackageFilePublishing, BinaryPackageFilePublishing)
from canonical.launchpad.interfaces import (
    PackagePublishingStatus, PackagePublishingPocket, pocketsuffix)


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


# XXX malcc 2006-09-20 : Move this somewhere useful. If generalised with
# timeout handling and stderr passthrough, could be a single method used for
# this and the similar requirement in test_on_merge.py.
def run_subprocess_with_logging(process_and_args, log, prefix):
    """Run a subprocess, gathering the output as it runs and logging it.

    process_and_args is a list containing the process to run and the
    arguments for it, just as passed in the first argument to
    subprocess.Popen.

    log is a logger to pass the output we gather.

    prefix is a prefix to attach to each line of output when we log it.
    """
    proc = subprocess.Popen(process_and_args,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            close_fds=True)
    proc.stdin.close()
    open_readers = set([proc.stdout, proc.stderr])
    buf = ""
    while open_readers:
        rlist, wlist, xlist = select(open_readers, [], [])

        for reader in rlist:
            chunk = os.read(reader.fileno(), 1024)
            if chunk == "":
                open_readers.remove(reader)
                if buf:
                    log.debug(buf)
            else:
                buf += chunk
                lines = buf.split("\n")
                for line in lines[0:-1]:
                    log.debug("%s%s" % (prefix, line))
                buf = lines[-1]

    ret = proc.wait()
    return ret


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
}

"""


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
        self.release_files_needed = {}

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

    def runApt(self, apt_config_filename):
        """Run apt in a subprocess and verify its return value. """
        self.log.debug("Filepath: %s" % apt_config_filename)
        ret = run_subprocess_with_logging(["apt-ftparchive", "--no-contents",
                                           "generate", apt_config_filename],
                                          self.log, "a-f: ")
        if ret:
            raise AssertionError(
                "Failure from apt-ftparchive. Return code %s" % ret)
        return ret

    #
    # Empty Pocket Requests
    #

    def createEmptyPocketRequests(self, fullpublish=False):
        """Write out empty file lists etc for pockets.

        We do this to have Packages or Sources for them even if we lack
        anything in them currently.
        """
        # XXX: kiko 2006-08-24: suffix is completely unnecessary here. Just
        # iterate over the pockets, and do the suffix check inside
        # createEmptyPocketRequest; that would also allow us to replace
        # the == "" check we do there by a RELEASE match
        for distroseries in self.distro:
            components = self._config.componentsForSeries(distroseries.name)
            for pocket, suffix in pocketsuffix.items():
                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        continue
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                for comp in components:
                    self.createEmptyPocketRequest(distroseries, suffix, comp)

    def requestReleaseFile(self, suite_name, component_name, arch_name):
        """Request Release file generation for given context.

        'suite_name', 'component_name' and 'arch_name' will be organised as
        a dictionary (self.release_files_needed) keyed by 'suite_name' which
        value will be another dictionary keyed by 'component_name' and
        containing a set of 'arch_name's as value.
        """
        suite_special = self.release_files_needed.setdefault(
            suite_name, {})
        suite_component_special = suite_special.setdefault(
            component_name, set())
        suite_component_special.add(arch_name)

    def createEmptyPocketRequest(self, distroseries, suffix, comp):
        """Creates empty files for a release pocket and distroseries"""
        full_distroseries_name = distroseries.name + suffix
        arch_tags = self._config.archTagsForSeries(distroseries.name)

        if suffix == "":
            # organize distroseries and component pair as
            # debian-installer -> distroseries_component
            # internal map. Only the main pocket actually
            # needs these, though.
            self._di_release_components.setdefault(
                distroseries.name, set()).add(comp)
            f_touch(self._config.overrideroot,
                    ".".join(["override", distroseries.name, comp,
                              "debian-installer"]))

        # Touch the source file lists and override files
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distroseries_name, comp]))
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distroseries_name, "extra", comp]))
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distroseries_name, comp, "src"]))

        dr_comps = self.release_files_needed.setdefault(
            full_distroseries_name, {})

        f_touch(self._config.overrideroot,
                "_".join([full_distroseries_name, comp, "source"]))
        dr_comps.setdefault(comp, set()).add("source")

        for arch in arch_tags:
            # organize dr/comp/arch into temporary binary
            # archive map for the architecture in question.
            dr_special = self.release_files_needed.setdefault(
                full_distroseries_name, {})
            dr_special.setdefault(comp, set()).add("binary-"+arch)

            # Touch more file lists for the archs.
            f_touch(self._config.overrideroot,
                    "_".join([full_distroseries_name, comp, "binary-"+arch]))
            f_touch(self._config.overrideroot,
                    "_".join([full_distroseries_name, comp,
                              "debian-installer", "binary-"+arch]))

    #
    # Override Generation
    #

    def getSourcesForOverrides(self, distroseries, pocket):
        """Return SelectResults containing SourcePackagePublishingHistory."""
        return SourcePackagePublishingHistory.select(
            """
            SourcePackagePublishingHistory.distroseries = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.pocket = %s AND
            SourcePackagePublishingHistory.status = %s
            """ % sqlvalues(distroseries,
                            self.publisher.archive,
                            pocket,
                            PackagePublishingStatus.PUBLISHED),
            prejoins=["sourcepackagerelease.sourcepackagename"],
            orderBy="id")

    def getBinariesForOverrides(self, distroseries, pocket):
        """Return SelectResults containing BinaryPackagePublishingHistory."""
        return BinaryPackagePublishingHistory.select(
            """
            BinaryPackagePublishingHistory.distroarchseries =
            DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.pocket = %s AND
            BinaryPackagePublishingHistory.status = %s
            """ % sqlvalues(distroseries,
                            self.publisher.archive,
                            pocket,
                            PackagePublishingStatus.PUBLISHED),
            prejoins=["binarypackagerelease.binarypackagename"],
            orderBy="id", clauseTables=["DistroArchSeries"])

    def generateOverrides(self, fullpublish=False):
        """Collect packages that need overrides, and generate them."""
        for distroseries in self.distro.serieses:
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

        def updateOverride(publication, packagename, distroseriesname,
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
            distroseriesname += pocketsuffix[publication.pocket]
            component = publication.component.name
            section = publication.section.name
            if component != DEFAULT_COMPONENT:
                section = "%s/%s" % (component, section)

            override = overrides.setdefault(distroseriesname, {})
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
                priority_displayed = priority.title.lower()
                # We pick up debian-installer packages here
                if section.endswith("debian-installer"):
                    # XXX: kiko 2006-08-24: This is actually redundant with
                    # what is done in createEmptyPocketRequests. However,
                    # this code does make it possible to unit test this
                    # method, so I'm sure if it should be removed.
                    self._di_release_components.setdefault(
                        distroseriesname, set()).add(component)
                    suboverride['d-i'].add((packagename, priority_displayed,
                                            section))
                else:
                    suboverride['bin'].add((packagename, priority_displayed,
                                            section))
            else:
                suboverride['src'].add((packagename, section))

        for pub in source_publications:
            updateOverride(pub, pub.sourcepackagerelease.name,
                           pub.distroseries.name)
            expire_from_cache(pub.sourcepackagerelease)
            expire_from_cache(pub)

        for pub in binary_publications:
            updateOverride(pub, pub.binarypackagerelease.name,
                           pub.distroarchseries.distroseries.name,
                           pub.priority)
            expire_from_cache(pub.binarypackagerelease)
            expire_from_cache(pub)

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
        f = open(main_override , "w")
        for package, priority, section in bin_overrides:
            origin = "\t".join([package, "Origin", "Ubuntu"])
            bugs = "\t".join([package, "Bugs",
                        "mailto:ubuntu-users@lists.ubuntu.com"])

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

    def generateFileLists(self, fullpublish=False):
        """Collect currently published FilePublishings and write filelists."""
        for distroseries in self.distro.serieses:
            for pocket in pocketsuffix:
                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        continue
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                spps = SourcePackageFilePublishing.select(
                    """
                    distribution = %s AND
                    archive = %s AND
                    publishingstatus = %s AND
                    pocket = %s AND
                    distroseriesname = %s
                    """ % sqlvalues(self.distro,
                                    self.publisher.archive,
                                    PackagePublishingStatus.PUBLISHED,
                                    pocket,
                                    distroseries.name),
                    orderBy="id")

                pps = BinaryPackageFilePublishing.select(
                    """
                    distribution = %s AND
                    archive = %s AND
                    publishingstatus = %s AND
                    pocket = %s AND
                    distroseriesname = %s
                    """ % sqlvalues(self.distro,
                                    self.publisher.archive,
                                    PackagePublishingStatus.PUBLISHED,
                                    pocket,
                                    distroseries.name),
                    orderBy="id")

                self.publishFileLists(spps, pps)

    def publishFileLists(self, sourcefiles, binaryfiles):
        """Collate the set of source files and binary files provided and
        write out all the file list files for them.

        listroot/distroseries_component_source
        listroot/distroseries_component_binary-archname
        """
        filelist = {}

        def updateFileList(fp, architecturetag=None):
            distroseriesname = fp.distroseriesname
            dr_pocketed = distroseriesname + pocketsuffix[fp.pocket]
            component = fp.componentname
            filename = fp.libraryfilealiasfilename
            sourcepackagename = fp.sourcepackagename
            ondiskname = self._diskpool.pathFor(
                            component, sourcepackagename, filename)

            this_file = filelist.setdefault(dr_pocketed, {})
            this_file.setdefault(component, {})
            if architecturetag:
                this_file[component].setdefault(architecturetag, [])
                this_file[component][architecturetag].append(ondiskname)
            else:
                this_file[component].setdefault('source', [])
                this_file[component]['source'].append(ondiskname)

        self.log.debug("Collating lists of source files...")
        for file_publishing in sourcefiles:
            updateFileList(file_publishing)

        self.log.debug("Collating lists of binary files...")
        for file_publishing in binaryfiles:
            architecturetag = "binary-%s" % file_publishing.architecturetag
            updateFileList(file_publishing, architecturetag)

        for dr_pocketed, components in filelist.items():
            self.log.debug("Writing file lists for %s" % dr_pocketed)
            for component, architectures in components.items():
                for architecture, file_names in architectures.items():
                    self.writeFileList(architecture, file_names,
                                             dr_pocketed, component)

    def writeFileList(self, arch, file_names, dr_pocketed, component):
        """Outputs a file list for a series and architecture.

        Also outputs a debian-installer file list if necessary.
        """
        self.release_files_needed.setdefault(
            dr_pocketed, {}).setdefault(component, set()).add(arch)

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

        Otherwise, we aim to limit our config to certain distroserieses
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
        # each of the distroserieses we've touched
        for distroseries_name in self._config.distroSeriesNames():
            distroseries = self.distro[distroseries_name]
            for pocket in pocketsuffix:

                if not fullpublish:
                    if not self.publisher.isDirty(distroseries, pocket):
                        self.log.debug("Skipping a-f stanza for %s/%s" %
                                           (distroseries_name, pocket.name))
                        continue
                    self.publisher.checkDirtySuiteBeforePublishing(
                        distroseries, pocket)
                else:
                    if not self.publisher.isAllowed(distroseries, pocket):
                        continue

                subtext = self.generateConfigForPocket(
                    apt_config, distroseries, distroseries_name, pocket)

        # And now return that string.
        s = apt_config.getvalue()
        apt_config.close()

        apt_config_filename = os.path.join(self._config.miscroot, "apt.conf")
        fp = file(apt_config_filename, "w")
        fp.write(s)
        fp.close()
        return apt_config_filename

    def generateConfigForPocket(self, apt_config, distroseries,
                                distroseries_name, pocket):
        """Generates the config stanza for an individual pocket."""
        dr_pocketed = distroseries_name + pocketsuffix[pocket]

        # XXX kiko 2006-08-24: I have no idea what the code below is meant
        # to do -- it appears to be a rehash of createEmptyPocketRequests.
        archs = self._config.archTagsForSeries(distroseries_name)
        comps = self._config.componentsForSeries(distroseries_name)
        for comp in comps:
            comp_path = os.path.join(self._config.overrideroot,
                                     "_".join([dr_pocketed, comp, "source"]))
            if not os.path.exists(comp_path):
                # Create empty files so that even if we don't output
                # anything here apt-ftparchive will DTRT
                f_touch(comp_path)
                f_touch(self._config.overrideroot,
                        ".".join(["override", dr_pocketed, comp]))
                f_touch(self._config.overrideroot,
                        ".".join(["override", dr_pocketed, comp, "src"]))

        if len(comps) == 0:
            self.log.debug("Did not find any components to create config "
                           "for %s" % dr_pocketed)
            return

        # Second up, pare archs down as appropriate
        for arch in archs:
            # XXX: kiko 2006-08-24: why is it comps[0] here?
            arch_path = os.path.join(self._config.overrideroot,
                "_".join([dr_pocketed, comps[0], "binary-"+arch]))
            if not os.path.exists(arch_path):
                # Create an empty file if we don't have one so that
                # apt-ftparchive will dtrt.
                f_touch(arch_path)
        # XXX kiko 2006-08-24: End uncomprehensible code.

        self.log.debug("Generating apt config for %s" % dr_pocketed)
        apt_config.write(STANZA_TEMPLATE % {
                         "LISTPATH": self._config.overrideroot,
                         "DISTRORELEASE": dr_pocketed,
                         "DISTRORELEASEBYFILE": dr_pocketed,
                         "DISTRORELEASEONDISK": dr_pocketed,
                         "ARCHITECTURES": " ".join(archs + ["source"]),
                         "SECTIONS": " ".join(comps),
                         "EXTENSIONS": ".deb",
                         "CACHEINSERT": "",
                         "DISTS": os.path.basename(self._config.distsroot),
                         "HIDEEXTRA": ""})

        if archs and dr_pocketed in self._di_release_components:
            for component in self._di_release_components[dr_pocketed]:
                apt_config.write(STANZA_TEMPLATE % {
                    "LISTPATH": self._config.overrideroot,
                    "DISTRORELEASEONDISK": "%s/%s" % (dr_pocketed, component),
                    "DISTRORELEASEBYFILE": "%s_%s" % (dr_pocketed, component),
                    "DISTRORELEASE": "%s.%s" % (dr_pocketed, component),
                    "ARCHITECTURES": " ".join(archs),
                    "SECTIONS": "debian-installer",
                    "EXTENSIONS": ".udeb",
                    "CACHEINSERT": "debian-installer-",
                    "DISTS": os.path.basename(self._config.distsroot),
                    "HIDEEXTRA": "// "
                    })

        # XXX: 2006-08-24 kiko: Why do we do this directory creation here?
        for comp in comps:
            component_path = os.path.join(self._config.distsroot,
                                          dr_pocketed, comp)
            base_paths = [component_path]
            if dr_pocketed in self._di_release_components:
                if comp in self._di_release_components[dr_pocketed]:
                    base_paths.append(os.path.join(component_path,
                                                   "debian-installer"))
            for base_path in base_paths:
                if "debian-installer" not in base_path:
                    safe_mkdir(os.path.join(base_path, "source"))
                for arch in archs:
                    safe_mkdir(os.path.join(base_path, "binary-"+arch))

