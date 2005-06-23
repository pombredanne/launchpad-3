#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

#from twisted.trial import unittest
import unittest
import sys
import os
import logging
import shutil
import datetime

import gnarly.process
import gnarly.process.unix_process
gnarly.process.Popen = gnarly.process.unix_process.Popen

import pybaz
import pybaz as arch
import pybaz.backends.forkexec
pybaz.backend.spawning_strategy = pybaz.backends.forkexec.PyArchSpawningStrategy

from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup

class JobCreationTestCase(unittest.TestCase):
    def testConstruct(self):
        """Test creation of Job"""
        from importd import Job
        foo=Job.Job()


class JobTestCase(unittest.TestCase):

    def testRunCVSSyncJob(self):
        """test runJob calls the strategy"""
        from importd import Job
        from pybaz.errors import NamespaceError
        aJob=Job.Job()
        aJob.RCS="CVS"
        aJob.TYPE="sync"
        try:
            aJob.runJob("./,,foo")
        except (AssertionError, NamespaceError):pass

    def testTlaFullPackageVersion(self):
        """test full package version is calculated correctly"""
        import importd.Job as Job
        aJob=Job.Job()
        aJob.TYPE="importd"
        aJob.RCS="CVS"
        aJob.repository="cvs"
        aJob.archivename="archive"
        aJob.module="bar"
        assert (aJob.bazFullPackageVersion() == "archive/bar--HEAD--0")
        aJob.category="category"
        assert (aJob.bazFullPackageVersion() == "archive/category--HEAD--0")
        aJob.branchfrom="phwoar"
        assert (aJob.bazFullPackageVersion() == "archive/category--HEAD--0")
        aJob.branchto="branch"
        assert (aJob.bazFullPackageVersion() == "archive/category--branch--0")
        aJob.archversion="1"
        assert (aJob.bazFullPackageVersion() == "archive/category--branch--1")
        self.assertEqual (aJob.bazNonArchVersion(), "category--branch--1")


class LoggingCounter(logging.Handler):
    """I count log messages"""

    def __init__(self):
        logging.Handler.__init__(self)
        self.messages=0

    def emit(self, record):
        """count the message"""
        self.messages+=1


class TestJobValidation(unittest.TestCase):
    """test job validation logic"""

    def setUp(self):
        """we need to see where the msgs go"""
        import logging
        self.counter=LoggingCounter()
        self.logger=logging.Logger("test")
        self.logger.addHandler(self.counter)

    def tearDown(self):
        self.logger.removeHandler(self.counter)

    def testTarget(self):
        """test job validation checks targets"""
        from importd import Job
        badJob=Job.Job()
        badJob.repository="http://site/foo.tar.bz2"
        badJob.validate(self.logger)
        self.assertEqual(self.counter.messages, 1)

    def testRepository(self):
        """test job validation checks repository"""
        from importd import Job
        badJob=Job.Job()
        badJob.category="c"
        badJob.archivename="a@b"
        badJob.branchto="b"
        badJob.archversion=0
        badJob.validate(self.logger)
        self.assertEqual(self.counter.messages, 1)


class CopyJobTestCase(unittest.TestCase):

    def testRunCVSSyncJob(self):
        """test CopyJob.runJob calls the strategy"""
        from importd import Job
        from pybaz.errors import ArchiveNotRegistered
        aJob=Job.CopyJob()
        aJob.RCS="CVS"
        aJob.TYPE="sync"
        aJob.archivename="archive@archive"
        aJob.category="category"
        aJob.branchto="branch"
        aJob.archversion="1"
        try:
            aJob.runJob("./,,foo")
            self.fail('should raise')
        except (AssertionError,RuntimeError, ArchiveNotRegistered):
            pass

    def testTlaFullPackageVersion(self):
        """test full package version is calculated correctly for CopyJob"""
        from importd import Job
        aJob=Job.CopyJob()
        aJob.TYPE="importd"
        aJob.RCS="CVS"
        aJob.repository="cvs"
        aJob.archivename="archive"
        aJob.module="bar"
        assert (aJob.bazFullPackageVersion() == "archive/bar--HEAD--0")
        aJob.category="category"
        assert (aJob.bazFullPackageVersion() == "archive/category--HEAD--0")
        aJob.branchfrom="phwoar"
        assert (aJob.bazFullPackageVersion() == "archive/category--HEAD--0")
        aJob.branchto="branch"
        assert (aJob.bazFullPackageVersion() == "archive/category--branch--0")
        aJob.archversion="1"
        assert (aJob.bazFullPackageVersion() == "archive/category--branch--1")
        self.assertEqual (aJob.bazNonArchVersion(), "category--branch--1")


