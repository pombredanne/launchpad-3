import re
from sets import Set
from pyPgSQL import PgSQL

# Disable cursors for now (can cause issues sometimes it seems)
PgSQL.noPostgresCursor = 1

from canonical.lp import initZopeless
from canonical.foaf.nickname import generate_nick
from canonical.launchpad.database import Distribution, DistroRelease, \
                                         DistroArchRelease,Processor, \
                                         SourcePackageName, \
                                         SourcePackageRelease, Build, \
                                         BinaryPackage, BinaryPackageName, \
                                         Person, EmailAddress, GPGKey, \
                                         PackagePublishingHistory, \
                                         Component, Section, \
                                         SourcePackagePublishingHistory, \
                                         SourcePackageReleaseFile, \
                                         BinaryPackageFile

from canonical.database.sqlbase import quote

from canonical.lp.dbschema import PackagePublishingStatus,  \
                                  EmailAddressStatus, \
                                  SourcePackageFormat, \
                                  BinaryPackagePriority, \
                                  SourcePackageUrgency, \
                                  SourcePackageFileType, \
                                  BinaryPackageFileType, \
                                  BinaryPackageFormat, \
                                  BuildStatus, \
                                  GPGKeyAlgorithm

from canonical.database.constants import nowUTC

priomap = {
    "low": SourcePackageUrgency.LOW,
    "medium": SourcePackageUrgency.LOW,
    "high": SourcePackageUrgency.LOW,
    "emergency": SourcePackageUrgency.LOW
    # FUCK_PEP8 -- Fuck it right in the ear
    }


class SQLThingBase:
    def ensure_string_format(self, name):
        assert isinstance(name, basestring), repr(name)
        try:
            # check that this is unicode data
            name.decode("utf-8").encode("utf-8")
            return name
        except UnicodeError:
            # check that this is latin-1 data
            s = name.decode("latin-1").encode("utf-8")
            s.decode("utf-8")
            return s

