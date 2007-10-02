# Copyright 2004-2005 Canonical Ltd.
# Author: Robert Collins  <robertc@robertcollins.net>

import os
from StringIO import StringIO
import pickle
import shutil

from twisted.spread import pb

from canonical.lp.dbschema import ImportStatus
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.interfaces import RevisionControlSystems
from importd import JobStrategy
from importd.bzrmanager import BzrManager

# official .job spec:
# job format
# TYPE=import
# RCS=svn|cvs
# repository=string  i.e. http://example.com/tarball-of-cvs-module.tar.bz2
#                         :pserver:user:password@anoncvs.example.com/server/cvs
# module=NULL (for svn) | string
# category=string
# archivename=string
# branchfrom=NULL (for svn) | string
# branchto=string
# archversion=x[[.x]...]

def _interval_to_seconds(interval):
    try:
        return interval.days * 24 * 60 * 60 + interval.seconds
    except AttributeError:
        msg = "Failed to convert interval to seconds: %r" % (interval,)
        raise TypeError(msg)


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
        self.branchfrom="MAIN"
        self.frequency=None
        self.__jobTrigger = None
        self.logger = None

    def from_sourcepackagerelease(self, sourcepackagerelease, distroseries):
        # we need the distroseries as a hint for branch names etc, and
        # as a way of verifying distro-specific import policy
        # first construct a sourcepackage for this import
        sp = SourcePackage(
                sourcepackagename=sourcepackagerelease.sourcepackagename,
                distroseries=distroseries)
        assert sp.shouldimport, ('%s %s %s should not be imported' %
                                (distroseries.distribution.name,
                                 distroseries.name,
                                 sourcepackagerelease.name))
        self.name = 'pkg'
        self.name += '-' + distroseries.distribution.name
        self.name += '-' + distroseries.name
        self.name += '-' + sourcepackagerelease.name
        self.name += '-' + sourcepackagerelease.version
        self.sourcepackagerelease = sourcepackagerelease
        self.distroseries = distroseries
        self.RCS = 'package'
        self.TYPE = 'sourcerer'
        self.product_id = sp.product.id
        # XXX sabdfl 2005-04-12: these are commented out until the Packaging
        # table has been fixed to support series-level granularity
        #assert sp.productseries is not None, ("Attempt to import %s %s %s "
        #        "which is not mapped to an upstream "
        #        "product series" %
        #        (distroseries.distribution.name,
        #         distroseries.name,
        #         sourcepackagerelease.name))
        #self.series_id = sp.productseries.id
        #self.series_branch = sp.productseries.branch
        #assert self.series_branch is not None, ("Attempt to import %s %s %s"
        #    " which has no upstream branch" %
        #        (distroseries.distribution.name,
        #         distroseries.name,
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

        name = series.product.name + '-' + series.name
        if series.product.project is not None:
            name = series.product.project.name + '-' + name
        self.name = name
        RCSNames = {
            RevisionControlSystems.CVS: 'cvs',
            RevisionControlSystems.SVN: 'svn',
            }
        self.RCS = RCSNames[series.rcstype]

        # set the repository
        if self.RCS == 'cvs':
            if self._use_cvstarfileurl(series):
                assert series.cvstarfileurl
                self.repository = str(series.cvstarfileurl)
            else:
                assert series.cvsroot
                self.repository = str(series.cvsroot)
            assert series.cvsmodule
            self.module = str(series.cvsmodule)
            assert series.cvsbranch
            self.branchfrom = str(series.cvsbranch)
        elif self.RCS == 'svn':
            assert series.svnrepository
            self.repository = str(series.svnrepository)

        self.product_id = series.product.id
        self.seriesID = series.id
        self.description = series.summary
        return self

    def _use_cvstarfileurl(self, series):
        "Should import be done by downloading a CVS repository tarball?"
        if self.RCS != 'cvs':
            return False
        elif self.TYPE != 'import':
            return False
        elif series.cvstarfileurl is None or series.cvstarfileurl == "":
            return False
        else:
            return True

    def __str__(self):
        result=StringIO()
        self.output(result.write, " ")
        return result.getvalue()

    def output(self, receiver, terminator=""):
        receiver("TYPE=%s%s" % (self.TYPE, terminator))
        receiver("RCS=%s%s" % (self.RCS, terminator))
        receiver("repository=%s%s" % (self.repository, terminator))
        receiver("module=%s%s" % (self.module, terminator))
        receiver("branchfrom=%s%s" % (self.branchfrom, terminator))
        if self.frequency:
            receiver("frequency=%s%s" % (self.frequency, terminator))

    def prepare(self, fileName, dir=".", logger=None):
        """Pickle the job and create the working directory."""
        self.getWorkingDir(dir)
        if not os.path.isdir(dir):
             os.makedirs(dir)
        aFile = open(os.path.join(dir,fileName),'w')
        trigger, self.__jobTrigger = self.__jobTrigger, None
        pickle.dump(self, aFile)
        self.__jobTrigger = None
        aFile.close()

    def runJob(self, dir=".", logger=None):
        self.working_root = dir
        self.logger = logger
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
        self.working_root = dir
        self.logger = logger
        working_dir = self.getWorkingDir(dir)
        self.makeTargetManager().mirrorBranch(working_dir)

    targetManagerType = BzrManager

    def makeTargetManager(self):
        """Factory method to create an ArchiveManager for this job."""
        return self.targetManagerType(self)

    def nukeTargets(self, dir='.', logger=None):
        """Remove the working tree and master archive.

        This is used to clean up the remains of a failed import before running
        the import a second time.
        """
        self.working_root = dir
        self.logger = logger
        logger.info('nuking working tree')
        shutil.rmtree(self.getWorkingDir(dir), ignore_errors=True)
        logger.info('nuked tree targets')

    def targetBranchName(self):
        """Target format independent name of the target branch.

        That should return an Arch branch name when the target format is Arch,
        and the url of the local target branch when the target format is bzr.
        """
        return self.makeTargetManager().targetBranchName(self.working_root)

    def getWorkingDir(self, dir, create=True):
        """create / reuse a working dir for the job to run in"""
        series_id = self.seriesID
        path = os.path.join(dir, 'series-%08x' % series_id)
        if create and not os.access(path, os.F_OK):
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


class CopyJob(Job, pb.Copyable):
    """I am a remotely copyable version of Job"""
    pass