class JobStrategyCreationTestCase(unittest.TestCase):

    def testGet(self):
        """Test getting a Strategy"""
        from importd import JobStrategy
        foo=JobStrategy.get("CVS", "sync")
        bar=JobStrategy.get("cvs", "sync")
        JobStrategy.get("package", "sourcerer")

    def testGetInvalidRCS(self):
        """Test getting with invalid RCS"""
        from importd import JobStrategy
        try:
            foo=JobStrategy.get("blargh", "sync")
        except KeyError:
            pass

    def testGetInvalidType(self):
        """Test getting with invalid type"""
        from importd import JobStrategy
        try:
            foo=JobStrategy.get("CVS", "blargh")
        except KeyError:pass


class CVSStrategyTestCreation(unittest.TestCase):
    def testParse(self):
        """test that CVSStrategy can be imported"""
        from importd.JobStrategy import CVSStrategy
    def testConstruct(self):
        """test creating a CVSStrategy"""
        from importd.JobStrategy import CVSStrategy
        foo=CVSStrategy()

def makeTestJob():
    """create a common job for test use"""
    from importd import Job
    class TestJob(Job.CopyJob):
        def __init__(self):
            Job.CopyJob.__init__(self)
            self.rollbackToMirrorCount = 0
        def RollbackToMirror(self, version):
            Job.CopyJob.RollbackToMirror(self, version)
            self.rollbackToMirrorCount += 1
    aJob=TestJob()
    aJob.RCS="CVS"
    aJob.TYPE="sync"
    aJob.repository=os.path.abspath(",,cvsroot1")
    aJob.module="test"
    aJob.category="test"
    aJob.archivename="test@importd.example.com"
    aJob.branchfrom="MAIN"
    aJob.branchto="HEAD"
    aJob.archversion=0
    return aJob


class ArchiveTestCase(unittest.TestCase):
    """Helper for test cases requiring an arch archive."""

    baz_archive_location = ',,temp-archive1'
    baz_mirror_location = ",,temp-archive2"
    baz_tree_location = ',,temp-dir'

    def setUp(self):
        import pybaz as arch
        self.here = os.getcwd()
        self.home_dir = os.environ.get('HOME')
        self.test_dir = os.path.join(self.here, ',,job-test')
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.mkdir(self.test_dir)
        os.environ['HOME'] = self.test_dir
        arch.set_my_id("John Doe <jdoe@example.com>")

    def tearDown(self):
        os.environ['HOME'] = self.home_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.baz_mirror_location, ignore_errors=True)
        os.chdir(self.here)

    def setupArchArchive(self, versionString, signed=False):
        """I setup a small baz repository to sync with"""
        import pybaz as arch
        parser = arch.NameParser(versionString)
        archive = arch.Archive(parser.get_archive())
        if archive.is_registered():
            archive.unregister()
        shutil.rmtree(self.baz_archive_location, ignore_errors=True)
        self.baz_archive = arch.make_archive(
            parser.get_archive(), os.path.abspath(self.baz_archive_location),
            signed=signed)

    def setupArchMirror(self, versionString):
        from pybaz import Archive
        name = self.baz_archive.name + '-MIRROR'
        location = os.path.abspath(self.baz_mirror_location)
        mirror = Archive(name)
        if mirror.is_registered(): mirror.unregister()
        shutil.rmtree(location, ignore_errors=True)
        self.baz_archive.make_mirror(name, location)

    def setupArchTree(self, versionString):
        import pybaz as arch
        shutil.rmtree(self.baz_tree_location, ignore_errors=True)
        os.mkdir(self.baz_tree_location)
        version = arch.Version(versionString)
        self.baz_tree = arch.init_tree(
            self.baz_tree_location, version, nested=True)

    def setupBaseZero(self):
        wt = self.baz_tree
        wt.import_()

    def setupPatchOne(self):
        wt = self.baz_tree
        msg = wt.log_message()
        msg['Summary'] = 'first revision'
        wt.commit(msg)

    def archiveSetupVersion(self, archive, version):
        os.mkdir(os.path.join(archive.location, version.nonarch))


