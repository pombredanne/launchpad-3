# Copyright (c) 2004 Virtual Development
# Licence to be determined
# Author: Robert Collins <robertc@robertcollins.net>

import os
import shutil
import pybaz as arch
import CVS
import SCM
from pybaz import Version
import cscvs.arch


class JobStrategy(object):
    """I am the base strategy used to do a Job."""

    def download(self, url, target):
        """download a url to a target"""
        import pycurl
        client=pycurl.Curl()
        stream=open(target, 'w')
        #client.setopt(client.PROXY, 'gentoo')
        #client.setopt(client.PROXYPORT, 8080)
        #client.setopt(client.PROXYTYPE, client.PROXYTYPE_HTTP)
        client.setopt(client.FOLLOWLOCATION, True)
        client.setopt(client.SSL_VERIFYPEER, False)
        client.setopt(client.WRITEFUNCTION, stream.write)
        client.setopt(client.NOPROGRESS, True)
        client.setopt(client.URL, str(url))
        client.setopt(client.NETRC, client.NETRC_OPTIONAL)
        client.perform()
        response = client.getinfo(pycurl.RESPONSE_CODE)
        if response >= 300:
            raise RuntimeError, \
                  "Response code %s for %r" % (response, str(url))
        client.close()
        stream.close()


def get(rcs, type=None):
    """I create a JobStrategy that can implement a specific command on
    a specific RCS system"""
    if rcs.lower()=="svn":
        if type=="import":
            return SVNStrategy().Import
        if type=="sync":
            return SVNStrategy().sync
        raise RuntimeError("unknown type for svn import (%s)" % type)
    if rcs.lower()=="cvs":
        if type=="import":
            return CVSStrategy().Import
        if type=="sync":
            return CVSStrategy().sync
        raise KeyError ("Unsupported type value")
    raise KeyError("Unsupported RCS value")


class CSCVSStrategy(JobStrategy):

    def __init__(self):
        self.sourceDirectory=None
        self._tree=None

    def getWorkingDir(self, aJob, dir):
        """create / reuse a working dir for the job to run in"""
        return aJob.getWorkingDir(dir)

    def getTLADirPath(self, aJob, dir):
        """return the baz working dir path"""
        return os.path.join(self.getWorkingDir(aJob,dir), "bazworking")

    def runtobaz(self, flags, revisions, bazpath, logger):
        from cscvs.cmds import totla
        import CVS
        config=CVS.Config(self.sourceDir())
        config.args =  ["--strict", "-b", self.job.bazFullPackageVersion(),
                        flags, revisions, bazpath]
        totla.totla(config, logger, config.args, self.sourceTree())

    def Import (self, aJob, dir, logger):
        """import from a concrete type to baz"""
        assert aJob is not None
        assert dir is not None
        self.job = aJob
        self.aJob = aJob
        self.dir = dir
        self.logger = logger
        archive_manager = aJob.makeArchiveManager()
        archive_manager.createMaster()
        archive_manager.createMirror()
        bazpath = self.getTLADirPath(self.aJob, self.dir)
        if os.path.exists(bazpath):
            shutil.rmtree(bazpath)
        os.makedirs(bazpath)
        arch.init_tree(bazpath, aJob.bazFullPackageVersion(), nested=True)
        newtagging_path = os.path.join(bazpath, '{arch}/=tagging-method.new')
        newtagging = open(newtagging_path, 'w')
        tagging_defaults_path = os.path.join(
            os.path.dirname(__file__), 'id-tagging-defaults')
        tagging_defaults = open(tagging_defaults_path, 'r').read()
        newtagging.write(tagging_defaults)
        for rule in aJob.tagging_rules:
            newtagging.write(rule + "\n")
        newtagging.close()
        taggingmethod_path = os.path.join(bazpath, '{arch}/=tagging-method')
        os.rename(newtagging_path, taggingmethod_path)
        self.runtobaz("-Si", "%s.1" % aJob.branchfrom, bazpath, logger)
        # for svn, the next revision is not 1::, rather lastCommit::
        aVersion = Version(aJob.bazFullPackageVersion())
        lastCommit = cscvs.arch.findLastCSCVSCommit(aVersion)
        self.runtobaz("-SCc", "%s::" % lastCommit, bazpath, logger)
        shutil.rmtree(bazpath)

    def sync(self, aJob, dir, logger):
        """sync from a concrete type to baz"""
        assert aJob is not None
        assert dir is not None
        self.job = aJob
        self.aJob = aJob
        self.logger = logger
        self.dir = dir
        archive_manager = aJob.makeArchiveManager()
        if not archive_manager.mirrorIsEmpty():
            archive_manager.rollbackToMirror()
        aVersion = Version(self.job.bazFullPackageVersion())
        lastCommit = cscvs.arch.findLastCSCVSCommit(aVersion)
        if lastCommit is None:
            raise RuntimeError(
                "No Commits have occured, cannot perform incremental tobaz")
        bazpath=self.getTLADirPath(self.aJob, dir)
        if os.access(bazpath, os.F_OK):
            shutil.rmtree(bazpath)
        try:
            arch.Version(self.job.bazFullPackageVersion()).get(bazpath)
        except (arch.util.ExecProblem, RuntimeError), e:
            logger.critical("Failed to get arch tree '%s'", e)
            raise
        self.runtobaz("-SCc", "%s::" % lastCommit, bazpath, logger)
        shutil.rmtree(bazpath)

    def sourceTree(self):
        """Return the CSCVS tree object we are importing from"""
        raise NotImplementedError("Must be implemented by subclasses")


