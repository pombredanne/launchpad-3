# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Package information classes.

This classes are responsable for fetch and hold the information inside
the sources and binarypackages.
"""

__all__ = ['AbstractPackageData', 'SourcePackageData', 'BinaryPackageData']

import re, os, tempfile, shutil, sys, time, rfc822

from canonical.launchpad.scripts.gina.changelog import parse_changelog

from canonical.database.constants import nowUTC
from canonical.lp.dbschema import GPGKeyAlgorithm

from canonical.launchpad.scripts import log
from canonical.launchpad.scripts.gina import call

def stripseq(seq):
    return [s.strip() for s in seq]

GPGALGOS = {}
for item in GPGKeyAlgorithm.items:
    GPGALGOS[item.value] = item.name

def get_person_by_key(self, keyrings, key):
    if key and key not in ("NOSIG", "None", "none"):
        command = ("gpg --no-options --no-default-keyring "
                   "--with-colons --fingerprint %s %s" % (key, keyrings))
        h = os.popen(command, "r")
        for line in h.readlines():
            if line.startswith("pub"):
                break
        else:
            log.warn("Broke parsing gpg output for %s" % key)
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

class AbstractPackageData:
    def parse_person(self, val):
        # Some emails has ',' like "Adam C. Powell, IV <hazelsct@debian.org>"
        # and rfc822.parseaddr seems to do not handle this properly
        val = val.replace(',','')
        return rfc822.parseaddr(val)

    def process_package(self, kdb, package_root, keyrings):
        """ Process the package using the archive

        This method, using the archive, try to set properly some required
        attributes with package information that we need to fill the lauchpad
        db package tables.
        """
        tempdir = tempfile.mkdtemp()
        try:
            self.do_package(tempdir, package_root)
        except:
            log.exception("Evil things happened, check out %s" % tempdir)
            return False
        shutil.rmtree(tempdir)
        if not self.do_katie(kdb, keyrings):
            return False
        self.is_processed = True
        return True

    def do_package(self, dir, package_root):
        raise NotImplementedError
    
    def do_katie(self, kdb, keyrings):
        raise NotImplementedError


class MissingRequiredArguments(ValueError):
    """Missing Required Arguments Exception.

    Raised if we attempted to construct a SourcePackageData without
    all the required arguments. This is because we are stuck (for now)
    passing arguments using **args as some of the argument names are not
    valid Python identifiers
    """
    pass


class SourcePackageData(AbstractPackageData):
    """This Class holds important data to a given sourcepackagerelease."""

    # These attributes must have been set by the end of the __init__ method.
    # They are passed in as keyword arguments. If any are not set, a
    # MissingRequiredArguments exception is raised.
    _required = [
        'package', 'binaries', 'version', 'section', 'maintainer', #'priority',
        'build_depends', 'build_depends_indep', 'architecture',
        'standards_version', 'directory', 'files', 'licence']

    build_depends = ""
    build_depends_indep = ""
    standards_version = ""
    description = ""
    licence = ""

    is_processed = False
    is_created = False

    def __init__(self, kdb, **args):
        sentinel = object()
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
        if getattr(self, 'section', sentinel) is sentinel:
            log.info("Source package %s lacks a section, looking it up..." %
                    self.package)
            if not kdb:
                self._setDefaults()
                return
            self.section = kdb.getSourceSection(self.package)
            if '/' in self.section:
                try:
                    self.component, self.section = self.section.split("/")
                except ValueError:
                    self._setDefaults()
                    return
            self._setDefaults()

        missing = [attr for attr in self._required if not hasattr(self, attr)]
        if missing:
            raise MissingRequiredArguments(missing)
                
    def _setDefaults(self):
        log.info("Damn, I had to assume 'misc'")
        self.section = 'misc'

    def do_package(self, dir, package_root):
        """Get the Changelog and licence from the package on archive."""
        self.package_root = package_root
        cwd = os.getcwd()

        version = re.sub("^\d+:", "", self.version)
        filename = "%s_%s.dsc" % (self.package, version)
        fullpath = os.path.join(package_root, self.directory, filename)
        self.dsc = open(fullpath).read().strip()

        os.chdir(dir)
        call("dpkg-source -sn -x %s" % fullpath)
        
        version = re.sub("-[^-]+$", "", version)
        filename = "%s-%s" % (self.package, version)
        fullpath = os.path.join(filename, "debian", "changelog")

        if os.path.exists(fullpath):
            changelog = open(fullpath)
            self.do_changelog(changelog)
            changelog.close()
        else:
            self.changelog = ''

        fullpath = os.path.join(filename, "debian", "copyright")
        if os.path.exists(fullpath):
            self.licence = open(fullpath).read().strip()
        else:
            log.info("WML courtesy of Missing Copyrights Ltd. in %s" % filename)

        os.chdir(cwd)

    def do_changelog(self, changelog):
        line = ""
        while not line:
            line = changelog.readline().strip()
        self.urgency = line.split("urgency=")[1].strip().lower()
        changelog.seek(0)
        self.changelog = parse_changelog(changelog)

    def do_katie(self, kdb, keyrings):
        if not kdb:
            self.date_uploaded = nowUTC
            return True
            
        data = kdb.getSourcePackageRelease(self.package, self.version)
        if not data:
            self.date_uploaded = nowUTC
            return True

        assert len(data) == 1
        data = data[0]
        # self.date_uploaded = data["install_date"]
        # XXX: Daniel Debonzi 20050621
        # launchpad does not accept to include date like it
        self.date_uploaded = nowUTC

        # XXX: Daniel Debonzi 2005-05-18
        # Check it when start using cprov gpghandler
##         self.dsc_signing_key = data["fingerprint"]
##         self.dsc_signing_key_owner = \
##             get_person_by_key(keyrings, self.dsc_signing_key)
        return True

#
#
#

class BinaryPackageData(AbstractPackageData):
    """This Class holds important data to a given binarypackage."""

    # These attributes must have been set by the end of the __init__ method.
    # They are passed in as keyword arguments. If any are not set, a
    # MissingRequiredArguments exception is raised.
    _required = [
        'package', 'priority', 'section', 'installed_size', 'maintainer',
        'architecture', 'essential', 'source', 'version', 'replaces',
        'provides', 'depends', 'pre_depends', 'enhances', 'suggests',
        'conflicts', 'filename', 'size', 'md5sum', 'description' ]
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
            if k == "Maintainer":
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
        if not hasattr(self, 'section'):
            log.info("Binary package %s lacks a section... assuming misc" %
                     self.package)
            self.section = 'misc'


        missing = [attr for attr in self._required if not hasattr(self, attr)]
        if missing:
            raise MissingRequiredArguments(missing)
 
    def do_package(self, dir, package_root):
        """
        Grab the shared library info from the package on archive if exists.
        
        """
        self.package_root = package_root
        cwd = os.getcwd()
        fullpath = os.path.join(package_root, self.filename)
        os.chdir(dir)

        if not os.path.exists(fullpath):
            raise ValueError, '%s not found'%fullpath

        call("dpkg -e %s" % fullpath)
        shlibfile = os.path.join("DEBIAN", "shlibs")
        if os.path.exists(shlibfile):
            log.debug("Grabbing shared library info from %s" % (
                os.path.basename(fullpath)
                ))
            self.shlibs = open(shlibfile).read().strip()
        os.chdir(cwd)
    
    def do_katie(self, kdb, keyrings):
        if not kdb:
            return True

        # XXX: Daniel Debonzi 2005-05-18
        # Check it when start using cprov gpghandler
        return True
        data = kdb.getBinaryPackageRelease(self.package, self.version,
                                           self.architecture)
        if not data:
            return False
        #assert len(data) >= 1
        if len(data) == 0:
            raise Exception, "assert len(data) >= 1"
        data = data[0]
        self.gpg_signing_key = data["fingerprint"]
        log.debug(self.gpg_signing_key)
        self.gpg_signing_key_owner = \
            get_person_by_key(keyrings, self.gpg_signing_key)
        return True