class ArchiveRollbackTestCase(ArchiveTestCase):
    """Archive rollback, time-translate a version to the point of the mirror"""

    version_fullname = "jo@example.com/foo-bar--HEAD--0"

    def setUp(self):
        ArchiveTestCase.setUp(self)
        self.revlib_dir = os.path.join(self.test_dir, 'revlib')
        self.setupArchArchive(self.version_fullname)
        self.setupArchMirror(self.version_fullname)
        self.setupArchTree(self.version_fullname)

    def tearDown(self):
        for name in (self.baz_tree_location, self.baz_archive_location):
            shutil.rmtree(name, ignore_errors=True)
        ArchiveTestCase.tearDown(self)


    def makeJob(self):
        from importd.Job import Job
        from pybaz import NameParser
        job = Job()
        parser = NameParser(self.version_fullname)
        job.category = parser.get_category()
        job.archivename = parser.get_archive()
        job.archversion = parser.get_version()
        job.branchto = parser.get_branch()
        return job
    
    def testRollackFailIfRevlib(self):
        """rollbackToMirror fails with RuntimeError is a revlib is present"""
        import pybaz as arch
        os.mkdir(self.revlib_dir)
        arch.register_revision_library(self.revlib_dir)
        version = arch.Version(self.version_fullname)
        def func(): self.makeJob().RollbackToMirror(version)
        self.assertRaises(RuntimeError, func)

    def testNothingToRollback(self):
        """rollbackToMirror is safe when mirror is up to date"""
        import pybaz as arch
        self.setupBaseZero()
        self.setupPatchOne()
        version = arch.Version(self.version_fullname)
        expected = [version[L] for L in ('base-0', 'patch-1')]
        self.assertEqual(expected, list(version.iter_revisions()))
        self.baz_archive.mirror(limit=[self.version_fullname])
        self.makeJob().RollbackToMirror(version)
        self.assertEqual(expected, list(version.iter_revisions()))        

    def testRollbackOneRevision(self):
        """rollbackToMirror can remove the latest revision"""
        import pybaz as arch
        self.setupBaseZero()
        self.baz_archive.mirror(limit=[self.version_fullname])
        self.setupPatchOne()
        version = arch.Version(self.version_fullname)
        expected = [version[L] for L in ('base-0', 'patch-1')]
        self.assertEqual(expected, list(version.iter_revisions()))
        self.makeJob().RollbackToMirror(version)
        expected = [version[L] for L in ('base-0',)]
        self.assertEqual(expected, list(version.iter_revisions()))

    def getCleanTestTree(self):
        import pybaz as arch
        shutil.rmtree(self.baz_tree_location)
        arch.Version(self.version_fullname).get(self.baz_tree_location)

    def testCommitAfterRollback(self):
        """rollbackToMirror does not prevent further commits"""
        import pybaz as arch
        self.testRollbackOneRevision()
        try:
            self.getCleanTestTree()
            self.setupPatchOne()
        except arch.ExecProblem, e:
            self.fail("CAUGHT %s" % e)
        version = arch.Version(self.version_fullname)
        expected = [version[L] for L in ('base-0', 'patch-1')]
        self.assertEqual(expected, list(version.iter_revisions()))

    def testRollbackToEmptyVersion(self):
        """rollbackToMirror works when reverting to empty version"""
        import pybaz as arch
        self.baz_archive.mirror(limit=[self.version_fullname])
        version = arch.Version(self.version_fullname)
        mirror = arch.Archive(version.archive.name + '-MIRROR')
        self.archiveSetupVersion(mirror, version)
        self.setupBaseZero()
        self.setupPatchOne()
        expected = [version[L] for L in ('base-0', 'patch-1')]
        self.assertEqual(expected, list(version.iter_revisions()))
        self.makeJob().RollbackToMirror(version)
        expected = []
        self.assertEqual(expected, list(version.iter_revisions()))
        
    def testRollbackToNonExistent(self):
        """rollbackToMirror works when reverting to a non existent version"""
        import pybaz as arch
        self.setupBaseZero()
        self.setupPatchOne()
        version = arch.Version(self.version_fullname)
        expected = [version[L] for L in ('base-0', 'patch-1')]
        self.assertEqual(expected, list(version.iter_revisions()))
        self.makeJob().RollbackToMirror(version)
        self.failIf(version.exists())


class MirrorNotEmptyTestCase(ArchiveTestCase):
    """Test cases for the mirrorNotEmpty predicate."""

    version_fullname = "jo@example.com/foo-bar--HEAD--0"

    def setUp(self):
        ArchiveTestCase.setUp(self)
        self.setupArchArchive(self.version_fullname)
        import pybaz as arch
        self.version = arch.Version(self.version_fullname)
        self.job = self.makeNullJob()

    def makeNullJob(self):
        from importd import Job
        return Job.Job()

    def testVersionOnMirror(self):
        """mirrorVersion works."""
        import pybaz as arch
        version = self.version
        mirrorversion = arch.Version("jo@example.com-MIRROR/foo-bar--HEAD--0")
        self.assertEqual(self.job.versionOnMirror(version), mirrorversion)

    def testMirrorNotRegistered(self):
        """mirrorNotEmpty is False if mirror not registered."""
        import pybaz as arch
        assert not arch.Archive("jo@example.com-MIRROR").is_registered()
        self.failIf(self.job.mirrorNotEmpty(self.version))

    def testMirrorHasNoVersion(self):
        """mirrorNotEmpty is False if mirror has no version."""
        import pybaz as arch
        self.setupArchMirror(self.version_fullname)
        assert arch.Archive("jo@example.com-MIRROR").is_registered()
        mirrorversion = self.job.versionOnMirror(self.version)
        assert 0 == len(list(mirrorversion.archive.iter_versions()))
        self.failIf(self.job.mirrorNotEmpty(self.version))

    def testMirrorHasEmptyVersion(self):
        """mirrorNotEmpty is False if mirror has empty version."""
        import pybaz as arch
        self.setupArchMirror(self.version_fullname)
        assert arch.Archive("jo@example.com-MIRROR").is_registered()
        mirrorversion = self.job.versionOnMirror(self.version)
        self.archiveSetupVersion(mirrorversion.archive, mirrorversion)
        assert mirrorversion.exists()
        assert 0 == len(list(mirrorversion.iter_revisions()))
        self.failIf(self.job.mirrorNotEmpty(self.version))

    def testMirrorNotEmpty(self):
        """mirrorNotEmpty is True if mirror version is not empty."""
        import pybaz as arch
        self.setupArchMirror(self.version_fullname)
        self.setupArchTree(self.version_fullname)
        self.setupBaseZero()
        self.baz_archive.mirror(limit=[self.version_fullname])
        mirrorversion = self.job.versionOnMirror(self.version)
        assert 1 == len(list(mirrorversion.iter_revisions()))
        self.failUnless(self.job.mirrorNotEmpty(self.version))


