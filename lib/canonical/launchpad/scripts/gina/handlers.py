# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina db handlers.

Classes to handle and create entries on launchpad db.
"""
__all__ = [
    'ImporterHandler',
    'BinaryPackageHandler',
    'BinaryPackagePublisher',
    'SourcePackageReleaseHandler',
    'SourcePublisher',
    'DistroHandler',
    'PersonHandler',
    ]

import os

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
    urgencymap, prioritymap, get_dsc_path, PoolFileNotFound)

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

        self.ztm = ztm

        self.distro = self._get_distro(distro_name)
        self.distrorelease = self._get_distrorelease(distrorelease_name)

        self.archinfo = {}
        self.imported_sources = []
        self.imported_bins = {}

        self.sphandler = SourcePackageReleaseHandler(ktdb, archive_root,
                                                     keyrings, pocket)
        self.bphandler = BinaryPackageHandler(self.sphandler, archive_root)

    def commit(self):
        """Commit to the database."""
        if not self.dry_run:
            self.ztm.commit()

    def abort(self):
        """Rollback changes to the database."""
        if not self.dry_run:
            self.ztm.abort()

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

    def _get_distroarchrelease_info(self, archtag):
        """Get distroarchrelease and processor from the architecturetag"""
        dar = DistroArchRelease.selectOneBy(
                distroreleaseID=self.distrorelease.id,
                architecturetag=archtag)
        if not dar:
            raise DataSetupError("Error finding distroarchrelease for %s/%s"
                                 % (self.distrorelease.name, archtag))

        processor = Processor.selectOneBy(familyID=dar.processorfamily.id)
        if not processor:
            raise DataSetupError("Unable to find a processor from the "
                                 "processor family chosen from %s/%s"
                                 % (self.distrorelease.name, archtag))

        return {'distroarchrelease': dar, 'processor': processor}

    def _store_sprelease_for_publishing(self, sourcepackagerelease):
        """Append to the sourcepackagerelease imported list."""
        if sourcepackagerelease not in self.imported_sources:
            self.imported_sources.append(sourcepackagerelease)

    def _store_bprelease_for_publishing(self, binarypackage, archtag):
        """Append to the binarypackage imported list."""
        if archtag not in self.imported_bins.keys():
            self.imported_bins[archtag] = []

        self.imported_bins[archtag].append(binarypackage)

    def _store_archinfo(self, archtag):
        """Append retrived distroarchrelease info to a dict."""
        if archtag in self.archinfo.keys():
            return

        info = self._get_distroarchrelease_info(archtag)
        self.archinfo[archtag] = info

    def ensure_sourcepackagename(self, name):
        """Import only the sourcepackagename ensuring them."""
        self.sphandler.ensureSourcePackageName(name)

    def preimport_sourcecheck(self, sourcepackagedata):
        """
        Check if this SourcePackageRelease already exists. This can
        happen, for instance, if a source package didn't change over
        releases, or if Gina runs multiple times over the same release
        """
        sourcepackagerelease = self.sphandler.checkSource(sourcepackagedata, 
                                                          self.distrorelease)
        if not sourcepackagerelease:
            log.debug('SPR not found in preimport: %r %r' %
                (sourcepackagedata.package, sourcepackagedata.version))
            return None

        # Append to the sourcepackagerelease imported list.
        self._store_sprelease_for_publishing(sourcepackagerelease)
        return sourcepackagerelease

    def import_sourcepackage(self, sourcepackagedata):
        """Handler the sourcepackage import process"""
        assert not self.sphandler.checkSource(sourcepackagedata,
                                              self.distrorelease)
        handler = self.sphandler.createSourcePackageRelease
        sourcepackagerelease = handler(sourcepackagedata,
                                       self.distrorelease)

        self._store_sprelease_for_publishing(sourcepackagerelease)
        return sourcepackagerelease

    def preimport_binarycheck(self, archtag, binarypackagedata):
        """
        Check if this BinaryPackageRelease already exists. This can
        happen, for instance, if a binary package didn't change over
        releases, or if Gina runs multiple times over the same release
        """
        self._store_archinfo(archtag)
        distroarchinfo = self.archinfo[archtag]
        binarypackagerelease = self.bphandler.checkBin(binarypackagedata,
                                                       distroarchinfo)
        if not binarypackagerelease:
            log.debug('BPR not found in preimport: %r %r %r' %
                (binarypackagedata.package, binarypackagedata.version,
                 binarypackagedata.architecture))
            return None

        # Append to the sourcepackagerelease imported list.
        self._store_bprelease_for_publishing(binarypackagerelease, archtag)
        return binarypackagerelease

    def import_binarypackage(self, archtag, binarypackagedata):
        """Handler the binarypackage import process"""
        self._store_archinfo(archtag)
        distroarchinfo = self.archinfo[archtag]

        # We know that preimport_binarycheck has run
        assert not self.bphandler.checkBin(binarypackagedata, distroarchinfo)

        # Find the sourcepackagerelease that generated this binarypackage.
        distrorelease = distroarchinfo['distroarchrelease'].distrorelease
        sourcepackage = self.sphandler.getSourceForBinary(
            binarypackagedata, distrorelease)

        if not sourcepackage:
            # We couldn't find a sourcepackagerelease in the database.
            # Perhaps we can opportunistically pick one out of the archive.
            log.warn("No source package %s (%s) listed for %s (%s), "
                     "scrubbing archive..." %
                (binarypackagedata.source,
                 binarypackagedata.source_version,
                 binarypackagedata.package,
                 binarypackagedata.version))
            sourcepackage = self.sphandler.findAndImportUnlistedSourcePackage(
                binarypackagedata, distrorelease)

        if not sourcepackage:
            # XXX: untested
            # If the sourcepackagerelease is not imported, not way to import
            # this binarypackage. Warn and giveup.
            raise NoSourcePackageError("No source package %s (%s) found "
                "for %s (%s)" % (binarypackagedata.name,
                                 binarypackagedata.version,
                                 binarypackagedata.source,
                                 binarypackagedata.source_version))

        binarypackage = self.bphandler.createBinaryPackage(binarypackagedata,
                                                           sourcepackage,
                                                           distroarchinfo,
                                                           archtag)
        self._store_bprelease_for_publishing(binarypackage, archtag)

    def publish_sourcepackages(self, pocket):
        log.info('Publishing Source Packages...')
        publisher = SourcePublisher(self.distrorelease)
        for spr in self.imported_sources:
            publisher.publish(spr, pocket)
        log.info('done')

    def publish_binarypackages(self, pocket):
        log.info('Publishing Binary Packages...')
        for archtag, binarypackages in self.imported_bins.iteritems():
            archinfo = self.archinfo[archtag]
            distroarchrelease = archinfo['distroarchrelease']
            publisher = BinaryPackagePublisher(distroarchrelease)
            for binary in binarypackages:
                publisher.publish(binary, pocket)
        log.info('done')


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


class SourcePackageReleaseHandler:
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

    def findAndImportUnlistedSourcePackage(self, binarypackagedata,
                                           distrorelease):
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
        assert not self.getSourceForBinary(binarypackagedata,
                                           distrorelease)

        sp_name = binarypackagedata.source
        sp_version = binarypackagedata.source_version
        sp_component = binarypackagedata.component
        sp_section = binarypackagedata.section

        log.debug("Looking for source package %r (%r) in %r" %
                  (sp_name, sp_version, sp_component))

        sp_data = self._getSourcePackageDataFromDSC(sp_name,
            sp_version, sp_component, sp_section)

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
        SourcePublisher(distrorelease).publish(spr, self.pocket)

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


    def getSourceForBinary(self, binarypackagedata, distrorelease):
        """Get a SourcePackageRelease for a BinaryPackage"""
        try:
            spname = SourcePackageName.byName(binarypackagedata.source)
        except SQLObjectNotFound:
            return None

        # Check if this sourcepackagerelease already exists using name and
        # version
        return self._getSource(spname,
                               binarypackagedata.source_version,
                               distrorelease)

    def checkSource(self, sourcepackagedata, distrorelease):
        """Check if a sourcepackagerelease is already on lp db.

        Returns the sourcepackagerelease if exists or none if not.
        """
        try:
            spname = SourcePackageName.byName(sourcepackagedata.package)
        except SQLObjectNotFound:
            return None

        # Check if this sourcepackagerelease already exists using name and
        # version
        return self._getSource(spname,
                               sourcepackagedata.version,
                               distrorelease)

    def _getSource(self, sourcepackagename, version, distrorelease):
        """Returns a sourcepackagerelease by its name and version."""
        distributionID=distrorelease.distribution.id
        query = """
                sourcepackagerelease.sourcepackagename = %s AND
                sourcepackagerelease.version = %s AND
                sourcepackagepublishing.sourcepackagerelease = 
                    sourcepackagerelease.id AND
                sourcepackagepublishing.distrorelease = distrorelease.id AND
                distrorelease.distribution = %s
                """ % (sourcepackagename.id, quote(version), distributionID)
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


class SourcePublisher:
    """Class to handle the sourcepackagerelease publishing process."""

    def __init__(self, distrorelease):
        # Get the distrorelease where the sprelease will be published.
        self.distrorelease = distrorelease

    def publish(self, sourcepackagerelease, pocket):
        """Create the publishing entry on db if does not exist."""
        # Check if the sprelease is already published and if so, just
        # report it.
        log.debug('Publishing SourcePackage %s-%s' % (
            sourcepackagerelease.sourcepackagename.name, 
            sourcepackagerelease.version))
        source_publishinghistory = self._checkPublishing(
            sourcepackagerelease, self.distrorelease)
        if source_publishinghistory:
            log.debug('SourcePackageRelease already published as %s' %
                      source_publishinghistory.status.title)
            return

        # XXX: Component may be incorrect: this code does not cope with
        # source packages not listed in Sources.gz (added by
        # findAndImportUnlistedSourcePackage) that have moved around in
        # the pool. We should be using locate_source_package_in_pool()
        # here instead of the strict component name. Section may suffer
        # from the same problem.
        #
        # Create the Publishing entry with status PENDING so that we can
        # republish this later into a Soyuz archive.
        SecureSourcePackagePublishingHistory(
            distrorelease=self.distrorelease.id,
            sourcepackagerelease=sourcepackagerelease.id,
            status=PackagePublishingStatus.PENDING,
            component=sourcepackagerelease.component.id,
            section=sourcepackagerelease.section.id,
            datecreated=nowUTC,
            datepublished=nowUTC,
            pocket=pocket
            )
        log.debug('SourcePackageRelease %s-%s published' % (
            sourcepackagerelease.sourcepackagename.name,
            sourcepackagerelease.version))

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
            licence = bin.licence,
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
    def __init__(self, distroarchrelease):
        self.distroarchrelease = distroarchrelease

    def publish(self, binarypackage, pocket):
        """Create the publishing entry on db if does not exist."""
        log.debug('Publishing BinaryPackage %s-%s' % (
            binarypackage.binarypackagename.name, binarypackage.version))

        # Check if the binarypackage is already published and if yes,
        # just report it.
        binpkg_publishinghistory = self._checkPublishing(
            binarypackage, self.distroarchrelease)
        if binpkg_publishinghistory:
            log.debug('Binarypackage already published as %s' % (
                binpkg_publishinghistory.status.title))
            return

        # Create the Publishing entry with status PENDING.
        SecureBinaryPackagePublishingHistory(
            binarypackagerelease = binarypackage.id,
            component = binarypackage.component,
            section = binarypackage.section,
            priority = binarypackage.priority,
            distroarchrelease = self.distroarchrelease.id,
            status = PackagePublishingStatus.PENDING,
            datecreated = nowUTC,
            datepublished = nowUTC,
            pocket = pocket,
            datesuperseded = None,
            supersededby = None,
            datemadepending = None,
            dateremoved = None,
            )

        log.debug('BinaryPackage %s-%s published.' % (
            binarypackage.binarypackagename.name, binarypackage.version))


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

