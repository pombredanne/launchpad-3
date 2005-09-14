# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina db handlers.

Classes to handle and create entries on launchpad db.
"""
__all__ = ['ImporterHandler', 'BinaryPackageHandler', 'BinaryPackagePublisher',
'SourcePackageReleaseHandler', 'SourcePublisher', 'DistroHandler',
'PersonHandler']

import os
from string import split

from sqlobject import SQLObjectNotFound

from zope.component import getUtility

from canonical.launchpad.scripts.gina.library import getLibraryAlias

from canonical.lp import initZopeless
from canonical.launchpad.database import (Distribution, DistroRelease,
    DistroArchRelease,Processor, SourcePackageName, SourcePackageRelease,
    Build, BinaryPackageRelease, BinaryPackageName,
    SecureBinaryPackagePublishingHistory,
    Component, Section, SourcePackageReleaseFile,
    SecureSourcePackagePublishingHistory, BinaryPackageFile)

from canonical.launchpad.interfaces import IPersonSet, IBinaryPackageNameSet
from canonical.launchpad.helpers import getFileType, getBinaryPackageFormat

from canonical.database.sqlbase import quote

from canonical.lp.dbschema import (PackagePublishingStatus,
    BinaryPackagePriority, SourcePackageUrgency, BuildStatus)

from canonical.launchpad.scripts import log
from canonical.database.constants import nowUTC
from canonical.config import config
from canonical import encoding
from canonical.launchpad.validators.version import valid_debian_version

priomap = {
    "low": SourcePackageUrgency.LOW,
    "medium": SourcePackageUrgency.LOW,
    "high": SourcePackageUrgency.LOW,
    "emergency": SourcePackageUrgency.LOW
    # FUCK_PEP8 -- Fuck it right in the ear
    }

prioritymap = {
"required": BinaryPackagePriority.REQUIRED,
"important": BinaryPackagePriority.IMPORTANT,
"standard": BinaryPackagePriority.STANDARD,
"optional": BinaryPackagePriority.OPTIONAL,
"extra": BinaryPackagePriority.EXTRA,
"source": BinaryPackagePriority.EXTRA #Some binarypackages ended up
                                           #with priority source.
}

class DisplaynameDecodingError(Exception):
    """Not valid unicode displayname"""
    def __init__(self, displayname):
        message = "Could not decode %s" % (displayname)
        Exception.__init__(self, message)

class ImporterHandler:
    """ Import Handler class
    
    This class is used to handle the import process.
    """
    def __init__(self, distro_name, distrorelease_name, dry_run):
        self.ztm = initZopeless(dbuser=config.gina.dbuser)

        # Store basic import info.
        self.distro = self._get_distro(distro_name)
        self.distrorelease = self._get_distrorelease(distrorelease_name)
        self.dry_run = dry_run

        # Info about architectures.
        self.archinfo_cache ={}
        
        self.imported_sources = []
        self.imported_bins ={}

        # Create a sourcepackagerelease handler
        self.sphandler = SourcePackageReleaseHandler()

        # Create a binarypackage handler
        self.bphandler = BinaryPackageHandler()
        


    def commit(self):
        """Commit to the database."""
        if not self.dry_run:
            self.ztm.commit()
    
    #
    # Distro Stuff: Should go to DistroHandler
    #
    def _get_distro(self, name):
        """Return the distro database object by name."""
        distro = Distribution.selectOneBy(name=name)
        if not distro:
            raise ValueError, "Error finding distribution for %s" % name
        return distro

    def _get_distrorelease(self, name):
        """Return the distrorelease database object by name."""
        dr = DistroRelease.selectOneBy(name=name,
                                       distributionID=self.distro.id)
        if not dr:
            raise ValueError, "Error finding distrorelease for %s" % name
        return dr


    def _get_distroarchrelease_info(self, archtag):
        """Get the distroarchrelease and processor using the architecturetag"""
        dar = DistroArchRelease.selectOneBy(\
                distroreleaseID=self.distrorelease.id,
                architecturetag=archtag)
        if not dar:
            raise ValueError, \
                  ("Error finding distroarchrelease for %s/%s"
                   % (self.distrorelease.name, archtag)
                   )
        
        processor = Processor.selectOneBy(familyID=dar.processorfamily.id)
        if not processor:
            raise ValueError, \
                  ("Unable to find a processor from the processor family"
                   "chosen from %s/%s"
                   % (self.distrorelease.name, archtag))

        return {'distroarchrelease': dar, 'processor': processor}
            
        
    #
    # Distro Stuff
    #
        

    def _cache_sprelease(self, sourcepackagerelease):
        """Append to the sourcepackagerelease imported list."""
        if sourcepackagerelease not in self.imported_sources:
            self.imported_sources.append(sourcepackagerelease)

    def _cache_binaries(self, binarypackage, archtag):
        """Append to the binarypackage imported list."""
        if archtag not in self.imported_bins.keys():
            self.imported_bins[archtag]=[]

        self.imported_bins[archtag].append(binarypackage)

    def _cache_archinfo(self, archtag):
        """Append retrived distroarchrelease info to a cache."""
        if archtag in self.archinfo_cache.keys():
            return
        
        info = self._get_distroarchrelease_info(archtag)
        self.archinfo_cache[archtag]=info


    def preimport_sourcecheck(self, sourcepackagedata):
        """Check if SourcePackage already exists from a non-processed data"""
        sourcepackagerelease = self.sphandler.checkSource(sourcepackagedata)
        if not sourcepackagerelease:
            return None

        # Append to the sourcepackagerelease imported list.
        self._cache_sprelease(sourcepackagerelease)
        return sourcepackagerelease

    def import_sourcepackagename(self, name):
        """Import only the sourcepackagename ensuring them."""
        self.sphandler.ensureSourcePackageName(name)

    def import_sourcepackage(self, sourcepackagedata):
        """Handler the sourcepackage import process"""

        # Check if the sourcepackagerelease already exists.
        sourcepackagerelease = self.sphandler.checkSource(sourcepackagedata)
        if sourcepackagerelease:
            log.debug('Sourcepackagerelease %s version %s already exists' %(
                sourcepackagedata.package, sourcepackagedata.version
                ))
        else:
            # If not, create it.
            handler = self.sphandler.createSourcePackageRelease
            sourcepackagerelease = handler(sourcepackagedata,
                                           self.distrorelease)

        # Append to the sourcepackagerelease imported list.
        if sourcepackagerelease:
            self._cache_sprelease(sourcepackagerelease)

        return sourcepackagerelease

    def import_binarypackage(self, archtag, binarypackagedata):
        """Handler the binarypackage import process"""

        self._cache_archinfo(archtag)
        distroarchinfo = self.archinfo_cache[archtag]

        # Check if the binarypackage already exists.
        binarypackage = self.bphandler.checkBin(binarypackagedata,
                                                distroarchinfo)
        if binarypackage:
            # Already imported, so return it.
            log.debug('Binarypackage %s version %s already exists for %s' % (
                binarypackagedata.package, binarypackagedata.version, archtag
                ))
            self._cache_binaries(binarypackage, archtag)
            return binarypackage

        # Find the sourcepackagerelease that generate this binarypackage.
        sourcepackage = self.sphandler.getSourceToBinary(binarypackagedata)
        if not sourcepackage:
            # If the sourcepackagerelease is not imported, not way to import
            # this binarypackage. Warn and giveup.
            log.info("FMO courtesy of TROUP & TROUT inc. on %s (%s)" % (
                binarypackagedata.source, binarypackagedata.source_version
                ))
            return None

        # Create the binarypackage on db and import into librarian
        binarypackage = self.bphandler.createBinaryPackage(binarypackagedata,
                                                           sourcepackage,
                                                           distroarchinfo)
        if binarypackage is None:
            log.error("Unable to createBinaryPackage on %s (%s)" % (
                binarypackagedata.source, binarypackagedata.source_version
                ))
            return None

        # Cache it and return.
        self._cache_binaries(binarypackage, archtag)
        return binarypackage

    def publish_sourcepackages(self, pocket):
        publisher = SourcePublisher(self.distrorelease)
        log.info('Starting sourcepackages publishing process...')
        # Goes over the imported sourcepackages publishing them.
        for spr in self.imported_sources:
            publisher.publish(spr, pocket)

    def publish_binarypackages(self, pocket):
        """Publish all the binaries present on the binary cache."""
        log.info('Starting binarypackages publishing process...')
        for archtag, binarypackages in self.imported_bins.iteritems():
            distroarchrelease = \
                              self.archinfo_cache[archtag]['distroarchrelease']
            publisher = BinaryPackagePublisher(distroarchrelease)
            for binary in binarypackages:
                publisher.publish(binary, pocket)
        log.debug('Pushing done...')

class BinaryPackageHandler:
    """Handler to deal with binarypackages."""
    def __init__(self):
        # Create other needed object handlers.
        self.person_handler = PersonHandler()
        self.distro_handler = DistroHandler()
        self.source_handler = SourcePackageReleaseHandler()

    def checkBin(self, binarypackagedata, archinfo):
        try:
            # First check if the Binarypackagename exists.
            bin_name = BinaryPackageName.byName(binarypackagedata.package)
        except SQLObjectNotFound:
            return None

        # Return the Binaripackage if exists.
        return self._getBinary(bin_name, binarypackagedata.version,
                               binarypackagedata.architecture,
                               archinfo)

    def _getBinary(self, binaryname, version, architecture, distroarchinfo):
        """Returns a binarypackage if it exists."""
        if architecture == "all":
            binpkg = BinaryPackageRelease.selectOneBy(
                binarypackagenameID=binaryname.id, version=version)

            if binpkg:
                return binpkg

        clauseTables=("BinaryPackageRelease","Build",)
        query = ("BinaryPackageRelease.binarypackagename=%s AND "
                 "BinaryPackageRelease.version=%s AND "
                 "Build.Processor=%s AND "
                 "Build.distroarchrelease=%s AND "
                 "Build.id = BinaryPackageRelease.build"
                 % (binaryname.id,
                    quote(version),
                    distroarchinfo['processor'].id,
                    distroarchinfo['distroarchrelease'].id)
                 )

        return BinaryPackageRelease.selectOne(query, clauseTables=clauseTables)
            
        
    def createBinaryPackage(self, bin, srcpkg, distroarchinfo):
        """Create a new binarypackage."""

        # Ensure a binarypackagename for this binarypackage.
        bin_name = getUtility(IBinaryPackageNameSet).ensure(bin.package)

        # Ensure a build record for this binarypackage.
        build = self.ensureBuild(bin, srcpkg, distroarchinfo)
        if not build:
            # Create build fealure. Return to make it keep going.
            return
               
        # Get binarypackage the description.
        description = encoding.guess(bin.description)

        # Build a sumary using the description.
        summary = description.split("\n")[0]
        if summary[-1] != '.':
            summary = summary + '.'

        # XXX: Daniel Debonzi
        # Keep it til we have licence on the SourcePackageRelease Table
        if hasattr(srcpkg, 'licence'):
            licence = encoding.guess(srcpkg.licence)
        else:
            licence = ''

        # Get component and section from lp db.
        componentID = self.distro_handler.getComponentByName(bin.component).id
        sectionID = self.distro_handler.ensureSection(bin.section).id

        
        # Check the architecture.
        architecturespecific = (bin.architecture == "all")

        # Some binary packages lack priority. Better to import them with
        # priority 'extra' than not to import them at all. Remove these
        # lines when we don't want to import these packages anymore.
        if not hasattr(bin, 'priority'):
            bin.priority = 'extra'

        # Sanity checking - priority has been known to be missing
        bin_required = [
            'version', 'filename', 'priority', 'installed_size',
            ]
        missing = [attr for attr in bin_required if not hasattr(bin, attr)]
        if missing:
            log.error("Binary package info missing %s" % ' '.join(missing))
            return None

        # Create the binarypackage entry on lp db.
        binpkg = BinaryPackageRelease(
            binarypackagename = bin_name.id,
            component = componentID,
            version = bin.version,
            summary = summary,
            description = description,
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
            essential = False,
            installedsize = int(bin.installed_size),
            licence = licence,
            architecturespecific = architecturespecific,
            copyright = None
            )

        # Insert file into Librarian

        fdir, fname = os.path.split(bin.filename)
        log.debug('Including %s into librarian' % fname)
        try:
            alias = getLibraryAlias(
                    "%s/%s" % (bin.package_root, fdir), fname
                    )
        except IOError:
            log.debug('Package %s not found on archive %s/%s/%s' % (
                fname, bin.package_root, fdir, fname
                ))
        else:
            self.createBinaryPackageFile(binpkg, fname, alias)

        # Return the binarypackage object.
        return binpkg

    def createBinaryPackageFile(self, binpkg, fname, alias):
        """Create the binarypackagefile entry on lp db."""
        BinaryPackageFile(binarypackagerelease=binpkg.id,
                          libraryfile=alias,
                          filetype=getFileType(fname))



    def ensureBuild(self, bin, srcpkg, distroarchinfo):
        """Ensure a build record."""
        distroarchrelease = distroarchinfo['distroarchrelease']
        processor = distroarchinfo['processor']
        
        # XXX: Check it later -- Debonzi 20050516
##         if bin.gpg_signing_key_owner:
##             key = self.getGPGKey(bin.gpg_signing_key, 
##                                  *bin.gpg_signing_key_owner)
##         else:
        key = None

        # Try to select a build.
        build = Build.selectOneBy(sourcepackagereleaseID=srcpkg.id,
                                  processorID=processor.id,
                                  distroarchreleaseID=distroarchrelease.id)

        if build:
            # If already exists, return it.
            return build

        # Nothing to do if we fail we insert...
        log.debug("Unable to retrieve build for %d; making new one..." % (
                srcpkg.id,
                ))

        # If does not exists, create a new record and return.
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
            binarypackage.binarypackagename.name, binarypackage.version,
            ))

        # Check if the binarypackage is already published and if yes,
        # just report it.
        binpkg_publishinghistory = self._checkPublishing(
            binarypackage, self.distroarchrelease)
        if binpkg_publishinghistory:
            log.debug('Binarypackage already published as %s' % (
                binpkg_publishinghistory.status.title,
                ))
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
            binarypackage.binarypackagename.name, binarypackage.version,
            ))


    def _checkPublishing(self, binarypackage, distroarchrelease):
        """Query for the publishing entry"""
        return SecureBinaryPackagePublishingHistory.selectOneBy(
            binarypackagereleaseID=binarypackage.id,
            distroarchreleaseID=distroarchrelease.id)


class SourcePackageReleaseHandler:
    """SourcePackageRelease Handler class

    This class has methods to make the sourcepackagerelease access
    on the launchpad db a little easier.
    """
    def __init__(self):
        self.person_handler = PersonHandler()
        self.distro_handler = DistroHandler()

    def getSourceToBinary(self, binarypackagedata):
        """Get a SourcePackageRelease to a BinaryPackage"""
        try:
            spname = SourcePackageName.byName(binarypackagedata.source)
        except SQLObjectNotFound:
            return None

        # Check if this sourcepackagerelease already exists using name and
        # version
        return self._getSource(spname, binarypackagedata.source_version)
        

    def checkSource(self, sourcepackagedata):
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
                               sourcepackagedata.version)
        

    def _getSource(self, sourcepackagename, version):
        """Returns a sourcepackagerelease by its name and version."""

        return SourcePackageRelease.selectOneBy(\
                            sourcepackagenameID=sourcepackagename.id,
                            version=version)


    def createSourcePackageRelease(self, src, distrorelease):
        """Create a SourcePackagerelease and db dependencies if needed.
        
        Returns the created SourcePackageRelease, or None if it failed.
        """

        displayname, emailaddress = src.maintainer
        try:
            maintainer = self.person_handler.ensurePerson(displayname,
                                                          emailaddress)
        except DisplaynameDecodingError:
            # problems decoding name in  utf8
            log.warn('Could not create person %s' % src.maintainer[1])
            return None

# XXX: Check it later -- Debonzi 20050516
##         if src.dsc_signing_key_owner:
##             key = self.getGPGKey(src.dsc_signing_key, 
##                                  *src.dsc_signing_key_owner)
##         else:
##             key = None
 
        key=None # FIXIT
        dsc = encoding.guess(src.dsc)

        try:
            changelog = encoding.guess(src.changelog[0]["changes"])
        except IndexError:
            changelog = None

        componentID = self.distro_handler.getComponentByName(src.component).id
        sectionID = self.distro_handler.ensureSection(src.section).id

        # urgency is not null for us, but seems that some sourcepackage
        # has no urgency.
        if not hasattr(src, 'urgency'):
            src.urgency = "low"

        if src.urgency not in priomap:
            src.urgency = "low"

        name = self.ensureSourcePackageName(src.package)

        if not valid_debian_version(src.version):
            log.warn('%s has an invalid version %s', name.name, src.version)
            return None

        spr = SourcePackageRelease(sourcepackagename=name.id,
                                   version=src.version,
                                   maintainer=maintainer.id,
                                   dateuploaded=src.date_uploaded,
                                   builddepends=src.build_depends,
                                   builddependsindep=src.build_depends_indep,
                                   architecturehintlist=src.architecture,
                                   component=componentID,
                                   creator=maintainer.id,
                                   urgency=priomap[src.urgency],
                                   changelog=changelog,
                                   dsc=dsc,
                                   dscsigningkey=key,
                                   section=sectionID,
                                   manifest=None,
                                   uploaddistrorelease=distrorelease.id)
        

        # Insert file into the library and create the
        # SourcePackageReleaseFile entry on lp db.
        for i in src.files:
            fname = i[-1]
            path = "%s/%s" %(src.package_root, src.directory)
            try:
                alias = getLibraryAlias(path, fname)
            except IOError:
                log.info('Package %s not found on archive %s/%s' %(
                    fname, path, fname))
            else:
                log.info('Package %s included into library' % fname)
                self.createSourcePackageReleaseFile(spr, fname, alias)

        return spr

    def createSourcePackageReleaseFile(self, spr, fname, alias):
        """Create the SourcePackageReleaseFile entry on lp db."""

        SourcePackageReleaseFile(sourcepackagerelease=spr.id,
                                 libraryfile=alias,
                                 filetype=getFileType(fname))

    def ensureSourcePackageName(self, name):
        return SourcePackageName.ensure(name)

class SourcePublisher:
    """Class to handle the sourcepackagerelease publishing process."""

    def __init__(self, distrorelease):
        # Get the distrorelease where the sprelease will be published.
        self.distrorelease = distrorelease

    def publish(self, sourcepackagerelease, pocket):
        """Create the publishing entry on db if does not exist."""
        log.debug('Publishing SourcePackageRelease %s-%s' % (
            sourcepackagerelease.sourcepackagename.name,
            sourcepackagerelease.version,
            ))

        # Check if the sprelease is already published and if yes,
        # just report it.
        souce_publishinghistory = self._checkPublishing(
            sourcepackagerelease, self.distrorelease)
        if souce_publishinghistory:
            log.debug('SourcePackageRelease already published as %s' % (
                souce_publishinghistory.status.title
                ))
            return
        
        # Create the Publishing entry with status PENDING.
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
            sourcepackagerelease.version,
            ))


    def _checkPublishing(self, sourcepackagerelease, distrorelease):
        """Query for the publishing entry"""
        return SecureSourcePackagePublishingHistory.selectOneBy(
            sourcepackagereleaseID=sourcepackagerelease.id,
            distroreleaseID=distrorelease.id)

class DistroHandler:
    """Class handler some distro related informations."""

    def __init__(self):
        # Create a cache for components and sections
        # to do not query db all the time.
        self.compcache = {} 
        self.sectcache = {}

    def getComponentByName(self, component):
        """Returns a component object by its name."""
        if component in self.compcache:
            return self.compcache[component]

        ret = Component.selectOneBy(name=component)

        if not ret:
            raise ValueError, "Component %s not found" % component

        self.compcache[component] = ret
        log.info("Component %s is %s" % \
              (component, self.compcache[component].id))

        return ret

    def ensureSection(self, section):
        """Returns a section object by its name.
        Create and return if does not exists.
        """
        if '/' in section:
            section = section[section.find('/')+1:]
        if section in self.sectcache:
            return self.sectcache[section]

        ret = Section.selectOneBy(name=section)

        if not ret:
            ret = Section(name=section)

        self.sectcache[section] = ret
        log.info("Section %s is %s" % (section, self.sectcache[section].id))
        return ret

    
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

        try:
            displayname = encoding.guess(displayname)
        except UnicodeDecodeError:
            raise DisplaynameDecodingError(displayname)

        givenname = split(displayname)[0]

        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email=emailaddress, displayname=displayname, givenname=givenname)
        return person