class CVSStrategy(CSCVSStrategy):
    """I belong in a new file!. I am a strategy for performing CVS
    operations in buildbot"""
    def __init__(self):
        CSCVSStrategy.__init__(self)
        self._repository=None #:pserver.
        self._repo=None       #actual repo instance
    def getCVSDirPath(self, aJob, dir):
        """return the cvs working dir path"""
        return os.path.join(self.getWorkingDir(aJob,dir), "cvsworking")
    def getCVSTempRepoDirPath(self):
        """return the cvs temp local repo dir path"""
        return os.path.join(self.getWorkingDir(self.aJob,self.dir), "cvs_temp_repo")

    def getCVSDir(self, aJob, dir):
        """ensure that there is a cvs checkout in the working dir/cvsworking,
        with a fresh cache"""
        import CVS
        self.job=aJob
        repository=self.repository()
        path=self.getCVSDirPath(aJob,dir)
        if os.access(path, os.F_OK):
            assert (not self._tree)
            self._tree=CVS.tree(path)
            self._tree.logger(self.logger)
            if self._tree.repository() != self.repo():
                self.logger.error(
                    'Current checkout is stale - wrong repository, regetting.'
                    ' Was %s, should be %s', self._tree.repository().root,
                    self.repo().root)
                self._tree=None
                self.checkOut(aJob, path)
            else:
                self._tree.update()
                if self._tree.has_changes():
                    self.logger.error('Local tree has changes, regetting.')
                    self._tree=None
                    self.checkOut(aJob, path)

        else:
            self.checkOut(aJob, path)
        try:
            catalog = self._tree.catalog(
                False, False, None, 168, "update",
                tlaBranchName=self.job.bazFullPackageVersion())
            branches = catalog.branches
            branches.sort()
            for branch in branches:
                self.logger.critical(
                    "%s revs on %s", len(catalog.getBranch(branch)), branch)
        finally:
            pass
        return path

    def checkOut(self, aJob, path):
        shutil.rmtree(path, ignore_errors=True)
        self.logger.debug("getting from CVS: %s %s" % (self.repository(), aJob.module))
        tree = None
        try:
            tree = self.repo().get(aJob.module, path)
        finally:
            if tree is None and os.access(path, os.F_OK):
                # don't leave partial CVS checkouts around
                shutil.rmtree(path)
        self._tree = tree

    def tarFullCopy(self, tar):
        files=iter(tar)
        for file in files:
            if "CVSROOT" in file.name.split("/"):
                return True
        return False
    def tarCVSROOTBase(self,tar):
        files=iter(tar)
        for file in files:
            if "CVSROOT" in file.name.split("/"):
                return file.name.split("/")[0]
        raise RuntimeError("couldn't find CVSROOT prefix dir")
    def tarFirstBase(self, tar):
        file=iter(tar).next()
        return file.name.split("/")[0]

    def makeLocalRepo(self):
        '''create a local repository. This can be useful for both sync and import jobs'''
        os.makedirs(self.getCVSTempRepoDirPath())
        self.download(self.aJob.repository, self.getWorkingDir(self.aJob, self.dir) + "/tarball")
        #self.download(self.aJob.repository, self.getCVSTempRepoDirPath() + "/tarball")
        import tarfile
        tar=tarfile.TarFile.open(self.getWorkingDir(self.aJob, self.dir) + "/tarball", 'r')
        if self.tarFullCopy(tar):
            tarbase=self.tarCVSROOTBase(tar)
            for element in tar:
                tar.extract(element, self.getCVSTempRepoDirPath())
            if not tarbase == 'CVSROOT':
                os.rename(self.getCVSTempRepoDirPath() + '/' + tarbase, self.getWorkingDir(self.aJob, self.dir) + "/tempcvsbase")
                shutil.rmtree(self.getCVSTempRepoDirPath())
                os.rename(self.getWorkingDir(self.aJob, self.dir) + "/tempcvsbase", self.getCVSTempRepoDirPath())
            os.chmod(self.getCVSTempRepoDirPath() + "/CVSROOT/config", 0644)
            print >> open(self.getCVSTempRepoDirPath() + "/CVSROOT/config", 'w'), ""
        else:
            import CVS
            CVS.init(self.getCVSTempRepoDirPath())
            for element in tar:
                tar.extract(element, self.getCVSTempRepoDirPath())
            basedir=self.tarFirstBase(tar)
            if not basedir==self.aJob.module:
                os.rename(self.getCVSTempRepoDirPath() + "/" + basedir, self.getCVSTempRepoDirPath() + "/" + self.aJob.module)
            
        os.unlink(self.getWorkingDir(self.aJob, self.dir) + "/tarball")

    def repository(self):
        """return the string representing the repository to use"""
        if self._repository is None:
            self._repository=self.aJob.repository
            if self.aJob.repositoryIsTar():
                self.makeLocalRepo()
                self._repository=self.getCVSTempRepoDirPath()
        return self._repository

    def sourceDir(self):
        """get a source dir to work against"""
        if self.sourceDirectory is None:
            if self.aJob.repositoryIsRsync():
                raise RuntimeError("not implemented yet")

            self.sourceDirectory = self.getCVSDir(self.aJob, self.dir) 
        return self.sourceDirectory
        
    def sourceTree(self):
        """return the CVS tree we are using"""
        assert self._tree is not None, "getCVSDir should have been run first"
        return self._tree


    def repo(self):
        '''return a CVS Repository instance'''
        if self._repo is None:
            self._repo=CVS.Repository(self.repository(), self.logger)
        return self._repo

class SVNStrategy(CSCVSStrategy):
    def getSVNDirPath(self, aJob, dir):
        """return the cvs working dir path"""
        return os.path.join(self.getWorkingDir(aJob,dir), "svnworking")
    def sourceDir(self):
        """get a source dir to work against"""
        if self.sourceDirectory is None:
            self.svnrepository=self.aJob.repository
            import pysvn
            repository=self.svnrepository
            path=self.getSVNDirPath(self.aJob,self.dir)
            try:
                if os.access(path, os.F_OK):
                    SCM.tree(path).update()
                else:      
                    self.logger.debug("getting from SVN: %s %s",
                                      (repository, self.aJob.module))
                    client=pysvn.Client()
                    client.checkout(repository, path)
            except Exception: # don't leave partial checkouts around
                if os.access(path, os.F_OK):
                    shutil.rmtree(path)
                raise
            self.sourceDirectory = path
        return self.sourceDirectory
        
    def sourceTree(self):
        """return the svn tree we are using"""
        if self._tree is None:
            self._tree = SCM.tree(self.sourceDir())
        return self._tree


