import re, os, tempfile, shutil, sys

from library import getLibraryAlias

# From zless /usr/share/doc/gnupg/DETAILS.gz 
GPGALGOS = {
    1 : "R",  # RSA
    16: "g", # ElGamal
    17: "D", # DSA
    20: "G", # ElGamal, compromised:
             #     http://www.w4kwh.org/privacy/gnupgelgamal.html
}

def stripseq(seq):
    return [s.strip() for s in seq]

class AbstractPackageRelease:
    def parse_person(self, val):
        name, email = val.split("<", 2)
        email = email.split(">")[0].lower()
        return (name.strip(), email.strip())

    def process_package(self, kdb, package_root, keyrings):
        tempdir = tempfile.mkdtemp()
        try:
            self.do_package(tempdir, package_root)
        except:
            print "\t** Evil things happened, check out %s" % tempdir
            raise
            # XXX we want to run this when in production
            # finally:
            # shutil.rmtree(tempdir)
        shutil.rmtree(tempdir)
        self.do_katie(kdb, keyrings)
        self.is_processed = True

    def get_person_by_key(self, keyrings, key):
        if key and key not in ("NOSIG", "None", "none"):
            h = os.popen("gpg --no-options --no-default-keyring %s "
                         "--with-colons --fingerprint %s" % (keyrings, key), 
                         "r")
            for line in h.readlines():
                if line.startswith("pub"):
                    break
            else:
                print "\t** Broke parsing gpg output for %s" % key
                return None

            line = line.split(":")
            algo = int(line[3])
            if GPGALGOS.has_key(algo):
                algochar = GPGALGOS[algo]
            else:
                algochar = "?" % algo
## STRIPED GPGID Support by cprov 20041004
##          id = line[2] + algochar + "/" + line[4][-8:]
            id = line[4][-8:]
            algorithm = algo
            keysize = line[2]
##                
            user, rest = line[9].split("<", 1)
            email = rest.split(">")[0].lower()
            if line[1] == "-":
                is_revoked = 0
            else:
                is_revoked = 1

            h = os.popen("gpg --export --no-default-keyring %s "
                         "--armor %s" % (keyrings, key), "r")
            armor = h.read().strip()

            return (user, email, id, armor, is_revoked, algorithm, keysize)
        else:
            return None

    def do_package(self, dir, package_root):
        raise NotImplementedError
    
    def do_katie(self, kdb, keyrings):
        raise NotImplementedError

class SourcePackageRelease(AbstractPackageRelease):
    # package
    # binaries
    # version
    # priority
    # section
    # maintainer
    # build-depends
    # build-depends-indep
    # architecture
    # standards-version
    # format
    # directory
    # files
    # uploaders
    # licence
    build_depends = ""
    build_depends_indep = ""
    standards_version = ""
    #
    description = ""
    licence = ""
    #
    is_processed = False
    is_created = False
    src_fields = [
        'Package',  # source package name (aalib)
        'Binary',   # list of binary package releases 
                    # (aalib1-dev, aalib1, aalib-bin)
        'Version',  # release (1.4p5-20)
        'Priority', # string (optional)
        'Section',  # string (libs)
        'Maintainer',        # maintainer name (Joey Hess <joeyh@debian.org>)
        'Build-Depends',     # list of package and version constraints
                             # ( debhelper (>= 4.1.1), slang1-dev, libx11-dev...)
        'Architecture',      # any
        'Standards-Version', # wtf? 3.5.10.0
        'Format',            # wtf? 1.0
        'Directory',         # where it lives (pool/main/a/aalib)
        'Files',             # list of md5 size filename
                             # 95df5f75e028a3dd2ae253bc975217c3 636 
                             #      adduser_3.57.dsc
                             # 194b435b76b094aa130743a7056b3c77 95403
                             #      adduser_3.57.tar.gz
        'Uploaders'          # list of maintainer names 
                             # (Roland Bauerschmidt <rb@debian.org>, 
                             #  Marc Haber <mh+debian-packages@zugschlus.de>
    ]
    def __init__(self, **args):
        for k, v in args.items():
            if k == 'Binary':
                self.binaries = stripseq(v.split(","))
            elif k == 'Section':
                if "/" in v:
                    self.component, self.section = v.split("/")
                else:
                    self.component, self.section  = "main", v
            elif k == 'Maintainer':
                self.maintainer = self.parse_person(v)
            elif k == 'Files':
                self.files = []
                files = v.split("\n")
                for f in files:
                    self.files.append(stripseq(f.split(" ")))
            elif k == 'Uploaders':
                people = stripseq(v.split(","))
                self.uploaders = [person.split(" ", 1) for person in people]
            else:
                setattr(self, k.lower().replace("-", "_"), v)

    def do_package(self, dir, package_root):
        self.package_root = package_root
        cwd = os.getcwd()

        version = re.sub("^\d+:", "", self.version) 
        filename = "%s_%s.dsc" % (self.package, version) 
        fullpath = os.path.join(package_root, self.directory, filename)
        self.dsc = open(fullpath).read().strip()

        os.chdir(dir)
        sys.stderr.write("\t")
        os.system("dpkg-source -sn -x %s" % fullpath)
        
        version = re.sub("-[^-]+$", "", version)
        filename = "%s-%s" % (self.package, version) 
        fullpath = os.path.join(filename, "debian", "changelog")
        changelog = open(fullpath)
        self.do_changelog(changelog)
        changelog.close()

        fullpath = os.path.join(filename, "debian", "copyright")
        if os.path.exists(fullpath):
            self.licence = open(fullpath).read().strip()
        else:
            # XXX the right thing is to unpack the binary tarball and
            # look at /usr/share/doc/PACKAGENAME/copyright
            print "\t** WML courtesy of Missing Copyrights Ltd. in %s" % filename

        os.chdir(cwd)

    def do_changelog(self, changelog):
        line = ""
        while not line:
            line = changelog.readline().strip()
        self.urgency = line.split("urgency=")[1].strip()
        changelog.seek(0)
        self.changelog = changelog.read().strip()

    def do_katie(self, kdb, keyrings):
        data = kdb.getSourcePackageRelease(self.package, self.version)
        assert len(data) == 1
        data = data[0]
        self.date_uploaded = data["install_date"]
        self.dsc_signing_key = data["fingerprint"]
        self.dsc_signing_key_owner = \
            self.get_person_by_key(keyrings, self.dsc_signing_key)

    def ensure_created(self, db):
        if not db.getSourcePackageRelease(self.package, self.version):
            print "\t$ Creating source package"
            db.createSourcePackageRelease(self)
            print "\t$ Adding files to librarian"
            files={}
            for f in self.files:
                fname = f[-1]
                print "\t\t+ %s/%s" % (self.directory, fname);
                alias = getLibraryAlias( "%s/%s" % (self.package_root, self.directory), fname )
                if alias is not None:
                    print "\t\t\t= %s" % alias
                    db.createSourcePackageReleaseFile(self, fname, alias)
            

