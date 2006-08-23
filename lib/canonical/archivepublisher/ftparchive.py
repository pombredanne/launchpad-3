# (C) Canonical Software Ltd. 2004-2006, all rights reserved.

import os
from StringIO import StringIO

from sqlobject import AND

from canonical.launchpad.database.publishing import (
    SourcePackagePublishingView, BinaryPackagePublishingView,
    SourcePackageFilePublishing, BinaryPackageFilePublishing)

from canonical.lp.dbschema import (
    PackagePublishingPriority, PackagePublishingStatus)

from canonical.launchpad.interfaces import pocketsuffix

def package_name(filename):
    """Extract a package name from a debian package filename."""
    return (os.path.basename(filename).split("_"))[0]


def f_touch(*parts):
    """Touch the file named by the arguments concatenated as a path."""
    fname = os.path.join(*parts)
    open(fname, "w").close()

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
    """Produces the Sources and Packages files based on many inputs."""


    def __init__(self, log, config, diskpool, distro, dirty_pockets):
        self.log = log
        self._config = config
        self._diskpool = diskpool
        self.distro = distro
        self.dirty_pockets = dirty_pockets
        self.release_files_needed = {}

        # We need somewhere to note down where the debian-installer
        # components came from. in _di_release_components we store
        # sets, keyed by distrorelease name of the component names
        # which contain debian-installer binaries.  This is filled out
        # when generating overrides and file lists, and then consumed
        # when generating apt-ftparchive configuration.
        self._di_release_components = {}

    def run(self, is_careful):
        self.createEmptyPocketRequests()
        self.log.debug("Preparing file lists and overrides.")
        self.generateOverrides()
        self.log.debug("Generating overrides for the distro.")
        self.generateFileLists()
        self.log.debug("Doing apt-ftparchive work.")

        apt_config = os.path.join(self._config.miscroot, "apt.conf")
        fp = file(apt_config, "w")
        fp.write(self.generateAptFTPConfig(is_careful))
        fp.close()

        self.log.debug("Filepath: %s" % apt_config)
        if os.system("apt-ftparchive --no-contents generate %s" % apt_config):
            raise OSError("Unable to run apt-ftparchive properly")

    def isDirty(self, distrorelease, pocket):
        # XXX: shamelessly ripped from Publisher, needs to be done properly
        if not (distrorelease.name, pocket) in self.dirty_pockets:
            return False
        return True

    def createEmptyPocketRequests(self):
        """Write out empty file lists etc for pockets we want to have
        Packages or Sources for but lack anything in them currently.
        """
        all_pockets = [suffix for _, suffix in pocketsuffix.items()]
        for distrorelease in self.distro:
            components = self._config.componentsForRelease(distrorelease.name)
            for suffix in all_pockets:
                for comp in components:
                    self.createEmptyPocketRequest(distrorelease, suffix, comp)

    def generateOverrides(self):
        spps = SourcePackagePublishingView.select(
            AND(SourcePackagePublishingView.q.distributionID == self.distro.id,
                SourcePackagePublishingView.q.publishingstatus ==
                    PackagePublishingStatus.PUBLISHED ))
        pps = BinaryPackagePublishingView.select(
            AND(BinaryPackagePublishingView.q.distributionID == self.distro.id,
                BinaryPackagePublishingView.q.publishingstatus ==
                    PackagePublishingStatus.PUBLISHED ))
        self.publishOverrides(spps, pps)

    def generateFileLists(self):
        spps = SourcePackageFilePublishing.select(
            AND(SourcePackageFilePublishing.q.distributionID == self.distro.id,
                SourcePackageFilePublishing.q.publishingstatus ==
                PackagePublishingStatus.PUBLISHED ))
        pps = BinaryPackageFilePublishing.select(
            AND(BinaryPackageFilePublishing.q.distributionID == self.distro.id,
                BinaryPackageFilePublishing.q.publishingstatus ==
                    PackagePublishingStatus.PUBLISHED ))

        self.publishFileLists(spps, pps)

    def publishOverrides(self, sourceoverrides, binaryoverrides, \
                         defaultcomponent = "main"):
        """Given the provided sourceoverrides and binaryoverrides, output
        a set of override files for use in apt-ftparchive.

        The files will be written to overrideroot with filenames of the form:
        override.<distrorelease>.<component>[.src]

        Attributes which must be present in sourceoverrides are:
        drname, spname, cname, sname

        Attributes which must be present in binaryoverrides are:
        drname, spname, cname, sname, priority

        The binary priority will be mapped via the values in dbschema.py
        """

        # overrides[distrorelease][component][src/bin] = list of lists
        overrides = {}

        prio = {}
        for p in PackagePublishingPriority._items:
            prio[p] = PackagePublishingPriority._items[p].title.lower()
            self.log.debug("Recording priority %d with name %s", p, prio[p])

        for so in sourceoverrides:
            distrorelease = so.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[so.pocket]
            component = so.componentname.encode('utf-8')
            section = so.sectionname.encode('utf-8')
            sourcepackagename = so.sourcepackagename.encode('utf-8')
            if component != defaultcomponent:
                section = "%s/%s" % (component, section)
            overrides.setdefault(distrorelease, {})
            this_override = overrides[distrorelease]
            this_override.setdefault(component, {})
            this_override[component].setdefault('src', [])
            this_override[component].setdefault('bin', [])
            this_override[component]['src'].append((sourcepackagename,
                                                    section))

        for bo in binaryoverrides:
            distrorelease = bo.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[bo.pocket]
            component = bo.componentname.encode('utf-8')
            section = bo.sectionname.encode('utf-8')
            binarypackagename = bo.binarypackagename.encode('utf-8')
            priority = bo.priority
            if priority not in prio:
                raise ValueError, "Unknown priority value %d" % priority
            priority = prio[priority]
            if component != defaultcomponent:
                section = "%s/%s" % (component, section)
            overrides.setdefault(distrorelease, {})
            this_override = overrides[distrorelease]
            this_override.setdefault(component, {})
            this_override[component].setdefault('src', [])
            this_override[component].setdefault('bin', [])
            this_override[component]['bin'].append((binarypackagename,
                                                    priority,
                                                    section))

        # Now generate the files on disk...
        for distrorelease in overrides:
            for component in overrides[distrorelease]:
                self.log.debug("Generating overrides for %s/%s..." % (
                    distrorelease, component))
                di_overrides = []
                # XXX: use os.path.join
                #   -- kiko, 2005-09-23
                f = open("%s/override.%s.%s" % (self._config.overrideroot,
                                                distrorelease, component), "w")
                ef = open("%s/override.%s.extra.%s" % (
                    self._config.overrideroot, distrorelease, component), "w")
                overrides[distrorelease][component]['bin'].sort()
                for tup in overrides[distrorelease][component]['bin']:
                    if tup[2].endswith("debian-installer"):
                        # Note in _di_release_components that this
                        # distrorelease has d-i contents in this component.
                        self._di_release_components.setdefault(distrorelease,
                                                set()).add(component)
                        # And record the tuple for later output in the d-i
                        # override file instead
                        di_overrides.append(tup)
                    else:
                        f.write("\t".join(tup))
                        f.write("\n")
                        # XXX: dsilvers: This needs to be made databaseish
                        # and be actually managed within Launchpad. (Or else
                        # we need to change the ubuntu as appropriate and look
                        # for bugs addresses etc in launchpad.
                        # bug 3900
                        ef.write("\t".join([tup[0], "Origin", "Ubuntu"]))
                        ef.write("\n")
                        ef.write("\t".join(
                            [tup[0], "Bugs",
                             "mailto:ubuntu-users@lists.ubuntu.com"]))
                        ef.write("\n")
                f.close()

                # XXX: dsilvers: As above, this needs to be integrated into
                # the database at some point.
                # bug 3900
                extra_extra_overrides = os.path.join(
                    self._config.miscroot,
                    "more-extra.override.%s.%s" % (distrorelease,
                                                   component))
                if not os.path.exists(extra_extra_overrides):
                    unpocketed_release = "-".join(
                        distrorelease.split('-')[:-1])
                    extra_extra_overrides = os.path.join(
                        self._config.miscroot,
                        "more-extra.override.%s.%s" % (unpocketed_release,
                                                       component))
                if os.path.exists(extra_extra_overrides):
                    eef = open(extra_extra_overrides, "r")
                    extras = {}
                    for line in eef:
                        line = line.strip()
                        if line:
                            (package, header, value) = line.split(None, 2)
                            pkg_extras = extras.setdefault(package, {})
                            header_values = pkg_extras.setdefault(header, [])
                            header_values.append(value)
                    eef.close()
                    for pkg, headers in extras.items():
                        for header, values in headers.items():
                            ef.write("\t".join(
                                [pkg, header, ", ".join(values)]))
                            ef.write("\n")
                ef.close()

                if len(di_overrides):
                    # We managed to find some d-i bits in these binaries,
                    # so we output a magical "component"-ish "section"-y sort
                    # of thing.
                    # Elmo informs me that the technical term for the d-i stuff
                    # is "horrible f***ing bodge"
                    # XXX: use os.path.join
                    #   -- kiko, 2005-09-23
                    f = open("%s/override.%s.%s.debian-installer" % (
                        self._config.overrideroot, distrorelease, component),
                             "w")
                    di_overrides.sort()
                    for tup in di_overrides:
                        f.write("\t".join(tup))
                        f.write("\n")
                    f.close()

                # XXX: use os.path.join
                #   -- kiko, 2005-09-23
                f = open("%s/override.%s.%s.src" % (self._config.overrideroot,
                                                    distrorelease,
                                                    component), "w")
                overrides[distrorelease][component]['src'].sort()
                for tup in overrides[distrorelease][component]['src']:
                    f.write("\t".join(tup))
                    f.write("\n")
                f.close()

    def publishFileLists(self, sourcefiles, binaryfiles):
        """Collate the set of source files and binary files provided and
        write out all the file list files for them.

        listroot/distrorelease_component_source
        listroot/distrorelease_component_binary-archname
        """
        filelist = {}
        self.log.debug("Collating lists of source files...")
        for f in sourcefiles:
            distrorelease = f.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[f.pocket]
            component = f.componentname.encode('utf-8')
            sourcepackagename = f.sourcepackagename.encode('utf-8')
            filename = f.libraryfilealiasfilename.encode('utf-8')
            ondiskname = self._diskpool.pathFor(component, sourcepackagename,
                                       filename)

            filelist.setdefault(distrorelease, {})
            filelist[distrorelease].setdefault(component, {})
            filelist[distrorelease][component].setdefault('source', [])
            filelist[distrorelease][component]['source'].append(ondiskname)

        self.log.debug("Collating lists of binary files...")
        for f in binaryfiles:
            distrorelease = f.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[f.pocket]
            component = f.componentname.encode('utf-8')
            sourcepackagename = f.sourcepackagename.encode('utf-8')
            filename = f.libraryfilealiasfilename.encode('utf-8')
            architecturetag = f.architecturetag.encode('utf-8')
            architecturetag = "binary-%s" % architecturetag

            ondiskname = self._diskpool.pathFor(component, sourcepackagename, filename)

            filelist.setdefault(distrorelease, {})
            this_file = filelist[distrorelease]
            this_file.setdefault(component, {})
            this_file[component].setdefault(architecturetag, [])
            this_file[component][architecturetag].append(ondiskname)

        # Now write them out...
        for distrorelease, components in filelist.items():
            self.log.debug("Writing file lists for %s" % distrorelease)
            for component, architectures in components.items():
                for architecture, file_names in architectures.items():
                    di_files = []
                    files = []
                    f = open(os.path.join(self._config.overrideroot,
                                          "%s_%s_%s" % (distrorelease,
                                                        component,
                                                        architecture)), "w")
                    for name in file_names:
                        if name.endswith(".udeb"):
                            # Once again, note that this componentonent in this
                            # distrorelease has d-i elements
                            self._di_release_components.setdefault(
                                distrorelease, set()).add(component)
                            # And note the name for output later
                            di_files.append(name)
                        else:
                            files.append(name)
                    files.sort(key=package_name)
                    f.write("\n".join(files))
                    f.write("\n")
                    f.close()
                    # Record this distrorelease/component/arch as needing a
                    # Release file.
                    self.release_files_needed.setdefault(
                        distrorelease, {}).setdefault(component,
                                                      set()).add(architecture)
                    if len(di_files):
                        # Once again, some d-i stuff to write out...
                        self.log.debug("Writing d-i file list for %s/%s/%s" % (
                            distrorelease, component, architecture))
                        # Erm, os.path.join would be much more of a pain
                        # here than the interpolation.
                        f = open("%s/%s_%s_debian-installer_%s" % (
                            self._config.overrideroot, distrorelease,
                            component, architecture), "w")
                        di_files.sort(key=package_name)
                        f.write("\n".join(di_files))
                        f.write("\n")
                        f.close()


    def generateAptFTPConfig(self, fullpublish=False):
        """Generate an APT FTPArchive configuration from the provided
        config object and the paths we either know or have given to us.

        If fullpublish is true, we generate config for everything.

        Otherwise, we aim to limit our config to certain distroreleases
        and pockets. By default, we will exclude release pockets for
        released distros, and in addition, if dirty_pockets is specified,
        we exclude any pocket not mentioned in it. dirty_pockets must be
        a nested dictionary of booleans, keyed by distrorelease.name then
        pocket.
        """
        cnf = StringIO()
        cnf.write(CONFIG_HEADER % (self._config.archiveroot,
                                   self._config.overrideroot,
                                   self._config.cacheroot,
                                   self._config.miscroot))

        # cnf now contains a basic header. Add a dists entry for each
        # of the distroreleases we've touched
        for dr in self._config.distroReleaseNames():
            db_dr = self.distro[dr]
            for pocket in pocketsuffix:

                if not fullpublish:
                    if not self.isDirty(db_dr, pocket):
                        self.log.debug("Skipping a-f stanza for %s/%s" %
                                           (dr, pocket))
                        continue
                    if not db_dr.isUnstable():
                        # See similar condition in D_writeReleaseFiles
                        assert pocketsuffix[pocket] != ''

                oarchs = self._config.archTagsForRelease(dr)
                ocomps = self._config.componentsForRelease(dr)
                # Firstly, pare comps down to the ones we've output
                comps = []
                for comp in ocomps:
                    comp_path = os.path.join(
                        self._config.overrideroot,
                        "_".join([dr + pocketsuffix[pocket],
                                  comp, "source"]))
                    if not os.path.exists(comp_path):
                        # Create an empty file if we don't have one so that
                        # apt-ftparchive will dtrt.
                        open(comp_path, "w").close()
                        # Also create an empty override file just in case.
                        open(os.path.join(
                            self._config.overrideroot,
                            ".".join(["override", dr + pocketsuffix[pocket],
                                      comp])), "w").close()
                        # Also create an empty source override file
                        open(os.path.join(
                            self._config.overrideroot,
                            ".".join(["override", dr + pocketsuffix[pocket],
                                      comp, "src"])), "w").close()
                    comps.append(comp)
                if len(comps) == 0:
                    self.log.debug("Did not find any components to create config "
                               "for %s%s" % (dr, pocketsuffix[pocket]))
                    continue
                # Second up, pare archs down as appropriate
                archs = []
                for arch in oarchs:
                    arch_path = os.path.join(
                        self._config.overrideroot,
                        "_".join([dr + pocketsuffix[pocket],
                                  comps[0],
                                  "binary-"+arch]))
                    if not os.path.exists(arch_path):
                        # Create an empty file if we don't have one so that
                        # apt-ftparchive will dtrt.
                        open(arch_path, "w").close()
                    archs.append(arch)
                self.log.debug("Generating apt config for %s%s" % (
                    dr, pocketsuffix[pocket]))
                # Replace those tokens
                cnf.write(STANZA_TEMPLATE % {
                    "LISTPATH": self._config.overrideroot,
                    "DISTRORELEASE": dr + pocketsuffix[pocket],
                    "DISTRORELEASEBYFILE": dr + pocketsuffix[pocket],
                    "DISTRORELEASEONDISK": dr + pocketsuffix[pocket],
                    "ARCHITECTURES": " ".join(archs + ["source"]),
                    "SECTIONS": " ".join(comps),
                    "EXTENSIONS": ".deb",
                    "CACHEINSERT": "",
                    "DISTS": os.path.basename(self._config.distsroot),
                    "HIDEEXTRA": ""
                    })
                dr_full_name = dr + pocketsuffix[pocket]
                if (dr_full_name in self._di_release_components and
                    len(archs) > 0):
                    for component in self._di_release_components[dr_full_name]:
                        cnf.write(STANZA_TEMPLATE % {
                            "LISTPATH": self._config.overrideroot,
                            "DISTRORELEASEONDISK": "%s%s/%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "DISTRORELEASEBYFILE": "%s%s_%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "DISTRORELEASE": "%s%s.%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "ARCHITECTURES": " ".join(archs),
                            "SECTIONS": "debian-installer",
                            "EXTENSIONS": ".udeb",
                            "CACHEINSERT": "debian-installer-",
                            "DISTS": os.path.basename(self._config.distsroot),
                            "HIDEEXTRA": "// "
                            })

                def safe_mkdir(path):
                    if not os.path.exists(path):
                        os.makedirs(path)


                for comp in comps:
                    component_path = os.path.join(self._config.distsroot,
                                                  dr + pocketsuffix[pocket],
                                                  comp)
                    base_paths = [component_path]
                    if dr_full_name in self._di_release_components:
                        if comp in self._di_release_components[dr_full_name]:
                            base_paths.append(os.path.join(component_path,
                                                           "debian-installer"))
                    for base_path in base_paths:
                        if "debian-installer" not in base_path:
                            safe_mkdir(os.path.join(base_path, "source"))
                        for arch in archs:
                            safe_mkdir(os.path.join(base_path, "binary-"+arch))
        # And now return that string.
        s = cnf.getvalue()
        cnf.close()

        return s

    def createEmptyPocketRequest(self, distrorelease, suffix, comp):
        """XXX"""
        full_distrorelease_name = distrorelease.name + suffix
        arch_tags = self._config.archTagsForRelease(distrorelease.name)

        if suffix == "":
            # organize distrorelease and component pair as
            # debian-installer -> distrorelease_component
            # internal map. Only the main pocket actually
            # needs these, though.
            self._di_release_components.setdefault(
                distrorelease.name, set()).add(comp)
            f_touch(self._config.overrideroot,
                    ".".join(["override", distrorelease.name, comp,
                              "debian-installer"]))

        # Touch the source file lists and override files
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distrorelease_name, comp]))
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distrorelease_name, "extra", comp]))
        f_touch(self._config.overrideroot,
                ".".join(["override", full_distrorelease_name, comp, "src"]))

        dr_comps = self.release_files_needed.setdefault(
            full_distrorelease_name, {})

        f_touch(self._config.overrideroot,
                "_".join([full_distrorelease_name, comp, "source"]))
        dr_comps.setdefault(comp, set()).add("source")

        for arch in arch_tags:
            # organize dr/comp/arch into temporary binary
            # archive map for the architecture in question.
            dr_special = self.release_files_needed.setdefault(
                full_distrorelease_name, {})
            dr_special.setdefault(comp, set()).add("binary-"+arch)

            # Touch more file lists for the archs.
            f_touch(self._config.overrideroot,
                    "_".join([full_distrorelease_name, comp, "binary-"+arch]))
            f_touch(self._config.overrideroot,
                    "_".join([full_distrorelease_name, comp, "debian-installer",
                              "binary-"+arch]))

