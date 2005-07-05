# Copyright 2004-2005 Canonical Ltd.
# Author: Robert Collins  <robertc@robertcollins.net>

import os
from StringIO import StringIO
import pickle
import pybaz as arch
from twisted.spread import pb

from canonical.lp.dbschema import ImportStatus, RevisionControlSystems

from canonical.launchpad.database.sourcepackage import SourcePackage

# official .job spec:
# job format
# TYPE=import
# RCS=svn|cvs
# repository=string  i.e. http://example.com/tarball-of-cvs-module.tar.bz2
#                         :pserver:user:password@anoncvs.example.com/server/cvs
# module=string
# category=NULL (use module) | string
# archivename=string
# branchfrom=NULL(use MAIN) | string
# branchto=NULL(use HEAD) | string
# archversion=NULL (0) | x[[.x]...]

def _interval_to_seconds(interval):
    try:
        return interval.days * 24 * 60 * 60 + interval.seconds
    except AttributeError:
        msg = "Failed to convert interval to seconds: %r" % (interval,)
        raise TypeError(msg)


class _JobNameMunger(object):
    # XXX ddaa 2004-10-28: This is part of a short term workaround for
    # code in cscvs which does not perform shell quoting correctly.
    # https://bugzilla.canonical.com/bugzilla/show_bug.cgi?id=2149

    def __init__(self):
        self._table = None

    def is_munged(self, char):
        import string
        return not (char in string.ascii_letters or char in string.digits
                    or char in ",-.:=@^_" or ord(char) > 127)

    def translation_table(self):
        if self._table is not None: return self._table
        table = []
        for code in range(256):
            if self.is_munged(chr(code)):
                table.append('_')
            else:
                table.append(chr(code))
        self._table = ''.join(table)
        return self._table

    def translate(self, text):
        return text.encode('utf8').translate(self.translation_table())


# XXX ddaa 2004-10-28: workaround for broken cscvs shell quoting
_job_name_munger = _JobNameMunger()