class BinaryPackageRelease(AbstractPackageRelease):
    # package
    # priority
    # section
    # installed_size
    # maintainer
    # architecture
    # essential
    # source
    # version
    # replaces
    # provides
    # depends
    # pre_depends
    # enhances
    # suggests
    # conflicts
    # filename
    # size
    # md5sum
    # description
    # bugs
    # origin
    # task
    source = None # Some packages have Source, some don't -- the ones
                  # that don't have the same package name
    depends = ""
    shlibs = ""
    pre_depends = ""
    recommends = ""
    suggests = ""
    enhances = ""
    conflicts = ""
    replaces = ""
    provides = ""
    essential = ""
    #
    is_processed = False
    is_created = False
    def __init__(self, **args):
        for k, v in args.items():
            if k == " Maintainer":
                self.maintainer = self.parse_person(v)
            else:
                setattr(self, k.lower().replace("-", "_"), v)
        self.source_version = self.version
        if not self.source:
            self.source = self.package
            self.source_version = self.version
        else:
            # handle cases like "Source: myspell (1:3.0+pre3.1-6)"
            src_bits = self.source.split(" ", 2)
            self.source = src_bits[0]
            if len(src_bits) > 1:
                self.source_version = src_bits[1][1:-1]

    def do_package(self, dir, package_root):
        self.package_root = package_root
        cwd = os.getcwd()
        fullpath = os.path.join(package_root, self.filename)
        os.chdir(dir)
        os.system("dpkg -e %s" % fullpath)
        shlibfile = os.path.join("DEBIAN", "shlibs")
        if os.path.exists(shlibfile):
            print "\tGrabbing shared library info from %s" % \
                os.path.basename(fullpath)
            self.shlibs = open(shlibfile).read().strip()
        os.chdir(cwd)
    
    def do_katie(self, kdb, keyrings):
        data = kdb.getBinaryPackageRelease(self.package, self.version,
                                           self.architecture)
        assert len(data) == 1
        data = data[0]
        self.gpg_signing_key = data["fingerprint"]
        self.gpg_signing_key_owner = \
            self.get_person_by_key(keyrings, self.gpg_signing_key)

    def ensure_created(self, db):
        if not self.is_created(db):
            print "\t$ Creating binary package"
            db.createBinaryPackage(self)
            if not self.is_created(db):
                return; # FMO TROUP etc.
            fname = self.filename[self.filename.rfind("/")+1:]
            fdir = self.filename[:self.filename.rfind("/")]
            print "\t\t+ %s" % self.filename
            alias = getLibraryAlias( "%s/%s" % (self.package_root, fdir), fname)
            if alias is not None:
                print "\t\t\t= %s" % alias
                db.createBinaryPackageFile( self, alias )

    def is_created(self, db):
        return db.getBinaryPackage(self.package, self.version)