class CVSStrategyTestCase(ArchiveTestCase):
    """I test the functionality of CVSStrategy"""

    def setupSyncEnvironment(self, aJob):
        """I create a environment that a sync can be performed in"""
        self.setupArchArchive(aJob.bazFullPackageVersion())
        self.setupCVSToSyncWith()
        self.doRevisionOne(aJob)

    def setupCVSToSyncWith(self):
        """I setup a small CVS repository to sync with"""
        import CVS
        # todo fixup this duplication of ,,cvsroot1 definition
        self.cvsroot=os.path.abspath(",,cvsroot1")
        repo=CVS.init(self.cvsroot)
        sourcedir=",,code1"
        shutil.rmtree(sourcedir, ignore_errors=True)
        os.mkdir(sourcedir)
        aFile=open(sourcedir + "/file1", "w")
        print >> aFile, "import" 
        aFile.close()
        repo.Import(module="test", log="import", vendor="vendor", release=['release'],dir=sourcedir)
        shutil.rmtree(sourcedir, ignore_errors=True)
        repo.get(module="test", dir=sourcedir)
        aFile=open(sourcedir + "/file1", "w")
        print >> aFile, "change1"
        aFile.close()
        cvsTree=CVS.tree(sourcedir)
        cvsTree.commit(log="change 1")
        shutil.rmtree(sourcedir, ignore_errors=True)

    def doRevisionOne(self,aJob):
        """I sync revision 1 into CVS"""
        import CVS
        import logging
        self.setupArchTree(aJob.bazFullPackageVersion())
        # get CVS dir
        shutil.rmtree(",,cvs-source1", ignore_errors=True)
        cvsrepo=CVS.Repository(self.cvsroot, logging)
        cvsrepo.get(module="test", dir=",,cvs-source1")
        from cscvs.cmds import cache
        argv=["-b"]
        startDir=os.path.abspath(os.path.curdir)
        config=CVS.Config(",,cvs-source1")
        config.args = argv
        cache.cache(config, logging, argv)
        from cscvs.cmds import totla
        config=CVS.Config(",,cvs-source1")
        config.args = ["-Si", "%s" % 1, self.baz_tree_location]
        totla.totla(config, logging, ["-Si", "%s" % 1, self.baz_tree_location])
        shutil.rmtree(self.baz_tree_location, ignore_errors=True)
        shutil.rmtree(",,cvs-source1", ignore_errors=True)

    def testGetWorkingDir(self):
        """test that the working dir is calculated & created correctly"""
        from importd.JobStrategy import CVSStrategy
        foo=CVSStrategy()
        try:
            assert(foo.getWorkingDir(makeTestJob(),".") == os.path.abspath("./test@importd.example.com/test--HEAD--0"))
            assert(os.access("./test@importd.example.com/test--HEAD--0", os.F_OK))
        finally:
            shutil.rmtree("test@importd.example.com", ignore_errors=True)
    
    def testGetCVSDir(self):
        """test ensuring we have an updated CVS dir with a cscvs cache in it"""
        from importd.JobStrategy import CVSStrategy
        import logging
        foo=CVSStrategy()
        #TODO test detailed parameters etc.
        aJob=makeTestJob()
        self.setupSyncEnvironment(aJob)
        cvspath=foo.getCVSDirPath(aJob,".")
        foo.aJob=aJob
        foo.logger=logging
        path=foo.getCVSDir(aJob, ".")
        assert(path==cvspath)
        if not os.access(os.path.join(cvspath, "CVS", "Catalog.sqlite"), os.F_OK):
            raise RuntimeError("Catalog not created")

    def testSync(self):
        """test performing a sync"""
        from importd.JobStrategy import CVSStrategy
        import logging
        strategy = CVSStrategy()
        self.assertRaises(AssertionError, strategy.sync, None, ".", None)
        self.assertRaises(AssertionError, strategy.sync, ".", None, None)
        self.assertRaises(AssertionError, strategy.sync, None, None, logging)
        aJob = makeTestJob()
        self.setupSyncEnvironment(aJob)
        self.setupArchMirror(aJob.bazFullPackageVersion())
        strategy.sync(aJob, ".", logging)
        self.assertEqual(0, aJob.rollbackToMirrorCount)
        import pybaz as arch
        version = arch.Version(aJob.bazFullPackageVersion())
        self.assertEqual(2, len(list(version.iter_revisions())))
        version.archive.mirror()
        strategy.sync(aJob, ".", logging)
        self.assertEqual(1, aJob.rollbackToMirrorCount)