class Job:
    """I represent a single Job in the importd system. I'm not a base
    class as the cross machine serialisation issues get annoying - but
    I am passed to a jobStrategy to do the work on slaves."""

    def __cmp__(self, other):
        if other is None: return 1
        return cmp(self.__dict__, other.__dict__)

    def __init__(self):
        self.TYPE = ""
        self.RCS=""
        self.repository=""
        self.module=""
        self.category=""
        self.archivename=""
        self.branchfrom="MAIN"
        self.branchto="HEAD"
        self.archversion=0
        self.frequency=None
        self.tagging_rules=[]
        self.__jobTrigger = None

    def from_sourcepackagerelease(self, sourcepackagerelease, distrorelease):
        # we need the distrorelease as a hint for branch names etc, and
        # as a way of verifying distro-specific import policy
        # first construct a sourcepackage for this import
        sp = SourcePackage(
                sourcepackagename=sourcepackagerelease.sourcepackagename,
                distrorelease=distrorelease)
        assert sp.shouldimport, ('%s %s %s should not be imported' %
                                (distrorelease.distribution.name,
                                 distrorelease.name,
                                 sourcepackagerelease.name))
        self.name = 'pkg'
        self.name += '-' + distrorelease.distribution.name
        self.name += '-' + distrorelease.name
        self.name += '-' + sourcepackagerelease.name
        self.name += '-' + sourcepackagerelease.version
        self.sourcepackagerelease = sourcepackagerelease
        self.distrorelease = distrorelease
        self.RCS = 'package'
        self.TYPE = 'sourcerer'
        self.archivename = distrorelease.distribution.name + '-'
        self.archivename += sourcepackagerelease.name + '@arch.ubuntu.com'
        self.product_id = sp.product.id
        # XXX sabdfl 12/04/05 these are commented out until the Packaging
        # table has been fixed to support series-level granularity
        #assert sp.productseries is not None, ("Attempt to import %s %s %s "
        #        "which is not mapped to an upstream "
        #        "product series" % 
        #        (distrorelease.distribution.name,
        #         distrorelease.name,
        #         sourcepackagerelease.name))
        #self.series_id = sp.productseries.id
        #self.series_branch = sp.productseries.branch
        #assert self.series_branch is not None, ("Attempt to import %s %s %s"
        #    " which has no upstream branch" % 
        #        (distrorelease.distribution.name,
        #         distrorelease.name,
        #         sourcepackagerelease.name))
        return self

    def from_series(self, series):
        assert series.importstatus is not None, \
               'Should never import series with no importstatus'
        assert series.importstatus not in [ImportStatus.DONTSYNC,
                                           ImportStatus.STOPPED], \
               'Should never import STOPPED or DONTSYNC series.'
        if series.importstatus == ImportStatus.TESTING:
            self.TYPE = 'import'
            self.frequency = 60 # autobuild this
        elif series.importstatus in [ImportStatus.AUTOTESTED,
                                     ImportStatus.TESTFAILED,
                                     ImportStatus.PROCESSING]:
            self.TYPE = 'import'
            self.frequency=0
        elif series.importstatus == ImportStatus.SYNCING:
            self.TYPE = 'sync'
            self.frequency = _interval_to_seconds(series.syncinterval)
        else:
            raise (NotImplementedError,
                   'Unknown ImportStatus %r' % series.importstatus)

        self.tagging_rules=[]

        # XXX ddaa 2004-10-28: workaround for broken cscvs shell quoting
        name = series.product.name + '-' + series.name
        if series.product.project is not None:
            name = series.product.project.name + '-' + name
        name = _job_name_munger.translate(name)
        # XXX end
        self.name = name
        RCSNames = {RevisionControlSystems.CVS: 'cvs',
                    RevisionControlSystems.SVN: 'svn',
                    RevisionControlSystems.ARCH: 'arch',
                    RevisionControlSystems.BITKEEPER: 'bitkeeper',
                    }
        self.RCS = RCSNames[series.rcstype]

        # set the repository
        if self.RCS == 'cvs':
            if series.cvstarfileurl is not None and series.cvstarfileurl != "":
                self.repository = str(series.cvstarfileurl)
            self.repository = str(series.cvsroot)
            self.module = str(series.cvsmodule)
            self.branchfrom = str(series.cvsbranch) # FIXME: assumes cvs!
        elif self.RCS == 'svn':
            self.repository = str(series.svnrepository)
        elif self.RCS == 'bitkeeper':
            self.repository = str(series.bkrepository)
        assert self.repository is not None and self.repository != ''

        self._arch_from_series(series)

        self.product_id = series.product.id
        self.seriesID = series.id
        self.description = series.summary
        self.releaseRoot = str(series.releaseroot)
        self.releaseFileGlob = str(series.releasefileglob)
        return self

    def _arch_from_series(self, series):
        """Setup the arch namespace from a productseries.

        If the importstatus is TESTING, and some arch namespace details are not
        filled in, we generate them.
        """
        archive = series.targetarcharchive
        category = series.targetarchcategory
        branch = series.targetarchbranch
        version = series.targetarchversion
        # Test for the truth value of the namespace components to indistinctly
        # handle None and empty string.
        if series.importstatus in [ImportStatus.TESTING,
                                   ImportStatus.AUTOTESTED,
                                   ImportStatus.TESTFAILED]:
            if not archive:
                archive = (str(series.product.name)
                           + '@autotest.bazaar.ubuntu.com')
            if not category:
                category = str(series.product.name)
            if not branch:
                # FIXME: if series.name starts with a digit, or contain
                # anything but alphanumerics and minus, that will produce an
                # illegal branch name. That could be fixed by doing url
                # escaping using '-' instead of '%' as the escaping character.
                # -- David Allouche 2005-06-18
                branch = str(series.name) + '-TEST-DO-NOT-USE'
            if not version:
                version = '0'
        assert archive
        assert category
        assert branch
        assert version
        self.archivename = str(archive)
        self.category = str(category)
        self.branchto = str(branch)
        self.archversion = str(version)

    def __str__(self):
        result=StringIO()
        self.output(result.write, " ")
        return result.getvalue()

    def output(self, receiver, terminator=""):
        receiver("TYPE=%s%s" % (self.TYPE,terminator))
        receiver("RCS=%s%s" % (self.RCS,terminator))
        receiver("repository=%s%s" % (self.repository,terminator))
        receiver("module=%s%s" % (self.module,terminator))
        receiver("category=%s%s" % (self.category,terminator))
        receiver("archivename=%s%s" % (self.archivename,terminator))
        receiver("branchfrom=%s%s" % (self.branchfrom,terminator))
        receiver("branchto=%s%s" % (self.branchto,terminator))
        receiver("archversion=%s%s" % (self.archversion,terminator))
        if self.frequency:
            receiver("frequency=%s%s" % (self.frequency,terminator))

    def toFile(self, fileName, dir=".", logger=None):
        if not os.path.isdir(dir):
             os.makedirs(dir)
        aFile = open(os.path.join(dir,fileName),'w')
        trigger, self.__jobTrigger = self.__jobTrigger, None
        pickle.dump(self, aFile)
        self.__jobTrigger = None
        aFile.close()

    def runJob(self, dir=".", logger=None):
        import JobStrategy
        if not os.path.isdir(dir):
             os.makedirs(dir)
        strategy = JobStrategy.get(self.RCS, self.TYPE)
        strategy(self, dir, logger)

    def setJobTrigger(self, trigger):
        """Set the callable to use for triggering jobs on the botmaster.

        :type trigger: callable(str)
        """
        self.__jobTrigger = trigger

    def triggerJob(self, name):
        """Send a message to the botmaster to build another job immediately.

        :param name: name of the job to build
        :type name: str
        """
        self.__jobTrigger(name)

    def mirrorTarget(self, dir=".", logger=None):
        self.mirrorVersion(dir, logger, self.bazFullPackageVersion())

    def mirrorVersion(self, dir, logger, version):
        """Publish a version to the database and the wide world.

        :type version: str
        """
        import taxi
        import util
        archive = arch.NameParser(version).get_archive()
        aTaxi = taxi.Taxi()
        aTaxi.logger = logger
        aTaxi.txnManager = util.getTxnManager()
        title = version
        version = arch.Version(version)
        mirror_location = self.archive_mirror_dir + arch.Archive(archive).name
        aTaxi.importVersion(version, mirror_location, self.product_id,
                            title=title, description=self.description,)

    def nukeTargets(self, dir=".", logger=None):
        from shutil import rmtree
        from pybaz import Archive, Version
        logger.error('nuking working tree')
        rmtree(self.getWorkingDir(dir), ignore_errors=True)
        logger.error('nuking archive targets')
        archive=Archive(self.archivename)
        if archive.is_registered():
            version = Version(self.bazFullPackageVersion())
            rmtree(self.PROPERversionLocation(version), ignore_errors=True)
        logger.error('nuking archive mirror targets')
        archive = Archive(self.archivename+'-MIRROR')
        if archive.is_registered():
            ### XXX David Allouche 2005-02-07
            ### XXX It looks like it will NOT nuke the mirror
            version = Version(self.bazFullPackageVersion())
            rmtree(self.PROPERversionLocation(version), ignore_errors=True)
        logger.error('nuked tree targets')

    def mirrorNotEmpty(self, version):
        """Is there at least one revision in the mirror for this version?

        :type version: pybaz.Version
        :rtype: bool
        """
        mirror = self.versionOnMirror(version)
        if not mirror.archive.is_registered():
            return False
        elif not mirror.exists():
            return False
        elif 0 == len(list(mirror.iter_revisions())):
            return False
        else:
            return True

    def RollbackToMirror(self, version):
        from shutil import rmtree
        if list(arch.iter_revision_libraries()):
            raise RuntimeError, \
                      "Revision library present, changing history is unsafe."
        if not version.exists():
            return
        mirror_version = self.versionOnMirror(version)
        master_levels = [rvsn.patchlevel
                         for rvsn in version.iter_revisions(reverse=True)]
        if not mirror_version.exists():
            rmtree(self.PROPERversionLocation(version))
