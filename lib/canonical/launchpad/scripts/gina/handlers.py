# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina db handlers.

Classes to handle and create entries on launchpad db.
"""
__all__ = [
    'ImporterHandler',
    'BinaryPackageHandler',
    'BinaryPackagePublisher',
    'SourcePackageHandler',
    'SourcePackagePublisher',
    'DistroHandler',
    'PersonHandler',
    ]

import os
import re
import tempfile
import shutil

from sqlobject import SQLObjectNotFound, SQLObjectMoreThanOneResultError

from zope.component import getUtility

from canonical.database.sqlbase import quote
from canonical.database.constants import nowUTC

from canonical.archivepublisher import Poolifier, parse_tagfile

from canonical.lp.dbschema import (PackagePublishingStatus, BuildStatus,
    SourcePackageFormat)

from canonical.launchpad.scripts import log
from canonical.launchpad.scripts.gina.library import (getLibraryAlias,
                                                      checkLibraryForFile)
from canonical.launchpad.scripts.gina.packages import (SourcePackageData,
    urgencymap, prioritymap, get_dsc_path, licence_cache, read_dsc,
    PoolFileNotFound)

from canonical.launchpad.database import (Distribution, DistroRelease,
    DistroArchRelease,Processor, SourcePackageName, SourcePackageRelease,
    Build, BinaryPackageRelease, BinaryPackageName,
    SecureBinaryPackagePublishingHistory,
    Component, Section, SourcePackageReleaseFile,
    SecureSourcePackagePublishingHistory, BinaryPackageFile)

from canonical.launchpad.interfaces import IPersonSet, IBinaryPackageNameSet
from canonical.launchpad.helpers import getFileType, getBinaryPackageFormat

# Stash a reference to the poolifier method
poolify = Poolifier().poolify


def check_not_in_librarian(files, archive_root, directory):
    to_upload = []
    if not isinstance(files, list):
        # A little bit of ugliness. The source package's files attribute
        # returns a three-tuple with md5sum, size and name. The binary
        # package, on the other hand, only really provides a filename.
        # This is tested through the two codepaths, so it should be safe.
        files = [(None, files)]
    for i in files:
        fname = i[-1]
        path = os.path.join(archive_root, directory)
        if not os.path.exists(os.path.join(path, fname)):
            # XXX: untested
            raise PoolFileNotFound('Package %s not found in archive '
                                   '%s' % (fname, path))
        # XXX: <stub> Until I or someone else completes
        # LibrarianGarbageCollection (the first half of which is
        # awaiting review)
        #if checkLibraryForFile(path, fname):
        #    # XXX: untested
        #    raise LibrarianHasFileError('File %s already exists in the '
        #                                'librarian' % fname)
        to_upload.append((fname, path))
    return to_upload


class DataSetupError(Exception):
    """Raised when required data is found to be missing in the database"""


class MultiplePackageReleaseError(Exception):
    """
    Raised when multiple package releases of the same version are
    found for a single distribution, indicating database corruption.
    """


class LibrarianHasFileError(MultiplePackageReleaseError):
    """
    Raised when the librarian already contains a file we are trying
    to import. This indicates database corruption.
    """


class MultiplePublishingEntryError(MultiplePackageReleaseError):
    """
    Raised when there are more than one publishing entries for this
    package.
    """


class MultipleBuildError(MultiplePackageReleaseError):
    """Raised when we have multiple builds for the same package"""


class NoSourcePackageError(Exception):
    """Raised when a Binary Package has no matching Source Package"""


class ImporterHandler:
    """Import Handler class

    This class is used to handle the import process.
    """
    def __init__(self, ztm, distro_name, distrorelease_name, dry_run,
                 ktdb, archive_root, keyrings, pocket):
        self.dry_run = dry_run
        self.pocket = pocket
        self.ztm = ztm

        self.distro = self._get_distro(distro_name)
        self.distrorelease = self._get_distrorelease(distrorelease_name)

        self.archinfo = {}
        self.imported_sources = []
        self.imported_bins = {}

        self.sphandler = SourcePackageHandler(ktdb, archive_root, keyrings, 
                                              pocket)
        self.bphandler = BinaryPackageHandler(self.sphandler, archive_root)

        self.sppublisher = SourcePackagePublisher(self.distrorelease, pocket)
        # This is initialized in ensure_archinfo
        self.bppublishers = {}

    def commit(self):
        """Commit to the database."""
        if not self.dry_run:
            self.ztm.commit()

    def abort(self):
        """Rollback changes to the database."""
        if not self.dry_run:
            self.ztm.abort()

    def ensure_archinfo(self, archtag):
        """Append retrived distroarchrelease info to a dict."""
        if archtag in self.archinfo.keys():
            return

        """Get distroarchrelease and processor from the architecturetag"""
        dar = DistroArchRelease.selectOneBy(
                distroreleaseID=self.distrorelease.id,
                architecturetag=archtag)
        if not dar:
            raise DataSetupError("Error finding distroarchrelease for %s/%s"
                                 % (self.distrorelease.name, archtag))

        # XXX: is this really a selectOneBy? Can't there be multiple
        # proessors per family?
        processor = Processor.selectOneBy(familyID=dar.processorfamily.id)
        if not processor:
            raise DataSetupError("Unable to find a processor from the "
                                 "processor family %s chosen from %s/%s"
                                 % (dar.processorfamily.name,
                                    self.distrorelease.name, archtag))

        info = {'distroarchrelease': dar, 'processor': processor}
        self.archinfo[archtag] = info

        self.bppublishers[archtag] = BinaryPackagePublisher(dar, self.pocket)
        self.imported_bins[archtag] = []

    #
    # Distro Stuff: Should go to DistroHandler
    #

    def _get_distro(self, name):
        """Return the distro database object by name."""
        distro = Distribution.selectOneBy(name=name)
        if not distro:
            raise DataSetupError("Error finding distribution %r" % name)
        return distro

    def _get_distrorelease(self, name):
        """Return the distrorelease database object by name."""
        dr = DistroRelease.selectOneBy(name=name,
                                       distributionID=self.distro.id)
        if not dr:
            raise DataSetupError("Error finding distrorelease %r" % name)
        return dr

    #
    # Package stuff
    #

    def ensure_sourcepackagename(self, name):
        """Import only the sourcepackagename ensuring them."""
        self.sphandler.ensureSourcePackageName(name)

    def preimport_sourcecheck(self, sourcepackagedata):
        """
        Check if this SourcePackageRelease already exists. This can
        happen, for instance, if a source package didn't change over
        releases, or if Gina runs multiple times over the same release
        """
        sourcepackagerelease = self.sphandler.checkSource(
                                   sourcepackagedata.package,
                                   sourcepackagedata.version,
                                   self.distrorelease)
        if not sourcepackagerelease:
            log.debug('SPR not found in preimport: %r %r' %
                (sourcepackagedata.package, sourcepackagedata.version))
            return None

        self.publish_sourcepackage(sourcepackagerelease, sourcepackagedata)
        return sourcepackagerelease

    def import_sourcepackage(self, sourcepackagedata):
        """Handler the sourcepackage import process"""
        assert not self.sphandler.checkSource(sourcepackagedata.package,
                                              sourcepackagedata.version,
                                              self.distrorelease)
        handler = self.sphandler.createSourcePackageRelease
        sourcepackagerelease = handler(sourcepackagedata,
                                       self.distrorelease)

        self.publish_sourcepackage(sourcepackagerelease, sourcepackagedata)
        return sourcepackagerelease

    def preimport_binarycheck(self, archtag, binarypackagedata):
        """
        Check if this BinaryPackageRelease already exists. This can
        happen, for instance, if a binary package didn't change over
        releases, or if Gina runs multiple times over the same release
        """
        distroarchinfo = self.archinfo[archtag]
        binarypackagerelease = self.bphandler.checkBin(binarypackagedata,
                                                       distroarchinfo)
        if not binarypackagerelease:
            log.debug('BPR not found in preimport: %r %r %r' %
                (binarypackagedata.package, binarypackagedata.version,
                 binarypackagedata.architecture))
            return None

        self.publish_binarypackage(binarypackagerelease, binarypackagedata,
                                   archtag)
        return binarypackagerelease

    def import_binarypackage(self, archtag, binarypackagedata):
        """Handler the binarypackage import process"""
        distroarchinfo = self.archinfo[archtag]

        # We know that preimport_binarycheck has run
        assert not self.bphandler.checkBin(binarypackagedata, distroarchinfo)

        # Find the sourcepackagerelease that generated this binarypackage.
        distrorelease = distroarchinfo['distroarchrelease'].distrorelease
        sourcepackage = self.locate_sourcepackage(binarypackagedata,
                                                  distrorelease)
        if not sourcepackage:
            # XXX: untested
            # If the sourcepackagerelease is not imported, not way to import
            # this binarypackage. Warn and giveup.
            raise NoSourcePackageError("No source package %s (%s) found "
                "for %s (%s)" % (binarypackagedata.package,
                                 binarypackagedata.version,
                                 binarypackagedata.source,
                                 binarypackagedata.source_version))

        binarypackagerelease = self.bphandler.createBinaryPackage(
            binarypackagedata, sourcepackage, distroarchinfo, archtag)
        self.publish_binarypackage(binarypackagerelease, binarypackagedata,
                                   archtag)

    binnmu_re = re.compile(r"^(.+)\.\d+$")
    binnmu_re2 = re.compile(r"^(.+)\.\d+\.\d+$")

    def locate_sourcepackage(self, binarypackagedata, distrorelease):
        # This function uses a list of versions to deal with the fact
        # that we may need to munge the version number as we search for
        # bin-only-NMUs. The fast path is dealt with the first cycle of
        # the loop; we only cycle more than once if the source package
        # is really missing.
        versions = [binarypackagedata.source_version]

        is_binnmu = self.binnmu_re2.match(binarypackagedata.source_version)
        if is_binnmu:
            # DEB is jikes-sablevm_1.1.5-1.0.1_all.deb
            #   bin version is 1.1.5-1.0.1
            # DSC is sablevm_1.1.5-1.dsc
            #   src version is 1.1.5-1
            versions.append(is_binnmu.group(1))

        is_binnmu = self.binnmu_re.match(binarypackagedata.source_version)
        if is_binnmu:
            # DEB is jikes-sablevm_1.1.5-1.1_all.deb
            #   bin version is 1.1.5-1.1
            # DSC is sablevm_1.1.5-1.dsc
            #   src version is 1.1.5-1
            versions.append(is_binnmu.group(1))

        for version in versions:
            sourcepackage = self.sphandler.checkSource(
                binarypackagedata.source, version, distrorelease)
            if sourcepackage:
                return sourcepackage

            # We couldn't find a sourcepackagerelease in the database.
            # Perhaps we can opportunistically pick one out of the archive.
            log.warn("No source package %s (%s) listed for %s (%s), "
                     "scrubbing archive..." %
                     (binarypackagedata.source,
                      version, binarypackagedata.package,
                      binarypackagedata.version))

            # XXX: I question whether binarypackagedata.section here is
            # actually correct -- but where can we obtain this
            # information from introspecting the archive?
            sourcepackage = self.sphandler.findUnlistedSourcePackage(
                binarypackagedata.source, version,
                binarypackagedata.component, binarypackagedata.section,
                distrorelease)
            if sourcepackage:
                return sourcepackage

            log.warn("Nope, couldn't find it. Could it be a "
                     "bin-only-NMU? Checking...")

            # XXX: testing a third cycle of this loop isn't done

        return None

    def publish_sourcepackage(self, sourcepackagerelease, sourcepackagedata):
        """Append to the sourcepackagerelease imported list."""
        self.sppublisher.publish(sourcepackagerelease, sourcepackagedata)
        self.imported_sources.append((sourcepackagerelease, sourcepackagedata))

    def publish_binarypackage(self, binarypackagerelease, binarypackagedata,
                              archtag):
        self.bppublishers[archtag].publish(binarypackagerelease,
                                           binarypackagedata)
        self.imported_bins[archtag].append((binarypackagerelease,
                                            binarypackagedata))


class DistroHandler:
    """Handles distro related information."""

    def __init__(self):
        # Components and sections are cached to avoid redoing the same
        # database queries over and over again.
        self.compcache = {} 
        self.sectcache = {}

    def getComponentByName(self, component):
        """Returns a component object by its name."""
        if component in self.compcache:
            return self.compcache[component]

        ret = Component.selectOneBy(name=component)

        if not ret:
            raise ValueError("Component %s not found" % component)

        self.compcache[component] = ret
        return ret

    def ensureSection(self, section):
        """Returns a section object by its name. Create and return if it
        doesn't exist.
        """
        if section in self.sectcache:
            return self.sectcache[section]

        ret = Section.selectOneBy(name=section)
        if not ret:
            ret = Section(name=section)

        self.sectcache[section] = ret
        return ret


class SourcePackageHandler:
    """SourcePackageRelease Handler class

    This class has methods to make the sourcepackagerelease access
    on the launchpad db a little easier.
    """
    def __init__(self, KTDB, archive_root, keyrings, pocket):
        self.person_handler = PersonHandler()
        self.distro_handler = DistroHandler()
        self.ktdb = KTDB
        self.archive_root = archive_root
        self.keyrings = keyrings
        self.pocket = pocket

    def ensureSourcePackageName(self, name):
        return SourcePackageName.ensure(name)

    def findUnlistedSourcePackage(self, sp_name, sp_version,
                                  sp_component, sp_section, distrorelease):
        """Try to find a sourcepackagerelease in the archive for the
        provided binarypackage data.

        The binarypackage data refers to a source package which we
        cannot find either in the database or in the input data.

        This commonly happens when the source package is no longer part
        of the distribution but a binary built from it is and thus the
        source is not in Sources.gz but is on the disk. This may also
        happen if the package has not built yet.

        If we fail to find it we return None and the binary importer
        will handle this in the same way as if the package simply wasn't
        in the database. I.E. the binary import will fail but the
        process as a whole will continue okay.
        """
        assert not self.checkSource(sp_name, sp_version, distrorelease)

        log.debug("Looking for source package %r (%r) in %r" %
                  (sp_name, sp_version, sp_component))

        sp_data = self._getSourcePackageDataFromDSC(sp_name,
            sp_version, sp_component, sp_section)
        if not sp_data:
            return None

        # Process the package
        sp_data.process_package(self.ktdb, self.archive_root, self.keyrings)
        sp_data.ensure_complete(self.ktdb)

        spr = self.createSourcePackageRelease(sp_data, distrorelease)

        # Publish it because otherwise we'll have problems later.
        # Essentially this routine is only ever called when a binary
        # is encountered for which the source was not found.
        # Now that we have found and imported the source, we need
        # to be sure to publish it because the binary import code
        # assumes that the sources have been imported properly before
        # the binary import is started. Thusly since this source is
        # being imported "late" in the process, we publish it immediately
        # to make sure it doesn't get lost.
        SourcePackagePublisher(distrorelease, self.pocket).publish(spr, sp_data)
        return spr

    def _getSourcePackageDataFromDSC(self, sp_name, sp_version,
                                     sp_component, sp_section):
        try:
            dsc_name, dsc_path, sp_component = get_dsc_path(sp_name,
                sp_version, sp_component, self.archive_root)
        except PoolFileNotFound:
            # Aah well, no source package in archive either.
            return None

        log.debug("Found a source package for %s (%s) in %s" % (sp_name,
            sp_version, sp_component))
        dsc_contents = parse_tagfile(dsc_path, allow_unsigned=True)

        # Since the dsc doesn't know, we add in the directory, package
        # component and section
        dsc_contents['directory'] = os.path.join("pool",
            poolify(sp_name, sp_component))
        dsc_contents['package'] = sp_name
        dsc_contents['component'] = sp_component
        dsc_contents['section'] = sp_section

        # the dsc doesn't list itself so add it ourselves
        if 'files' not in dsc_contents:
            log.error('DSC for %s didn\'t contain a files entry: %r' % 
                      (dsc_name, dsc_contents))
            return None
        if not dsc_contents['files'].endswith("\n"):
            dsc_contents['files'] += "\n"
        # XXX: Why do we hack the md5sum and size of the DSC? Should
        # probably calculate it properly.
        dsc_contents['files'] += "xxx 000 %s" % dsc_name

        # SourcePackageData requires capitals
        capitalized_dsc = {}
        for k, v in dsc_contents.items():
            capitalized_dsc[k.capitalize()] = v

        return SourcePackageData(**capitalized_dsc)

    def checkSource(self, source, version, distrorelease):
        """Check if a sourcepackagerelease is already on lp db.

        Returns the sourcepackagerelease if exists or none if not.
        """
        try:
            spname = SourcePackageName.byName(source)
        except SQLObjectNotFound:
            return None

        # Check if this sourcepackagerelease already exists using name and
        # version
        return self._getSource(spname, version, distrorelease)

    def _getSource(self, sourcepackagename, version, distrorelease):
        """Returns a sourcepackagerelease by its name and version."""
        # XXX: we use the source package publishing tables here, but I
        # think that's a bit flawed. We should have a way of saying "my
        # distrorelease overlays the version namespace of that
        # distrorelease" and use that to decide on whether we've seen
        # this package before or not. The publishing tables are wrong,
        # for instance, in the context of proper derivation.
        query = """
                sourcepackagerelease.sourcepackagename = %s AND
                sourcepackagerelease.version = %s AND
                sourcepackagepublishing.sourcepackagerelease = 
                    sourcepackagerelease.id AND
                sourcepackagepublishing.distrorelease = distrorelease.id AND
                distrorelease.distribution = %s
                """ % (sourcepackagename.id, quote(version), 
                       distrorelease.distribution.id)
        # XXX: this should really be a select DISTINCT. What we want to
        # know here is the set of source packages with this version that
        # was ever published into this archive.
        releases = set()
        for spr in SourcePackageRelease.select(query,
            clauseTables=['SourcePackagePublishing', 'DistroRelease']):
            releases.add(spr.id)
        if not releases:
            return None
        if len(releases) != 1:
            # XXX: untested
            raise MultiplePackageReleaseError("Found more than one "
                    "entry for %s (%s) published into %s" %
                    (sourcepackagename.name, version,
                     distrorelease.distribution.name))
        return spr

    def createSourcePackageRelease(self, src, distrorelease):
        """Create a SourcePackagerelease and db dependencies if needed.

        Returns the created SourcePackageRelease, or None if it failed.
        """

        displayname, emailaddress = src.maintainer
        maintainer = self.person_handler.ensurePerson(displayname,
                                                      emailaddress)

        # XXX: Check it later -- Debonzi 20050516
        #         if src.dsc_signing_key_owner:
        #             key = self.getGPGKey(src.dsc_signing_key, 
        #                                  *src.dsc_signing_key_owner)
        #         else:
        key = None

        to_upload = check_not_in_librarian(src.files, src.archive_root,
                                           src.directory)

        #
        # DO IT! At this point, we've decided we have everything we need
        # to create the SPR.
        #

        componentID = self.distro_handler.getComponentByName(src.component).id
        sectionID = self.distro_handler.ensureSection(src.section).id
        name = self.ensureSourcePackageName(src.package)
        spr = SourcePackageRelease(
                                   section=sectionID,
                                   creator=maintainer.id,
                                   component=componentID,
                                   sourcepackagename=name.id,
                                   maintainer=maintainer.id,
                                   dscsigningkey=key,
                                   manifest=None,
                                   urgency=urgencymap[src.urgency],
                                   dateuploaded=src.date_uploaded,
                                   dsc=src.dsc,
                                   version=src.version,
                                   changelog=src.changelog,
                                   builddepends=src.build_depends,
                                   builddependsindep=src.build_depends_indep,
                                   architecturehintlist=src.architecture,
                                   format=SourcePackageFormat.DPKG,
                                   uploaddistrorelease=distrorelease.id)
        log.info('Source Package Release %s (%s) created' % 
                 (name.name, src.version))

        # Insert file into the library and create the
        # SourcePackageReleaseFile entry on lp db.
        for fname, path in to_upload:
            alias = getLibraryAlias(path, fname)
            SourcePackageReleaseFile(sourcepackagerelease=spr.id,
                                     libraryfile=alias,
                                     filetype=getFileType(fname))
            log.info('Package file %s included into library' % fname)

        return spr


class SourcePackagePublisher:
    """Class to handle the sourcepackagerelease publishing process."""

    def __init__(self, distrorelease, pocket):
        # Get the distrorelease where the sprelease will be published.
        self.distrorelease = distrorelease
        self.pocket = pocket
        self.distro_handler = DistroHandler()

    def publish(self, sourcepackagerelease, spdata):
        """Create the publishing entry on db if does not exist."""
        # Check if the sprelease is already published and if so, just
        # report it.
        source_publishinghistory = self._checkPublishing(
            sourcepackagerelease, self.distrorelease)
        if source_publishinghistory:
            log.info('SourcePackageRelease already published as %s' %
                      source_publishinghistory.status.title)
            return

        component = self.distro_handler.getComponentByName(spdata.component)
        section = self.distro_handler.ensureSection(spdata.section)

        # Create the Publishing entry with status PENDING so that we can
        # republish this later into a Soyuz archive.
        entry = SecureSourcePackagePublishingHistory(
            distrorelease=self.distrorelease.id,
            sourcepackagerelease=sourcepackagerelease.id,
            status=PackagePublishingStatus.PENDING,
            component=component.id,
            section=section.id,
            datecreated=nowUTC,
            datepublished=nowUTC,
            pocket=self.pocket
            )
        log.info('Source package %s (%s) published' % (
            entry.sourcepackagerelease.sourcepackagename.name,
            entry.sourcepackagerelease.version))

    def _checkPublishing(self, sourcepackagerelease, distrorelease):
        """Query for the publishing entry"""
        try:
            return SecureSourcePackagePublishingHistory.selectOneBy(
                sourcepackagereleaseID=sourcepackagerelease.id,
                distroreleaseID=distrorelease.id)
        except SQLObjectMoreThanOneResultError:
            # XXX: untested
            name = sourcepackagerelease.sourcepackagename.name
            raise MultiplePublishingEntryError("Source package %s (%s) has "
                "more than one publishing record for %s" %
                (name, sourcepackagerelease.version, distrorelease.name))


class BinaryPackageHandler:
    """Handler to deal with binarypackages."""
    def __init__(self, sphandler, archive_root):
        # Create other needed object handlers.
        self.person_handler = PersonHandler()
        self.distro_handler = DistroHandler()
        self.source_handler = sphandler
        self.archive_root = archive_root

    def checkBin(self, binarypackagedata, distroarchinfo):
        """Returns a binarypackage -- if it exists."""
        try:
            binaryname = BinaryPackageName.byName(binarypackagedata.package)
        except SQLObjectNotFound:
            # If the binary package's name doesn't exist, don't even
            # bother looking for a binary package.
            return None

        version = binarypackagedata.version
        architecture = binarypackagedata.architecture

        clauseTables = ["BinaryPackageRelease", "DistroRelease", "Build",
                        "DistroArchRelease"]
        distrorelease = distroarchinfo['distroarchrelease'].distrorelease

        # When looking for binaries, we need to remember that they are
        # shared between distribution releases, so match on the
        # distribution and the architecture tag of the distroarchrelease
        # they were built for
        query = ("BinaryPackageRelease.binarypackagename=%s AND "
                 "BinaryPackageRelease.version=%s AND "
                 "BinaryPackageRelease.build = Build.id AND "
                 "Build.distroarchrelease = DistroArchRelease.id AND "
                 "DistroArchRelease.distrorelease = DistroRelease.id AND "
                 "DistroRelease.distribution = %d" %
                 (binaryname.id, quote(version),
                  distrorelease.distribution.id))

        if architecture != "all":
            query += ("AND DistroArchRelease.architecturetag = %s" %
                      quote(architecture))

        try:
            bpr = BinaryPackageRelease.selectOne(query,
                                                 clauseTables=clauseTables)
        except SQLObjectMoreThanOneResultError:
            # XXX: untested
            raise MultiplePackageReleaseError("Found more than one "
                    "entry for %s (%s) for %s in %s" %
                    (binaryname.name, version, architecture,
                     distrorelease.distribution.name))
        return bpr

    def readLicence(self, bin_name, src_name, version, component):
        licence = self.readLicenceCached(bin_name, src_name, version)
        if licence:
            return licence

        # XXX: untested
        # Couldn't find the licence in the cache; let's trigger a
        # read_dsc to see if we can find it.
        try:
            tempdir = tempfile.mkdtemp()
            cwd = os.getcwd()
            os.chdir(tempdir)
            try:
                # Read the DSC and ensure the licence_cache is set
                read_dsc(src_name, version, component, self.archive_root)
            finally:
                os.chdir(cwd)
            shutil.rmtree(tempdir)
        except PoolFileNotFound:
            log.warn("While groping for a copyright file for %s, could "
                     "not even find the source package for %s (%s) in "
                     "the archive. Dropped copyright." %
                     (bin_name, src_name, version))
            licence = None
        else:
            licence = self.readLicenceCached(bin_name, src_name, version)

        return licence

    def readLicenceCached(self, bin_name, src_name, version):
        licence = licence_cache.get((src_name, version, bin_name), None)
        if licence is None:
            # No binarypackage-specific licence, so let's get the
            # main one (if it's there)
            licence = licence_cache.get((src_name, version, None), None)
        return licence

    def createBinaryPackage(self, bin, srcpkg, distroarchinfo, archtag):
        """Create a new binarypackage."""
        fdir, fname = os.path.split(bin.filename)
        to_upload = check_not_in_librarian(fname, bin.archive_root, fdir)
        fname, path = to_upload[0]

        componentID = self.distro_handler.getComponentByName(bin.component).id
        sectionID = self.distro_handler.ensureSection(bin.section).id
        architecturespecific = (bin.architecture == "all")

        bin_name = getUtility(IBinaryPackageNameSet).ensure(bin.package)
        build = self.ensureBuild(bin, srcpkg, distroarchinfo, archtag)

        licence = self.readLicence(bin.package,
                                   srcpkg.sourcepackagename.name,
                                   srcpkg.version, srcpkg.component.name)

        # Create the binarypackage entry on lp db.
        binpkg = BinaryPackageRelease(
            binarypackagename = bin_name.id,
            component = componentID,
            version = bin.version,
            description = bin.description,
            summary = bin.summary,
            build = build.id,
            binpackageformat = getBinaryPackageFormat(bin.filename),
            section = sectionID,
            priority = prioritymap[bin.priority],
            shlibdeps = bin.shlibs,
            depends = bin.depends,
            suggests = bin.suggests,
            recommends = bin.recommends,
            conflicts = bin.conflicts,
            replaces = bin.replaces,
            provides = bin.provides,
            essential = bin.essential,
            installedsize = bin.installed_size,
            licence = licence,
            architecturespecific = architecturespecific,
            copyright = None,
            )
        log.info('Binary Package Release %s (%s) created' %
                 (bin_name.name, bin.version))

        alias = getLibraryAlias(path, fname)
        BinaryPackageFile(binarypackagerelease=binpkg.id,
                          libraryfile=alias,
                          filetype=getFileType(fname))
        log.info('Package file %s included into library' % fname)

        # Return the binarypackage object.
        return binpkg

    def ensureBuild(self, binary, srcpkg, distroarchinfo, archtag):
        """Ensure a build record."""
        distroarchrelease = distroarchinfo['distroarchrelease']
        distribution = distroarchrelease.distrorelease.distribution
        clauseTables = ["Build", "DistroArchRelease", "DistroRelease"]

        query = ("Build.sourcepackagerelease = %d AND "
                 "Build.distroarchrelease = DistroArchRelease.id AND " 
                 "DistroArchRelease.distrorelease = DistroRelease.id AND "
                 "DistroRelease.distribution = %d"
                 % (srcpkg.id, distribution.id))

        if archtag != "all":
            query += ("AND DistroArchRelease.architecturetag = %s" 
                      % quote(archtag))

        try:
            build = Build.selectOne(query, clauseTables)
        except SQLObjectMoreThanOneResultError:
            # XXX: untested
            raise MultipleBuildError("More than one build was found "
                "for package %s (%s)" % (binary.package, binary.version))

        if build:
            for bpr in build.binarypackages:
                if bpr.binarypackagename.name == binary.package:
                    # XXX: untested
                    raise MultipleBuildError("Build %d was already found "
                        "for package %s (%s)" %
                        (build.id, binary.package, binary.version))
        else:

            # XXX: Check it later -- Debonzi 20050516
            #         if bin.gpg_signing_key_owner:
            #             key = self.getGPGKey(bin.gpg_signing_key, 
            #                                  *bin.gpg_signing_key_owner)
            #         else:
            key = None

            processor = distroarchinfo['processor']
            build = Build(processor=processor.id,
                          distroarchrelease=distroarchrelease.id,
                          buildstate=BuildStatus.FULLYBUILT,
                          gpgsigningkey=key,
                          sourcepackagerelease=srcpkg.id,
                          buildduration=None,
                          buildlog=None,
                          builder=None,
                          changes=None,
                          datebuilt=None)
        return build


class BinaryPackagePublisher:
    """Binarypackage publisher class."""
    def __init__(self, distroarchrelease, pocket):
        self.distroarchrelease = distroarchrelease
        self.pocket = pocket
        self.distro_handler = DistroHandler()

    def publish(self, binarypackage, bpdata):
        """Create the publishing entry on db if does not exist."""
        # Check if the binarypackage is already published and if yes,
        # just report it.
        binpkg_publishinghistory = self._checkPublishing(
            binarypackage, self.distroarchrelease)
        if binpkg_publishinghistory:
            log.info('Binarypackage already published as %s' % (
                binpkg_publishinghistory.status.title))
            return

        # These need to be pulled from the binary package data, not the
        # binary package release: the data represents data from /this
        # specific distrorelease/, whereas the package represents data
        # from when it was first built.
        component = self.distro_handler.getComponentByName(bpdata.component)
        section = self.distro_handler.ensureSection(bpdata.section)
        priority = prioritymap[bpdata.priority]

        # Create the Publishing entry with status PENDING.
        SecureBinaryPackagePublishingHistory(
            binarypackagerelease = binarypackage.id,
            component = component.id,
            section = section.id,
            priority = priority,
            distroarchrelease = self.distroarchrelease.id,
            status = PackagePublishingStatus.PENDING,
            datecreated = nowUTC,
            datepublished = nowUTC,
            pocket = self.pocket,
            datesuperseded = None,
            supersededby = None,
            datemadepending = None,
            dateremoved = None,
            )

        log.info('BinaryPackage %s-%s published into %s.' % (
            binarypackage.binarypackagename.name, binarypackage.version,
            self.distroarchrelease.architecturetag))


    def _checkPublishing(self, binarypackage, distroarchrelease):
        """Query for the publishing entry"""
        try:
            return SecureBinaryPackagePublishingHistory.selectOneBy(
                binarypackagereleaseID=binarypackage.id,
                distroarchreleaseID=distroarchrelease.id)
        except SQLObjectMoreThanOneResultError:
            # XXX: untested
            name = binarypackage.binarypackagename.name
            raise MultiplePublishingEntryError("Binary package %s (%s) has "
                "more than one publishing record for %s" %
                (name, binarypackage.version,
                 distroarchrelease.distrorelease.name))


class PersonHandler:
    """Class to handle person."""

    def ensurePerson(self, displayname, emailaddress):
        """Return a person by its email.

        Create and Return if does not exist.
        """
        person = self.checkPerson(emailaddress)
        if person is None:
            return self.createPerson(emailaddress, displayname)
        return person

    def checkPerson(self, emailaddress):
        """Check if a person already exists using its email."""
        return getUtility(IPersonSet).getByEmail(emailaddress, default=None)

    def createPerson(self, emailaddress, displayname):
        """Create a new Person"""
        givenname = displayname.split()[0]
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email=emailaddress, displayname=displayname, givenname=givenname)
        return person