class PackageStrategyTestCase(ArchiveTestCase):
    '''test PackageStrategy'''
    def setUp(self):
        ArchiveTestCase.setUp(self)
        LaunchpadZopelessTestSetup().setUp()

    def testAccess(self):
        '''test we can actually get at the lp database'''
        from canonical.launchpad.database.person import Person
        stub = Person.byName('stub')
        self.assertEqual(stub.displayname, u'Stuart Bishop')

    def testArchiveName(self):
        '''test the archive name calculation from the product and distro
        information'''
        from importd.JobStrategy import PackageStrategy
        job=makeTestJob()
        job.type='package'
        strategy=PackageStrategy()
        strategy.aJob = job
        self.assertEqual(strategy.archiveName(), job.archivename)

    def testStrategy(self):
        '''test calling a package strategy from the database'''
        from importd import Job, JobStrategy
        from canonical.launchpad.database import SourcePackageRelease, \
                DistroRelease
        import logging
        # get sample data and verify it
        spr = SourcePackageRelease.get(15) # evolution 1.0 in sampledata
        self.assertEqual(spr.name, 'evolution')
        self.assertEqual(spr.version, '1.0')
        dr = DistroRelease.get(3) # ubuntu hoary in sampledata
        self.assertEqual(dr.name, 'hoary')
        self.assertEqual(dr.distribution.name, 'ubuntu')
        job=Job.CopyJob()
        job.from_sourcepackagerelease(spr, dr)
        strategy=JobStrategy.get(job.RCS, job.TYPE)
        # pretend to be a buildbot slave
        # 
        job.slave_home=',,StrategyHome'
        job.archive_mirror_dir=',,StrategyMirror'
        signing_dir = os.path.expanduser("~/.arch-params/signing")
        os.makedirs(signing_dir)
        self.setupArchArchive(job.archivename + "/foo--bar-0")
        self.setupArchMirror(job.archivename + "/foo--bar-0")
        # XXX sabdfl 11/04/05 disabled till I figure out how to do a
        # librarian during testing
        # strategy(job, ",,Strategy", logging, self.captcha)

    def captcha(self, *args):
        # sabdfl 11/04/05 this *appears* to want to verify the arguments
        # that would be passed to bubblewrap by the PackageStrategy
        import logging
        self.assertEqual(len(args), 6)
        self.assertEqual(args[0], [])
        self.assertEqual(args[1], 'evolution@arch.ubuntu.com')
        self.assertEqual(args[2], 9)
        self.assertEqual(args[3], logging)
        self.assertEqual(args[4], ",,Strategy")
        self.assertEqual(type(args[5]), type(self.captcha))

    def tearDown(self):
        shutil.rmtree(",,Strategy", ignore_errors=True)
        shutil.rmtree(",,StrategyHome", ignore_errors=True)
        shutil.rmtree(",,StrategyMirror", ignore_errors=True)
        LaunchpadZopelessTestSetup().tearDown()
        ArchiveTestCase.tearDown(self)


class TestRepoType(unittest.TestCase):
    """I test repo identification works"""

    def testRsync(self):
        """rsync repositories are identified"""
        from importd.Job import Job
        job=Job()
        job.repository="rsync://phwoar"
        self.failUnless(job.repositoryIsRsync())

    def testTar(self):
        """tar balls are identified correctly"""
        from importd.Job import Job
        job=Job()
        job.repository="foo.tgz"
        self.failUnless(job.repositoryIsTar())
        job.repository="foo.tar.gz"
        self.failUnless(job.repositoryIsTar())
        job.repository="foo.tar.bz2"
        self.failUnless(job.repositoryIsTar())