#             for level in master_levels:
#                 rmtree(self.revisionLocation(version, level),
#                        ignore_errors=True)
            return
        mirror_levels = [rvsn.patchlevel for rvsn
                         in mirror_version.iter_revisions(reverse=True)]
        if len(mirror_levels) > len(master_levels):
            raise RuntimeError, ("Mirror is more up to date than master: %s"
                                 % mirror_version)
        mirror_last_level = None
        if len(mirror_levels):
            for level in master_levels: # relies on reverse ordering
                if level in mirror_levels:
                    mirror_last_level = level
                    break
            os.rename(self.revisionLockLocation(version, master_levels[0]),
                      self.revisionLockLocation(version, mirror_last_level))
        for level in master_levels:
            if level in mirror_levels:
                break # relies on reverse ordering
            rmtree(self.revisionLocation(version, level), ignore_errors=True)

    def versionOnMirror(self, version):
        mirror_name = version.archive.name + '-MIRROR'
        mirror_version = arch.Version(mirror_name + '/' + version.nonarch)
        return mirror_version

    def versionLocation(self, archive):
        return "/".join((archive.get_location(), self.getCategory(),
                         self.getCategory() + '--' + self.branchto,
                         self.getCategory() + '--' + self.branchto + '--' +
                         str(self.archversion)))

    def PROPERversionLocation(self, version):
        archive_loc = version.archive.location
        name = arch.NameParser(version)
        return "/".join((archive_loc, 
                         name.get_category() + "--" + name.get_branch()
                         + "--" + name.get_version()))
    

    def revisionLocation(self, version, level):
        return "/".join((self.PROPERversionLocation(version), level))

    def revisionLockLocation(self, version, level):
        return "/".join((self.revisionLocation(version, level), '++revision-lock'))

    def bazFullPackageVersion(self, archivename=None):
        """Fully-qualified Arch version.

        :param archivename: override the archive name specified in the
            `archivename` attribute. That's useful to refer to the branch in
            mirrors.

        :rtype: str
        """
        if archivename is None:
            archivename = self.archivename
        return "%s/%s" % (archivename, self.bazNonArchVersion())

    def bazNonArchVersion(self):
        """Arch version name, without the archive part."""
        category = self.getCategory()
        return "%s--%s--%s" % (category, self.branchto, self.archversion)

    def getCategory(self):
        """Arch category name, with heuristics.

        If the category was not set (or set to the empty string), use the name
        of CVS module.

        :rtype: str
        """
        if self.category == "":
            return self.module
        return self.category

    def validate(self, logger):
        """sanity check the job details, and log results"""
        name=arch.NameParser(self.bazFullPackageVersion())
        if not name.is_version():
            logger.error("invalid arch version: %s" % self.bazFullPackageVersion())
        if not self.repository:
            logger.error("Missing source repository. Target is %s"
                         % self.bazFullPackageVersion())

    def getWorkingDir(self, dir):
        """create / reuse a working dir for the job to run in"""
        version = arch.Version(self.bazFullPackageVersion())
        path = os.path.join(dir, version.archive.name, version.nonarch)
        if not os.access(path, os.F_OK):
            os.makedirs(path)
        return os.path.abspath(path)

    def endswithOneOf(self, aString, suffixes):
        """True if aString ends with one of suffixes"""
        for suffix in suffixes:
            if aString.endswith(suffix):
                return True
        return False

    def repositoryIsTar(self):
        return self.endswithOneOf(self.repository,["tar.gz", "tgz", "tar.bz2"])

    def repositoryIsRsync(self):
        return self.repository.startswith("rsync://")

    def prepRepository(self, dir, logger):
        """ensure the repository is ready to be accessed"""
        if self.repositoryIsTar():
            pass #tar
        elif self.repositoryIsRsync():
            pass #rsync

    def sourceBranch(self):
        if not self.branchfrom:
            # and svn ?
            return "MAIN"
        return self.branchfrom


class CopyJob(Job, pb.Copyable):
    """I am a remotely copyable version of Job"""
    pass
