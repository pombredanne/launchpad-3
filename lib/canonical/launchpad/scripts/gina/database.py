import re
from pyPgSQL import PgSQL

# Disable cursors for now (can cause issues sometimes it seems)
PgSQL.noPostgresCursor = 1

from nickname import generate_nick

class SQLThing:
    def __init__(self, dbname):
        self.dbname = dbname
        self.db = PgSQL.connect(database=self.dbname)

    def commit(self):
        return self.db.commit()
    
    def close(self):
        return self.db.close()

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

    def __init__(self, bar, suite):
        SQLThing.__init__(self,bar)
        self.suite = suite

    def getSourcePackageRelease(self, name, version):
        print "\t\t* Hunting for spr (%s,%s)" % (name,version)
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
"required": 50,
"important": 40,
"standard": 30,
"optional": 20,
"extra":10
}

class Launchpad(SQLThing):
    def __init__(self, bar, dr, proc):
        SQLThing.__init__(self,bar)
        self.compcache = {}
        self.sectcache = {}
        try:
            ddr = self._query_single("""
            SELECT id,distribution FROM distrorelease WHERE name=%s;
            """, (dr,))
            self.distrorelease = ddr[0]
            self.distro = ddr[1]
        except:
            raise ValueError, "Error finding distrorelease for %s" % dr
        try:
            dar = self._query_single("""
            SELECT processorfamily, id FROM distroarchrelease WHERE
            distrorelease = %s AND architecturetag = %s
            """, (self.distrorelease,proc))
            self.processor = dar[0]
            self.distroarchrelease = dar[1]
        except:
            raise ValueError, "Error finding distroarchrelease for %s/%s" % (dr,proc)
        try:
            self.processor = self._query_single("""
            SELECT id FROM processor WHERE family = %s
            """, (self.processor))[0]
        except:
            raise ValueError, "Unable to find a processor from the processor family chosen from %s/%s" % (dr, proc)
        print "INFO: Chosen D(%d) DR(%d), PROC(%d), DAR(%d) from SUITE(%s), ARCH(%s)" % (self.distro, self.distrorelease, self.processor, self.distroarchrelease, dr, proc)
        # Attempt to populate self._debiandistro
        self._debiandistro = self._query_single("""
        SELECT id FROM distribution WHERE name = 'debian'
        """)[0]
        print "INFO: Found Debian GNU/Linux at %d" % (self._debiandistro)
        
    #
    # SourcePackageName
    #
    def ensureSourcePackageName(self, name):
        if self.getSourcePackageName(name):
            return
        name = self.ensure_string_format(name)
        self._insert("sourcepackagename", {"name": name})

    def getSourcePackageName(self, name):
        return self._query_single("""SELECT id FROM sourcepackagename
                                     WHERE name = %s;""", (name,))

    #
    # SourcePackage
    #
    def ensureSourcePackage(self, src):
        if self.getSourcePackage(src.package):
            return

        self.ensureSourcePackageName(src.package)
        name = self.getSourcePackageName(src.package)

        people = self.getPeople(*src.maintainer)[0]
    
        description = self.ensure_string_format(src.description)
        short_desc = description.split("\n")[0]

        data = {
            "maintainer":           people,
            "shortdesc" :           short_desc,
            "distro":               self.distro,
            "description":          description,
            "sourcepackagename":    name[0],
            ## XXX: (srcpackageformat+hardcoded) cprov 20041025
            ## Sourcepackeformat hardcoded for .deb or whatever ...
            "srcpackageformat":     1 
        }
        self._insert("sourcepackage", data)
        data["distro"] = self._debiandistro
        self._insert("sourcepackage", data)

        ubuntupackage = self.getSourcePackage(src.package)
        debianpackage = self.getSourcePackage(src.package, self._debiandistro)
        
        data = {
            "subject": ubuntupackage,
            "label": 4, ## DERIVESFROM
            "object": debianpackage
            }
        self._insert("sourcepackagerelationship", data)

    def getSourcePackage(self, name_name, distro = None):
        # Suckage because Python won't analyse default values in the context
        # of the call. Python idiom is nasty.
        if distro is None:
            distro = self.distro
        self.ensureSourcePackageName(name_name)
        name = self.getSourcePackageName(name_name)
        # FIXME: SELECT * is crap !!!
        return self._query_single("""SELECT * FROM sourcepackage 
                                     WHERE sourcepackagename=%s
                                       AND distro=%s""",
                                  (name[0],distro))
        
    #
    # SourcePackageRelease
    #
    def getSourcePackageRelease(self, name, version):
        src_id = self.getSourcePackage(name)
        if not src_id:
            return None
        #FIXME: SELECT * is crap !!!
        return self._query("""SELECT id FROM sourcepackagerelease
                              WHERE sourcepackage = %s 
                              AND version = %s;""", (src_id[0] , version))
    def createSourcePackageReleaseFile(self, src, fname, alias):
        r = self.getSourcePackageRelease(src.package, src.version)
        if not r:
            raise ValueError, "Source not yet in database"
        data = {
        "sourcepackagerelease": r[0][0],
        "libraryfile": alias,
        "filetype": 1 # XXX: No types defined as yet?
        }

        self._insert( "sourcepackagereleasefile", data )

    def createSourcePackageRelease(self, src):
        self.ensureSourcePackage(src)

        srcpkgid = self.getSourcePackage(src.package)[0]
        maintid = self.getPeople(*src.maintainer)[0]
        if src.dsc_signing_key_owner:
            key = self.getGPGKey(src.dsc_signing_key, 
                                 *src.dsc_signing_key_owner)[0]
        else:
            key = None

        dsc = self.ensure_string_format(src.dsc)
        changelog = self.ensure_string_format(src.changelog)
        component = self.getComponentByName(src.component)[0]
        section = self.getSectionByName(src.section)[0]
        data = {
            "sourcepackage":           srcpkgid,
            "version":                 src.version,
            "dateuploaded":            src.date_uploaded,
            "builddepends":            src.build_depends,
            "builddependsindep":       src.build_depends_indep,
            "architecturehintlist":    src.architecture,
            "component":               component,
            "creator":                 maintid,
            "urgency":                 1,
            "changelog":               changelog,
            "dsc":                     dsc,
            "dscsigningkey":           key,
            "section":                 section,
        }                                                          
        self._insert("sourcepackagerelease", data)


    def publishSourcePackage(self, src):
        release = self.getSourcePackageRelease(src.package, src.version)[0]
        component = self.getComponentByName(src.component)[0]
        section = self.getSectionByName(src.section)[0]

        data = {
            "distrorelease":           self.distrorelease,
            "sourcepackagerelease":    release[0],
            # XXX dsilvers 2004-11-01: This *ought* to be pending
            "status":                  2, ## Published
            "component":               component,
            "section":                 section, ## default Section
        }
        self._insert("sourcepackagepublishing", data)

    #
    # Build
    #
    #FIXME: DOn't use until we have the DB modification
    def getBuild(self, name, version, arch):
        build_id = self.getBinaryPackage(name, version, arch)
        #FIXME: SELECT * is crap !!!
        return self._query("""SELECT * FROM build 
                              WHERE  id = %s;""", (build_id[0],))

    def getBuildBySourcePackage(self, srcid):
        return self._query("""SELECT id FROM build
                              WHERE sourcepackagerelease = %s
                                AND processor=%s""", (srcid,self.processor))[0]

    def createBuild(self, bin):
        print "\t() hunting for spr with %s at %s" % (bin.source,bin.source_version)
        srcpkg = self.getSourcePackageRelease(bin.source, bin.source_version)
        if not srcpkg:
            # try handling crap like lamont's world-famous
            # debian-installer 20040801ubuntu16.0.20040928
            bin.source_version = re.sub("\.\d+\.\d+$", "", bin.source_version)

            print "\t() trying again with %s at %s" % (bin.source,bin.source_version)
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

        if bin.gpg_signing_key_owner:
            key = self.getGPGKey(bin.gpg_signing_key, 
                                 *bin.gpg_signing_key_owner)[0]
        else:
            key = None

        try:
            buildid = self.getBuildBySourcePackage(srcpkg[0][0])
            return buildid
        except:
            # Nothing to do if we fail we insert...
            print "\tUnable to retrieve build for %d; making new one..." % srcpkg[0][0]
            pass
        
    
        data = {
            "processor":            self.processor,
            "distroarchrelease":    self.distroarchrelease,
            "buildstate":           1,
            "gpgsigningkey":        key,
            "sourcepackagerelease": srcpkg[0][0],
        }
        self._insert("build", data)

        ##FIXME: for god sake !!!!
        return self._query("""SELECT currval('build_id_seq');""")[0]

    #
    # BinaryPackageName
    #
    def getBinaryPackageName(self, name):
        return self._query("""SELECT * FROM binarypackagename 
                              WHERE  name = %s;""", (name,))

    def createBinaryPackageName(self, name):
        name = self.ensure_string_format(name)
        self._insert("binarypackagename", {"name": name})
       
    def createBinaryPackageFile(self, binpkg, alias):
        bp = self.getBinaryPackage(binpkg.package,binpkg.version,binpkg.architecture)
        #print bp
        data = {
        "binarypackage": bp[0],
        "libraryfile": alias,
        "filetype": 1, # XXX Default to DEB/UDEB unless we get a better option
        }
        self._insert("binarypackagefile", data)
        pass
    #
    # BinaryPackage
    #
    def getBinaryPackage(self, name, version, architecture):
        #print "Looking for %s %s for %s" % (name,version,architecture)
        bin_id = self.getBinaryPackageName(name)
        if not bin_id:
            print "Failed to find the binarypackagename for %s" % (name)
            return None
        if architecture == "all":
            return self._query_single("""SELECT * from binarypackage WHERE
                                         binarypackagename = %s AND
                                         version = %s""", (bin_id[0][0], version))
        #else:
        return self._query_single("""SELECT * from binarypackage, build
                                     WHERE  binarypackagename = %s AND 
                                            version = %s AND
                                            build.processor = %s AND
                                            build.id = binarypackage.build""", 
                                  (bin_id[0][0], version, self.processor))

    def createBinaryPackage(self, bin):
        if not self.getBinaryPackageName(bin.package):
            self.createBinaryPackageName(bin.package)
        
        build = self.createBuild(bin)
        if not build:
            # LA VARZEA
            return

        name = self.getBinaryPackageName(bin.package)
        if not name:
            self.createBinaryPackageName(bin.package)
            name = self.getBinaryPackageName(bin.package)

               
        description = self.ensure_string_format(bin.description)
        short_desc = description.split("\n")[0]
        licence = self.ensure_string_format(bin.licence)
        component = self.getComponentByName(bin.component)[0]
        section = self.getSectionByName(bin.section)[0]

        data = {
            "binarypackagename":    name[0][0],
            "component":            component,
            "version":              bin.version,
            "shortdesc":            short_desc,
            "description":          description,
            "build":                build[0],
            "binpackageformat":     1, # Deb
            "section":              section,
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
            "architecturespecific": True
        }
        if bin.architecture == "all":
            data["architecturespecific"] = False
        if bin.filename.endswith(".udeb"):
            data["binpackageformat"] = 2 # UDEB
        self._insert("binarypackage", data)


    def publishBinaryPackage(self, bin):
        ## Just publish the binary as Warty DistroRelease
        component = self.getComponentByName(bin.component)[0]
        section = self.getSectionByName(bin.section)[0]
        #print "%s %s %s" % (bin.package, bin.version, bin.architecture)
        bin_id = self.getBinaryPackage(bin.package, bin.version, bin.architecture)
        #print "%s" % bin_id
        data = {
           "binarypackage":     bin_id[0], 
           "component":         component, 
           "section":           section,
           "priority":          prioritymap[bin.priority],
           "distroarchrelease": self.distroarchrelease,
            # XXX dsilvers 2004-11-01: This *ought* to be pending
           "status": 2, ### Published !!!
        }
        self._insert("packagepublishing", data)

    def emptyPublishing(self, source=False):
        """Empty the publishing tables for this distroarchrelease"""
        if source:
            self._exec(
                """DELETE FROM sourcepackagepublishing
                         WHERE distrorelease = %s
                
                """ % self.distrorelease
                )
        self._exec(
            """DELETE FROM packagepublishing
            WHERE distroarchrelease = %s
            """ % self.distroarchrelease
            )

    #
    # People
    #
    def getPeople(self, name, email):        
        name = self.ensure_string_format(name)
        email = self.ensure_string_format(email)
        self.ensurePerson(name, email)
        return self.getPersonByEmail(email)

    def getPersonByEmail(self, email):
        return self._query_single("""SELECT Person.id FROM Person,emailaddress 
                                     WHERE email = %s AND 
                                           Person.id = emailaddress.person;""",
                                  (email,))
    
    def getPersonByName(self, name):
        return self._query_single("""SELECT Person.id FROM Person
                                     WHERE name = %s""", (name,))
    
    def getPersonByDisplayName(self, displayname):
        return self._query_single("""SELECT Person.id FROM Person 
                                     WHERE displayname = %s""", (displayname,))

    def createPeople(self, name, email):
        print "\tCreating Person %s <%s>" % (name, email)
        name = self.ensure_string_format(name)

        items = name.split()
        if len(items) == 1:
            givenname = name
            familyname = ""
        else:
            givenname = items[0]
            familyname = " ".join(items[1:])

        data = {
            "displayname":  name,
            "givenname":    givenname,
            "familyname":   familyname,
            "name":         generate_nick(email, self.getPersonByName),
        }
        self._insert("person", data)
        pid = self._query_single("SELECT CURRVAL('person_id_seq')")[0]
        self.createEmail(pid, email)
        
    def createEmail(self, pid, email):
        data = {
            "email":    email,
            "person":   pid,
            "status":   1, # XXX
        }
        self._insert("emailaddress", data)

    def ensurePerson(self, name, email):
        people = self.getPersonByEmail(email)
        if people:
            return people
        # XXX this check isn't exactly right -- if there are name
        # collisions, we just add addresses because there is no way to
        # validate them. Bad bad kiko.
        people = self.getPersonByDisplayName(name)
        if people:
            print "\tAdding address <%s> for %s" % (email, name)
            self.createEmail(people[0], email)
            return people
        self.createPeople(name, email)
    
    def getGPGKey(self, key, name, email, id, armor, is_revoked,
                  algorithm, keysize):
        self.ensurePerson(name, email)
        person = self.getPersonByEmail(email)[0]
        ret = self._query_single("""SELECT id FROM gpgkey
                                    WHERE  keyid = %s""", (id,))
        if not ret:
            ret = self.createGPGKey(person, key, id, armor, is_revoked,
                                    algorithm, keysize)
        return ret

    def createGPGKey(self, person, key, id, armor, is_revoked, algorithm,
                     keysize):
        # person      | integer | not null
        # keyid       | text    | not null
        # fingerprint | text    | not null
        # pubkey      | text    | not null
        # revoked     | boolean | not null
        # algorith    | integer | not null
        # keysize     | integer | not null
        data = {
            "person":       person,
            "keyid":        id,
            "fingerprint":  key,
            "pubkey":       armor,
            "revoked":      is_revoked and "True" or "False",
            "algorithm":    algorithm,
            "keysize":      keysize,
        }
        self._insert("gpgkey", data)
        return self._query_single("""SELECT id FROM gpgkey
                                     WHERE id = CURRVAL('gpgkey_id_seq')""")

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
        ret = self._query_single("""SELECT id FROM component 
                                    WHERE  name = %s""", component)
        if not ret:
            raise ValueError, "Component %s not found" % component
        self.compcache[component] = ret
        print "\t+++ Component %s is %s" % (component, self.compcache[component])
        return ret

    def getSectionByName(self, section):
        if '/' in section:
            section = section[section.find('/')+1:]
        if section in self.sectcache:
            return self.sectcache[section]
        ret = self._query_single("""SELECT id FROM section
                                    WHERE  name = %s""", section)
        if not ret:
            raise ValueError, "Section %s not found" % section
        self.sectcache[section] = ret
        print "\t+++ Section %s is %s" % (section, self.sectcache[section])
        return ret

    def addSection(self, section):
        if '/' in section:
            section = section[section.find('/')+1:]
        try:
            self.getSectionByName(section)
        except:
            print "No good, need to add it"
            self._insert( "section", { "name": section } )