class TestArchStrategy(ArchiveTestCase):
    
    version_fullname = "jo@example.com/foo-bar--devel--0"
    baz_mirror_location = ",,temp-archive2"

    def setUp(self, signed=False):
        ArchiveTestCase.setUp(self)
        self.slave_home = ',,temp-slave-home'
        shutil.rmtree(self.slave_home, ignore_errors=True)
        os.mkdir(self.slave_home)
        self.setupArchArchive(self.version_fullname, signed=signed)
        if signed: self._setup_signing()
        self.setupArchTree(self.version_fullname)
        self.setupBaseZero()
        self.setupPatchOne()

    def tearDown(self):
        for name in (self.slave_home, self.baz_tree_location,
                     self.baz_archive_location, self.baz_mirror_location):
            shutil.rmtree(name, ignore_errors=True)
        ArchiveTestCase.tearDown(self)

    def makeJob(self, gpguser=None):
        from importd.Job import Job
        from pybaz import NameParser
        parser = NameParser(self.version_fullname)
        job = Job()
        job.archsourceurl = os.path.abspath(self.baz_archive_location)
        job.archsourcearchive = parser.get_archive()
        job.archsourcegpg = gpguser
        job.archive_mirror_dir = os.path.abspath(self.baz_mirror_location)
        job.slave_home = os.path.abspath(self.slave_home)
        return job

    def testMirrorFromScratch(self, gpguser=None):
        """ArchStrategy.mirror works from scratch with unsigned source."""
        from importd import JobStrategy
        import pybaz as arch
        mirror = arch.Archive(
            arch.NameParser(self.version_fullname).get_archive() + '-MIRROR')
        if mirror.is_registered(): mirror.unregister()
        job = self.makeJob(gpguser)
        JobStrategy.ArchStrategy().mirror(job, None, logging)
        expected = ['base-0', 'patch-1']
        result = [ rvsn.patchlevel for rvsn in
                   arch.Version(self.version_fullname).iter_revisions() ]
        self.assertEqual(expected, result)


def test_file(basename):
    test_dir = os.path.dirname(__file__)
    relpath = os.path.join(test_dir, basename)
    return os.path.abspath(relpath)
    

class TestArchStrategySigned(TestArchStrategy):
    
    def setUp(self):
        TestArchStrategy.setUp(self, signed=True)

    def _setup_signing(self):
        import pybaz as arch
        parser = arch.NameParser(self.version_fullname)
        self.archive_name = parser.get_archive()
        signing_dir = os.path.expanduser("~/.arch-params/signing")
        os.makedirs(signing_dir)
        self.signing_rule_file = os.path.join(signing_dir, self.archive_name)
        print >> open(self.signing_rule_file, 'w'), (
            "gpg --default-key john.doe@snakeoil --no-default-keyring"
            " --secret-keyring %s --keyring %s --clearsign"
            % tuple(map(test_file, ("john.doe@snakeoil.gpg",
                              "john.doe@snakeoil.pub"))))
        try:
	    print >> open(os.path.expanduser("~/.arch-params/archives/defaults"), 'w'), (
                "gpg_comand=gpg\n"
                "gpg_options= --default-key john.doe@snakeoil --no-default-keyring"
                " --secret-keyring %s --keyring %s"
                % tuple(map(test_file, ("john.doe@snakeoil.gpg",
                                  "john.doe@snakeoil.pub"))))
        except IOError:
            pass
        gpgdir = os.path.join(self.slave_home, 'gpg')
        os.mkdir(gpgdir)
        for name in ("john.doe@snakeoil.gpg", "john.doe@snakeoil.pub"):
            shutil.copyfile(test_file(name), os.path.join(gpgdir, name))
        

    def tearDown(self):
       rule = self.signing_rule_file
       for name in (rule, rule + '.check',
                    rule + '-MIRROR', rule + '-MIRROR.check'):
           if os.path.isfile(name):
               os.unlink(name)
       TestArchStrategy.tearDown(self)

    def testMirrorFromScratch(self):
        """ArchStrategy.mirror works from scratch with SIGNED source."""
        TestArchStrategy.testMirrorFromScratch(self, 'john.doe@snakeoil')
        self.failUnless(os.path.isfile(os.path.join(
            self.baz_mirror_location,
            '=meta-info', 'signed-archive')))

# def threadTest(aTest):
#     """Run a test in a thread to work around Twisted insanity.
#
#     That is intended to prevent "interrupted system call" errors
#     occuring in cscvs and PyArch because of some obscure voodoo
#     interactions with the Twisted environment.
#     """
#     from twisted.internet import threads
#     from twisted.trial.util import deferredResult
#     return deferredResult(threads.deferToThread(aTest))

class sampleData:

    package_import_id = 15
    package_import_distrorelease_id = 3 # ubuntu hoary
    package_job_name = 'pkg-ubuntu-hoary-evolution-1.0'
    cvs_job_id = 3 # this is ProductSeries.id 3 for the evolution
    cvs_job_name = 'gnome-evolution-main'
    product_id = 5
    product_name = 'evolution'

class ZopelessTestCase(unittest.TestCase):
    """Base class for test cases that need database access."""

    def setUp(self):
        LaunchpadZopelessTestSetup().setUp()

    def tearDown(self):
        LaunchpadZopelessTestSetup().tearDown()