class SQLThing(SQLThingBase):
    def __init__(self, dbname, dry_run):
        self.dbname = dbname
        self.dry_run = dry_run
        self.db = PgSQL.connect(database=self.dbname)

    def commit(self):
        if self.dry_run:
            # Not committing -- we're on a dry run
            return
        return self.db.commit()
    
    def close(self):
        return self.db.close()

    def _get_dicts(self, cursor):
        names = [x[0] for x in cursor.description]
        ret = []
        for item in cursor.fetchall():
            res = {}
            for i in range(len(names)):
                res[names[i]] = item[i]
            ret.append(res)
        return ret

    def _query_to_dict(self, query, args=None):
        cursor = self._exec(query, args)
        return self._get_dicts(cursor)
        
    def _query(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        results = cursor.fetchall()
        return results
    
    def _query_single(self, query, args=None):
        q = self._query(query, args)
        if len(q) == 1:
            return q[0]
        elif not q:
            return None
        else:
            raise AssertionError, "%s killed us on %s %s" \
                % (len(q), query, args)

    def _exec(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        return cursor

    def _insert(self, table, data):
        keys = data.keys()
        query = "INSERT INTO %s (%s) VALUES (%s)" \
                 % (table, ",".join(keys), ",".join(["%s"] * len(keys)))
        #print query
        try:
            self._exec(query, data.values())
        except Exception, e:
            print "Bad things happened, data was %s" % data
            print "Exception was: %s" % e
            raise

class Katie(SQLThing):

    def __init__(self, bar, suite, dry_run):
        SQLThing.__init__(self, bar, dry_run)
        self.suite = suite

    def getSourcePackageRelease(self, name, version):
        print "\t\t* Hunting for release %s / %s" % (name,version)
        ret =  self._query_to_dict("""SELECT * FROM source, fingerprint
                                      WHERE  source = %s 
                                      AND    source.sig_fpr = fingerprint.id
                                      AND    version = %s""", (name, version))
        if not ret:
            return None #Shortcircuit because the ubuntu lookup fails
            print "\t\t* that spr didn't turn up. Attempting to find via ubuntu*"
        else:
            return ret

        return self._query_to_dict("""SELECT * FROM source, fingerprint
                                      WHERE  source = %s 
                                      AND    source.sig_fpr = fingerprint.id
                                      AND    version like '%subuntu%s'""" % ("%s", version, "%"), name)
        
    
    def getBinaryPackageRelease(self, name, version, arch):  
        return self._query_to_dict("""SELECT * FROM binaries, architecture, 
                                                    fingerprint
                                      WHERE  package = %s 
                                      AND    version = %s
                                      AND    binaries.sig_fpr = fingerprint.id
                                      AND    binaries.architecture =
                                                architecture.id
                                      AND    arch_string = %s""",
                                        (name, version, arch))
    def getSections(self):
        return self._query("""SELECT section FROM section""")

    def getSourceSection(self, sourcepackage):
        return self._query_single("""
        SELECT section.section
          FROM section,
               override,
               suite

         WHERE override.section = section.id
           AND suite.id = override.suite
           AND override.package = %s
           AND suite.suite_name = %s
        """, (sourcepackage, self.suite))[0]

prioritymap = {
"required": BinaryPackagePriority.REQUIRED,
"important": BinaryPackagePriority.IMPORTANT,
"standard": BinaryPackagePriority.STANDARD,
"optional": BinaryPackagePriority.OPTIONAL,
"extra": BinaryPackagePriority.EXTRA,
"source": BinaryPackagePriority.EXTRA #Some binarypackages ended up
                                           #with priority source.
}

class Launchpad(SQLThingBase):
    def __init__(self, bar, distro, dr, proc, dry_run):
        self.ztm = initZopeless()
        self.dry_run = dry_run
        self.compcache = {}
        self.sectcache = {}
        try:            
            self.distro = Distribution.selectBy(name=distro)[0]
        except:
            raise ValueError, "Error finding distribution for %s" % distro

        try:
            self.distrorelease = DistroRelease.selectBy(name=dr,
                                         distributionID=self.distro.id)[0]
        except:
            raise ValueError, "Error finding distrorelease for %s" % dr

        try:
            dar = DistroArchRelease.selectBy(\
                distroreleaseID=self.distrorelease.id,
                architecturetag=proc)[0]

            self.processor = dar.processorfamily
            self.distroarchrelease = dar
        except:
            raise ValueError, \
                  "Error finding distroarchrelease for %s/%s" % (dr,proc)

        try:
            self.processor = Processor.selectBy(\
                             familyID=self.processor.id)[0]
        except:
            raise ValueError, \
                  ("Unable to find a processor from the processor family"
                   "chosen from %s/%s" % (dr, proc))

        print ("INFO: Chosen D(%d) DR(%d), PROC(%d), "
               "DAR(%d) from SUITE(%s), ARCH(%s)" %
               (self.distro.id, self.distrorelease.id, self.processor.id,
                self.distroarchrelease.id, dr, proc))
        

    def commit(self):
        if self.dry_run:
            # Not committing -- we're on a dry run
            return
        return self.ztm.commit()


    def getFileType(self, fname):
        if fname.endswith(".deb"):
            return BinaryPackageFileType.DEB
        if fname.endswith(".udeb"):
            return BinaryPackageFileType.DEB
        if fname.endswith(".dsc"):
            return SourcePackageFileType.DSC
        if fname.endswith(".diff.gz"):
            return SourcePackageFileType.DIFF
        if fname.endswith(".orig.tar.gz"):
            return SourcePackageFileType.ORIG
        if fname.endswith(".tar.gz"):
            return SourcePackageFileType.TARBALL

    def getBinaryPackageFormat(self, fname):
        if fname.endswith(".deb"):
            return BinaryPackageFormat.DEB
        if fname.endswith(".udeb"):
            return BinaryPackageFormat.UDEB
        if fname.endswith(".rpm"):
            return BinaryPackageFormat.RPM
        
        

    #
    # SourcePackageName
    #
    def ensureSourcePackageName(self, name):
        return SourcePackageName.ensure(name)

    def getSourcePackageName(self, name):
        return SourcePackageName.selectBy(name=name)

    #
    # SourcePackageRelease
    #
    def getSourcePackageRelease(self, name, version):

        name = self.ensureSourcePackageName(name)

        spr = SourcePackageRelease.selectBy(sourcepackagenameID=name.id,
                                            version=version)

        if not spr.count():
            return None

        return spr

    def createSourcePackageReleaseFile(self, src, fname, alias):
        r = self.getSourcePackageRelease(src.package, src.version)
        if not r:
            raise ValueError, "Source not yet in database"

        # BIG XXX: Daniel Debonzi 20050223
        # If commit is not performed here
        # the database says that libraryfilealias.id=alias
        # is not on db, because it was included by librarian
        # and somehow the initZopeless db connection can't "see"
        # this db modification.
        self.commit()
        
        if self.dry_run:
            # Data was not commited and due to the BIG XXX above
            # create SourcePackageReleaseFile will fail so just
            # skip it
            return
        SourcePackageReleaseFile(sourcepackagerelease=r[0].id,
                                 libraryfile=alias,
                                 filetype=self.getFileType(fname))

    def createSourcePackageRelease(self, src):

        maintid = self.getPeople(*src.maintainer)[0]
        if src.dsc_signing_key_owner:
            key = self.getGPGKey(src.dsc_signing_key, 
                                 *src.dsc_signing_key_owner)
        else:
            key = None

        dsc = self.ensure_string_format(src.dsc)
        try:
            changelog = self.ensure_string_format(src.changelog[0]["changes"])
        except IndexError:
            changelog = None
        componentID = self.getComponentByName(src.component).id
        sectionID = self.getSectionByName(src.section).id
        if src.urgency not in priomap:
            src.urgency = "low"
        name = self.getSourcePackageName(src.package)[0]

        SourcePackageRelease(sourcepackagename=name.id,
                             version=src.version,
                             maintainer=maintid,
                             dateuploaded=src.date_uploaded,
                             builddepends=src.build_depends,
                             builddependsindep=src.build_depends_indep,
                             architecturehintlist=src.architecture,
                             component=componentID,
                             creator=maintid,
                             urgency=priomap[src.urgency],
                             changelog=changelog,
                             dsc=dsc,
                             dscsigningkey=key,
                             section=sectionID,
                             manifest=None,
                             uploaddistrorelease=self.distro.id)

    def publishSourcePackage(self, src):
        release = self.getSourcePackageRelease(src.package, src.version)[0].id
        componentID = self.getComponentByName(src.component).id
        sectionID = self.getSectionByName(src.section).id

        # XXX dsilvers 20050415: This needs to be changed eventually because
        # we want gina's published records to be handled by Lucille's
        # publishing code. I.E. the publishing record should come in as
        # PENDING and that's that.
        # Also we should not be adding publishing records if the source was
        # already published in the distrorelease but that comes for free with
        # the checks done earlier I hope.

        SourcePackagePublishingHistory(
            distrorelease=self.distrorelease.id,
            sourcepackagerelease=release,
            status=PackagePublishingStatus.PUBLISHED,
            component=componentID,
            section=sectionID,
            datecreated=nowUTC,
            datepublished=nowUTC
            )

    def createFakeSourcePackageRelease(self, release, src):
        maintid = self.getPeople(*release["parsed_maintainer"])[0]
        # XXX these are hardcoded to the current package's value, which is not
        # really the truth
        componentID = self.getComponentByName(src.component).id
        sectionID = self.getSectionByName(src.section).id
        name = self.getSourcePackageName(src.package)[0]
        changelog=self.ensure_string_format(release["changes"])
        
        SourcePackageRelease(sourcepackagename=name.id,
                             version=release["version"],
                             dateuploaded=release["parsed_date"],
                             component=componentID,
                             creator=maintid,
                             maintainer=maintid,
                             urgency=priomap[release["urgency"]],
                             changelog=changelog,
                             section=sectionID,
                             builddepends=None,
                             builddependsindep=None,
                             architecturehintlist=None,
                             dsc=None,
                             dscsigningkey=None,
                             manifest=None,
                             uploaddistrorelease=self.distro.id)

    #
    # Build
    #
    #FIXME: DOn't use until we have the DB modification
    def getBuild(self, name, version, arch):
        build_id = self.getBinaryPackage(name, version, arch)
        return Build.get(build_id[0])

    def getBuildBySourcePackage(self, srcid):
        return Build.selectBy(sourcepackagereleaseID=srcid,
                              processorID=self.processor.id)[0]

    def createBuild(self, bin):
        print ("\t() hunting for spr with %s at %s"
               % (bin.source,bin.source_version))
        
        srcpkg = self.getSourcePackageRelease(bin.source, bin.source_version)
        if not srcpkg:
            # try handling crap like lamont's world-famous
            # debian-installer 20040801ubuntu16.0.20040928
            bin.source_version = re.sub("\.\d+\.\d+$", "", bin.source_version)

            print "\t() trying again with %s at %s" \
                                % (bin.source,bin.source_version)
            
            srcpkg = self.getSourcePackageRelease(bin.source,
                                                  bin.source_version)
            if not srcpkg:
                sentinel = object()
                if getattr(bin, "sourcepackageref", sentinel) != sentinel:
                    print "\t() last ditch effort via sourcepackageref..."
                    srcpkg = self.getSourcePackageRelease(
                        bin.sourcepackageref.package,
                        bin.sourcepackageref.version)

            if not srcpkg:
                print "\t** FMO courtesy of TROUP & TROUT inc. on %s (%s)" \
                    % (bin.source, bin.source_version)
                return

        srcpkg = srcpkg[0]

        if bin.gpg_signing_key_owner:
            key = self.getGPGKey(bin.gpg_signing_key, 
                                 *bin.gpg_signing_key_owner)
        else:
            key = None

        build = Build.selectBy(sourcepackagereleaseID=srcpkg.id,
                               processorID=self.processor.id)

        if build.count():
            return build[0]

        # Nothing to do if we fail we insert...
        print "\tUnable to retrieve build for %d; making new one..." % srcpkg.id

        build = Build(processor=self.processor.id,
                      distroarchrelease=self.distroarchrelease.id,
                      buildstate=BuildStatus.FULLYBUILT, 
                      gpgsigningkey=key,
                      sourcepackagerelease=srcpkg.id,
                      buildduration=None,
                      buildlog=None,
                      builder=None,
                      changes=None,
                      datebuilt=None)
        
        return build
    
    #
    # BinaryPackageName
    #
    def getBinaryPackageName(self, name):
        return BinaryPackageName.selectBy(name=name)

    def createBinaryPackageName(self, name):
        name = self.ensure_string_format(name)
        return BinaryPackageName(name=name)
       
    def createBinaryPackageFile(self, binpkg, alias):
        bp = self.getBinaryPackage(binpkg.package,
                                   binpkg.version,
                                   binpkg.architecture)

        # BIG XXX: Daniel Debonzi 20050223
        # If commit is not performed here
        # the database says that libraryfilealias.id=alias
        # is not on db, because it was included by librarian
        # and somehow the initZopeless db connection can't "see"
        # this db modification.
        self.commit()

        if self.dry_run:
            # Data was not commited and due to the BIG XXX above
            # create SourcePackageReleaseFile will fail so just
            # skip it
            return
        BinaryPackageFile(binarypackage=bp[0].id,
                          libraryfile=alias,
                          filetype=self.getFileType(binpkg.filename))
        
    #
    # BinaryPackage
    #
    def getBinaryPackage(self, name, version, architecture):
        #print "Looking for %s %s for %s" % (name,version,architecture)
        bin = self.getBinaryPackageName(name)
        if not bin.count():
            print "Failed to find the binarypackagename for %s" % (name)
            return None
        bin = bin[0]
        if architecture == "all":
            binpkg = BinaryPackage.selectBy(binarypackagenameID=bin.id,
                                            version=version)
            if not binpkg.count():
                return None
            return binpkg
        #else:
        clauseTables=("BinaryPackage","Build",)
        query = ("BinaryPackage.binarypackagename=%s AND "
                 "BinaryPackage.version=%s AND "
                 "Build.Processor=%s AND "
                 "Build.id = BinaryPackage.build"
                 % (bin.id, quote(version), self.processor.id)
                 )

        binpkg = BinaryPackage.select(query, clauseTables=clauseTables)
        if not binpkg.count():
            return None
        return binpkg
    
    def createBinaryPackage(self, bin):
        bin_name = self.getBinaryPackageName(bin.package)

        if not bin_name.count():
            bin_name = self.createBinaryPackageName(bin.package)
        else:
            bin_name = bin_name[0]
        
        build = self.createBuild(bin)
        if not build:
            # LA VARZEA
            return
               
        description = self.ensure_string_format(bin.description)
        summary = description.split("\n")[0]
        if summary[-1] != '.':
            summary = summary + '.'
        licence = self.ensure_string_format(bin.licence)
        componentID = self.getComponentByName(bin.component).id
        sectionID = self.getSectionByName(bin.section).id

        data = {
            "binarypackagename":    bin_name.id,
            "component":            componentID,
            "version":              bin.version,
            "summary":              summary,
            "description":          description,
            "build":                build.id,
            "binpackageformat":     self.getBinaryPackageFormat(bin.filename),
            "section":              sectionID,
            "priority":             prioritymap[bin.priority],
            "shlibdeps":            bin.shlibs,
            "depends":              bin.depends,
            "suggests":             bin.suggests,
            "recommends":           bin.recommends,
            "conflicts":            bin.conflicts,
            "replaces":             bin.replaces,
            "provides":             bin.provides,
            "essential":            False,
            "installedsize":        bin.installed_size,
            "licence":              licence,
            "architecturespecific": True,
            "copyright": None
            }
        
        if bin.architecture == "all":
            data["architecturespecific"] = False

        BinaryPackage(**data)

    def publishBinaryPackage(self, bin):
        ## Just publish the binary as Warty DistroRelease
        componentID = self.getComponentByName(bin.component).id
        sectionID = self.getSectionByName(bin.section).id
        #print "%s %s %s" % (bin.package, bin.version, bin.architecture)
        binpkg = self.getBinaryPackage(bin.package, bin.version, bin.architecture)
        if not binpkg:
            print '\t*Failed to Publish ', bin.package
            return
        #print "%s" % bin_id
        data = {
           "binarypackage":     binpkg[0].id, 
           "component":         componentID, 
           "section":           sectionID,
           "priority":          prioritymap[bin.priority],
           "distroarchrelease": self.distroarchrelease.id,
           # XXX dsilvers 2004-11-01: This *ought* to be pending.
           # Once the publisher is ready such that Gina always writes into
           # a distrorelease where publishing is occuring, we can change
           # this to PENDING so that publishing happens properly.
           # Perhaps we should offer a commandline option to choose?
           "status":            PackagePublishingStatus.PUBLISHED,
           # Irritating needed defaults for the sqlobject guff...
           "datecreated":       nowUTC,
           "datepublished":     nowUTC,
           "datesuperseded":    None,
           "supersededby":      None,
           "datemadepending":   None,
           "dateremoved":       None,
        }

        PackagePublishingHistory(**data)

    def emptyPublishing(self, source=False, source_only=False):
        """Empty the publishing tables for this distroarchrelease.

        This is a pretty heavy handed process because it destroys source
        package publishing history for the given distrorelease which is
        a bit sucky. Eventually we won't be using this because we'll use
        Lucille's domination code and publisher to handle it all.
        """

        if source:
            spps = SourcePackagePublishingHistory.selectBy(
                distroreleaseID=self.distrorelease.id
                )

            for spp in spps:
                spp.destroySelf()

        # Source Only mode. Does not mess with binary publishing
        if source_only:
            return

        pps = PackagePublishingHistory.selectBy(
            distroarchreleaseID=self.distroarchrelease.id
            )

        for pp in pps:
            pp.destroySelf()

    #
    # People
    #
    def getPeople(self, name, email):        
        name = self.ensure_string_format(name)
        email = self.ensure_string_format(email).lower()
        self.ensurePerson(name, email)
        return self.getPersonByEmail(email)

    def getPersonByEmail(self, email):
        query=("email=%s AND "
               "Person.id=emailaddress.person"
               %quote(email)
               )
        clauseTables=("Person", "EmailAddress",)

        return Person.select(query, clauseTables=clauseTables)
    
    def getPersonByName(self, name):
        return Person.selectBy(name=name)
    
    def getPersonByDisplayName(self, displayname):
        return Person.selectBy(displayname=displaybname)

    def createPeople(self, name, email):
        print "\tCreating Person %s <%s>" % (name, email)
        name = self.ensure_string_format(name)

        items = name.split()

        if len(items) == 1:
            givenname = name
            familyname = ""
        elif not items:
            # No name, just an email
            print "\t\tGuessing name is stem of email %r" % email
            givenname = email.split("@")[0]
            familyname = ""
        else:
            givenname = items[0]
            familyname = " ".join(items[1:])

        data = {
            "displayname":  name,
            "givenname":    givenname,
            "familyname":   familyname,
            "name":         generate_nick(email),
        }

        person = Person(**data)

        self.createEmail(person.id, email)

    def createEmail(self, pid, email):
        data = {
            "email":    email,
            "person":   pid,
            "status":   EmailAddressStatus.NEW
        }

        EmailAddress(**data)

    def ensurePerson(self, name, email):
        if self.getPersonByEmail(email).count():
            return
        # No person found and we can't rely on displayname to find the right
        # person. Have to create a new person.
        self.createPeople(name, email)
    
    def getGPGKey(self, key, name, email, id, armor, is_revoked,
                  algorithm, keysize):
        self.ensurePerson(name, email)
        person = self.getPersonByEmail(email)[0]

        ret = GPGKey.selectBy(keyid=id)

        if not ret.count():
            ret = self.createGPGKey(person, key, id, armor, is_revoked,
                                    algorithm, keysize)
            return ret
        
        return ret[0]

    def createGPGKey(self, person, key, id, armor, is_revoked, algorithm,
                     keysize):
        # person      | integer | not null
        # keyid       | text    | not null
        # fingerprint | text    | not null
        # pubkey      | text    | not null
        # revoked     | boolean | not null
        # algorith    | integer | not null
        # keysize     | integer | not null
        algorithm = GPGKeyAlgorithm.items[algorithm]
        data = {
            "owner":       person,
            "keyid":        id,
            "fingerprint":  key,
            "pubkey":       armor,
            "revoked":      is_revoked and "True" or "False",
            "algorithm":    algorithm,
            "keysize":      keysize,
        }

        gpgkey = GPGKey(**data)
        
        return gpgkey
    #
    # Distro/Release
    #
    def getDistro(self, distro):
        # XXX
        pass

    def getRelease(self, distro, release):
        # XXX
        pass

    def getComponentByName(self, component):
        if component in self.compcache:
            return self.compcache[component]

        ret = Component.selectBy(name=component)

        if not ret.count():
            raise ValueError, "Component %s not found" % component

        self.compcache[component] = ret[0]
        print "\t+++ Component %s is %s" % \
              (component, self.compcache[component].id)

        return ret[0]

    def getSectionByName(self, section):
        if '/' in section:
            section = section[section.find('/')+1:]
        if section in self.sectcache:
            return self.sectcache[section]

        ret = Section.selectBy(name=section)

        if not ret.count():
            raise ValueError, "Section %s not found" % section

        self.sectcache[section] = ret[0]
        print "\t+++ Section %s is %s" % (section, self.sectcache[section].id)
        return ret[0]

    def addSection(self, section):
        if '/' in section:
            section = section[section.find('/')+1:]
        try:
            self.getSectionByName(section)
        except:
            print "No good, need to add it"
            Section(name=section)

class SPNamesImporter:
    def __init__(self, srcmap, dryrun):
        self.ztm = initZopeless()
        self.srcmap = srcmap
        self.dryrun = dryrun

    def run(self):
        counter = 0
        for k, src in self.srcmap.items():
            print '\t --- Ensuring %s'%src.package
            SourcePackageName.ensure(src.package)
            
            if counter > 10:
                self.commit()
                counter = 0
            counter += 1
        self.commit()

    def commit(self):
        print ' * Commiting SourcePackageNames'
        if not self.dryrun:
            self.ztm.commit()

class LaunchpadTester:
    """Class to test the launchpad db consistance"""

    def __init__(self, srcmap={}, binmap={}):
        self.ztm = initZopeless()
        self.srcmap = srcmap
        self.binmap = binmap

    def countBinaryPackages(self):
        return BinaryPackage.select().count()
    
    def countBinaryBuilds(self):
        bins = BinaryPackage.select()
        builds = []

        for bin in bins:
            builds.append(bin.build)

        return len(Set(builds))

    def countBuilds(self):
        return Build.select().count()

    def countBuildSourceReleases(self):
        builds = Build.select()
        sprs = []

        for build in builds:
            sprs.append(build.sourcepackagerelease)

        return len(Set(sprs))

    def countSourceReleases(self):
        return SourcePackageRelease.select().count()

    def run(self):
        print 'Start to check DB'

        print ' @Counting BinaryPackages'
        bin = self.countBinaryPackages()
        print '\t ***Found %d BinaryPackages'%bin

        print ' @Counting BinaryPackages builds'
        bpbuild = self.countBinaryBuilds()
        print '\t***Found %d Builds in BinaryPackage rows'%bpbuild
        
        print ' @Counting Builds'
        build = self.countBuilds()
        print '\t***Found %d Builds'%build
        
        print ' @Counting Builds SourcePackageReleases'
        bspr = self.countBuildSourceReleases()
        print '\t***Found %d SourcePackageRelease in Build rows'%bspr
        
        print ' @Counting SourcePackageReleases'
        spr = self.countSourceReleases()
        print '\t***Found %d SourcePackageReleases'%spr

        print ' @Checking SourcePackageRelease against the Archive Source File'
        src_errors = 0
        src_notfound = 0
        for k, src in self.srcmap.items():
            try:
                clauseTables = ('SourcePackageName',)
                query = ('SourcePackageRelease.sourcepackagename = '
                         'sourcepackagename.id AND '
                         'SourcePackageName.name = %s AND '
                         'SourcePackageRelease.version = %s'
                         %(quote(src.package), quote(src.version))
                         )

                if not SourcePackageRelease.select(\
                    query, clauseTables=clauseTables).count():
                    src_notfound += 1
                    print ('\t===SourcePackageRelease %s-%s not found'
                           %(src.package, src.version)
                           )
            except:
                print ('\t---Exception found in SourcePackage %s-%s'
                       %(src.package, src.version)
                       )
                src_errors += 1
        print '\t***%d exceptions found checking SourcePackages'%src_errors
        print '\t***%d SourcePackageRelease not included'%src_notfound


        

        