class TestGetJob(ZopelessTestCase):
    '''can we get a job from the database'''

    def testGetBuilders(self):
        '''get a builders list from the db'''
        import importd.util
        from canonical.lp.dbschema import ImportStatus
        jobs = importd.util.jobsFromDB("slave_home",
                                       "archive_mirror_dir",
                                       [ImportStatus.PROCESSING])
        self.assertEqual(len(jobs), 1)
        builders = importd.util.jobsBuilders(jobs, ["slavename"], autotest=False)
        self.assertEqual(len(builders), 1)

    def testGetPackageJob(self):
        '''get a usable package job from the db'''
        from canonical.launchpad.database import SourcePackage, \
                SourcePackageRelease, DistroRelease
        from importd.Job import CopyJob
        pkgid = sampleData.package_import_id
        drid = sampleData.package_import_distrorelease_id
        spr = SourcePackageRelease.get(pkgid)
        dr = DistroRelease.get(drid)
        job = CopyJob().from_sourcepackagerelease(spr, dr)
        self.assertEqual(job.TYPE, 'sourcerer')
        self.assertEqual(job.RCS, 'package')
        self.assertEqual(job.product_id, sampleData.product_id)
        self.assertEqual(job.name, sampleData.package_job_name)

    def testGetCVSJob(self):
        """get a usable CVS job from the db"""
        from canonical.launchpad.database import ProductSeries
        from importd.Job import CopyJob
        job = CopyJob().from_series(ProductSeries.get(sampleData.cvs_job_id))
        self.assertEqual(job.TYPE, 'import')
        self.assertEqual(job.RCS, 'cvs')
        self.assertEqual(job.product_id, sampleData.product_id)
        self.assertEqual(job.name, sampleData.cvs_job_name)

    def testGetJobInterval(self):
        """get a CVS sync job with an syncinterval from the db"""
        from canonical.launchpad.database import ProductSeries
        from importd.Job import CopyJob
        series = ProductSeries.get(sampleData.cvs_job_id)
        interval = datetime.timedelta(days=1)
        series.syncinterval = interval
        series.enableAutoSync()
        series = ProductSeries.get(sampleData.cvs_job_id)
        self.assertEqual(series.syncinterval, interval)
        job = CopyJob().from_series(series)
        day_seconds = 24 * 60 * 60
        self.assertEqual(job.frequency, day_seconds)

class MockJob(object):
    pass

class TestInterlockNonDB(unittest.TestCase):

    """Interlock tests that do not need the database."""

    def mockJob(self, name, product_id, rcs):
        job = MockJob()
        job.name = name
        job.product_id = product_id
        job.RCS = rcs
        return job

    def testNoJob(self):
        """jobsInterlocks works with an empty job list."""
        import importd.util
        interlocks = importd.util.jobsInterlocks([])
        self.assertEqual(interlocks, [])

    def testAnonInterlock(self):
        """anonymousInterlock separates one package and one cvs"""
        import importd.util
        cvs = self.mockJob('foo-head', 1, 'cvs')
        pkg = self.mockJob('foo-warty', 1, 'package')
        interlock = importd.util.anonymousInterlock([pkg, cvs])
        self.assertEqual(2, len(interlock))
        self.assertEqual([1,1], map(len, interlock))
        self.assertEqual(cvs.name, interlock[0][0])
        self.assertEqual(pkg.name, interlock[1][0])

    def testAnonNoInterlock(self):
        """anonymousInterlock handles absence of interlock"""
        import importd.util
        cvs = self.mockJob('foo', 1, 'cvs')
        pkg = self.mockJob('foo', 1, 'package')
        interlock = importd.util.anonymousInterlock([pkg])
        self.assertEqual(interlock, None)
        interlock = importd.util.anonymousInterlock([cvs])
        self.assertEqual(interlock, None)

    def testNoInterlock(self):
        """jobsInterlocks does not interlock different products."""
        import importd.util
        cvs = self.mockJob('foo-head', 1, 'cvs')
        pkg = self.mockJob('bar-warty', 2, 'package')
        interlocks = importd.util.jobsInterlocks([cvs, pkg])
        self.assertEqual([], interlocks)


class TestInterlockDB(ZopelessTestCase):
    """Interlock tests that need database access."""

    def testNameInterlock(self):
        """nameInterlock works"""
        import importd.util
        anon = (object(), object())
        inter = importd.util.nameInterlock(sampleData.product_id, anon)
        self.assertEqual(inter, (sampleData.product_name,) + anon)

    def testBuildersInterlocksFeature(self):
        """buildersInterlocks works with sample data"""
        import importd.util
        from canonical.launchpad.database import SourcePackage, \
                SourcePackageRelease, DistroRelease
        from importd.Job import CopyJob
        from canonical.lp.dbschema import ImportStatus
        pkgid = sampleData.package_import_id
        drid = sampleData.package_import_distrorelease_id
        spr = SourcePackageRelease.get(pkgid)
        dr = DistroRelease.get(drid)
        pkgjob = CopyJob().from_sourcepackagerelease(spr, dr)
        jobs = importd.util.jobsFromDB("slave_home",
                                       "archive_mirror_dir",
                                       [ImportStatus.PROCESSING])
        jobs.append(pkgjob)
        builders = []
        interlocks = importd.util.jobsInterlocks(jobs)
        self.assertEqual(1, len(interlocks))
        interlock = interlocks[0]
        self.assertEqual(sampleData.product_name, interlock[0])
        self.assertEqual([1, 1], map(len, interlock[1:]))
        self.assertEqual(sampleData.cvs_job_name, interlock[1][0])
        self.assertEqual(sampleData.package_job_name, interlock[2][0])


class MockBuild(object):
    pass


class TestImpordDBuild(ZopelessTestCase):

    def setUp(self):
        ZopelessTestCase.setUp(self)
        self._impl = None

    def tearDown(self):
        from canonical.lp.dbschema import ImportStatus
        self.series().dateautotested = None
        self.series().importstatus = ImportStatus.PROCESSING
        self.txnManager().commit()
        ZopelessTestCase.tearDown(self)

    def mockBuild(self):
        build = MockBuild()
        build.importDJob = MockJob()
        build.importDJob.seriesID = sampleData.cvs_job_id
        build.importDJob.RCS = 'cvs'
        return build

    def implementor(self):
        import importd.util
        if self._impl is None:
            build = self.mockBuild()
            self._impl = importd.util.ImportDBImplementor(build)
        return self._impl

    def series(self):
        return self.implementor().getSeries()

    def txnManager(self):
        import importd.util
        return importd.util.getTxnManager()

    def testSetDateStarted(self):
        """ImportDBImplementor.setDateStarted changes datestarted."""
        self.series().datestarted = None
        self.implementor().setDateStarted()
        self.assert_(self.series().datestarted is not None)

    def testSetDateFinished(self):
        """ImportDBImplementor.setDateFinished changes datefinished."""
        self.series().datefinished = None
        self.implementor().setDateFinished()
        self.assert_(self.series().datefinished is not None)

    def testSetAutotestedSuccess(self):
        """ImportDBImplementor.setAutotested works on success."""
        from canonical.lp.dbschema import ImportStatus
        self.series().dateautotested = None
        self.implementor().setAutotested(True)
        self.assert_(self.series().dateautotested is not None)
        self.assertEqual(self.series().importstatus, ImportStatus.AUTOTESTED)

    def testSetAutotestedFailure(self):
        """ImportDBImplementor.setAutotested works on failure."""
        from canonical.lp.dbschema import ImportStatus
        self.series().dateautotested = None
        self.implementor().setAutotested(False)
        self.assert_(self.series().dateautotested is None)
        self.assertEqual(self.series().importstatus, ImportStatus.TESTFAILED)

    def testStartBuild(self):
        """ImportDBImplementor.startBuild sets series and commits."""
        self.txnManager().begin()
        self.series().datestarted = None
        self.txnManager().commit()
        self.implementor().startBuild()
        # spiv who is reviewing this suggested this XXX abstraction
        # violation. RBC 20050608
        from canonical.database.sqlbase import SQLBase
        if SQLBase._connection is not None:
            self.txnManager().abort() # discard uncommitted changes
        self.assert_(self.series().datestarted is not None)

    def testBuildFinished(self):
        """ImportDBImplementor.buildFinished sets series and commits."""
        from canonical.lp.dbschema import ImportStatus
        self.txnManager().begin()
        self.series().datefinished = None
        self.series().importstatus = ImportStatus.TESTING
        self.txnManager().commit()
        self.implementor().buildFinished(True)
        # spiv who is reviewing this suggested this XXX abstraction
        # violation. RBC 20050608
        from canonical.database.sqlbase import SQLBase
        if SQLBase._connection is not None:
            self.txnManager().abort() # discard uncommitted changes
        self.assert_(self.series().datefinished is not None)
        self.assertEqual(self.series().importstatus, ImportStatus.AUTOTESTED)



def test_suite():
    '''return all the tests in this module'''
    import unittest
    from tests.TestUtil import TestSuite
    loader=unittest.TestLoader()
    loader.suiteClass=TestSuite
    return loader.loadTestsFromName(__name__)

def main(argv):
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    runner=unittest.TextTestRunner(verbosity=2)
    #threadTest(lambda: runner.run(suite))
    #if not runner.wasSuccessful(): return 1
    result = runner.run(suite)
    if not result.wasSuccessful(): return 1
    return 0
 
if __name__ == '__main__':
    sys.exit(main(sys.argv))
