# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
# Authors: Robert Collins <robertc@robertcollins.net>
#          David Allouche <david@allouche.net>

"""Strategy classes for importd jobs."""

__metaclass__ = type


import os
import shutil
import subprocess
import sys

import CVS
import cscvs
import SCM

from canonical.launchpad.webapp.uri import URI


class ImportSanityError(Exception):
    """Raised when an import fails sanity checks."""


class JobStrategy:
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

    def runtobaz(self, flags, revisions, bazpath, logger):
        from cscvs.cmds import totla
        import CVS
        config=CVS.Config(self.sourceDir())
        config.args =  ["--strict", "-b", self.job.targetBranchName(),
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
        self._checkSanity()
        target_manager = aJob.makeTargetManager()
        working_dir = self.getWorkingDir(aJob, dir)
        target_path = target_manager.createImportTarget(working_dir)
        # Option -I here to do a full-tree import for the first revision.
        # No option -C here because the working tree is not at revision 1.
        self.runtobaz("-SI", "%s.1" % aJob.branchfrom, target_path, logger)
        # WARNING: Do not use the "1::" syntax for the revision range, because
        # the svn revision range parser is not stable. If the svn branch to
        # import was created at revision 42, the previous command will produce
        # a commit with a cscvs id of "MAIN.42". Then the incremental import
        # must start on revision 43. -- David Allouche 2006-10-31
        self._importIncrementally(target_path)

    def _checkSanity(self):
        """Run sanity checks to avoid putting excessive load on server.

        By default do no check. Subclasses may override this. If the import is
        deemed unsafe, this method must raise ImportSanityError.
        """

    def sync(self, aJob, dir, logger):
        """sync from a concrete type to baz"""
        assert aJob is not None
        assert dir is not None
        self.job = aJob
        self.aJob = aJob
        self.logger = logger
        self.dir = dir
        working_dir = self.getWorkingDir(aJob, dir)
        target_path = self._getSyncTarget(working_dir)
        self._importIncrementally(target_path)

    def _getSyncTarget(self, working_dir):
        """Retrieve the bzrworking directory when doing a sync.

        This is factored out as a separate method to allow shorting out the
        this functionality and its dependencies when testing sync.

        :param working_dir: path of job's working directory
        :return: path of the bzr working tree to import into
        """
        target_manager = self.job.makeTargetManager()
        target_path = target_manager.getSyncTarget(working_dir)
        return target_path

    def _importIncrementally(self, target_path):
        """Do an incremental import, starting after the last imported revision.

        :param target_path: path of the bzr workingtree to import into
        """
        branch = SCM.branch(self.job.targetBranchName())
        lastCommit = cscvs.findLastCscvsCommit(branch)
        if lastCommit is None:
            raise RuntimeError(
                "The incremental 'tobaz' was not performed because "
                "no cscvs commit was found in the history of the target.")
        self.runtobaz("-SC", "%s::" % lastCommit, target_path, self.logger)

    def sourceDir(self):
        """Get a source directory to work against"""
        raise NotImplementedError("Must be implemented by subclasses")

    def sourceTree(self):
        """Return the CSCVS tree object we are importing from"""
        raise NotImplementedError("Must be implemented by subclasses")


class CVSStrategy(CSCVSStrategy):
    """I belong in a new file!. I am a strategy for performing CVS
    operations in buildbot"""

    def __init__(self):
        CSCVSStrategy.__init__(self)
        self._working_tree_factory = CvsWorkingTree
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
        assert self._tree is None
        self.job=aJob
        repository=self.repository()
        path=self.getCVSDirPath(aJob,dir)
        working_tree = self._working_tree_factory(aJob, path, self.logger)
        if working_tree.cvsTreeExists():
            if working_tree.repositoryHasChanged(self.repo()):
                self.logger.error(
                    "CVS checkout does not have the right repository.")
                working_tree.cvsReCheckOut(self.repo())
            else:
                if working_tree.cvsTreeHasChanges():
                    self.logger.error("CVS checkout has changes.")
                    working_tree.cvsReCheckOut(self.repo())
                else:
                    working_tree.cvsUpdate()
        else:
            working_tree.cvsCheckOut(self.repo())
        working_tree.updateCscvsCache()
        self._tree = working_tree.cscvsCvsTree()
        return path

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


class CvsWorkingTree:

    """Strategy for handling a CVS working tree to use as import source.

    This class can be replaced by a stub class for testing CVSStrategy.

    :param job: importd job, containing the cvs repository and module details.
    :param path: path of the cvs tree to create or update
    """

    def __init__(self, job, path, logger):
        self._job = job
        self._path = path
        self.logger = logger

    def cvsTreeExists(self):
        """Is this the path of an existing CVS checkout?

        Fail if the path exists but is not a CVS checkout.
        """
        try:
            unused = CVS.tree(self._path)
        except CVS.NotAWorkingTree:
            assert not os.path.exists(self._path), (
                "exists but is not a cvs checkout: %r" % self._path)
            return False
        else:
            return True

    def cscvsCvsTree(self):
        """Creates a CVS.WorkingTree instance for an existing CVS checkout.

        :precondition: `treeExists` is true.
        """
        assert self.cvsTreeExists()
        tree = CVS.tree(self._path)
        tree.logger(self.logger)
        return tree

    def repositoryHasChanged(self, repository):
        """Is the repository of the tree different from the job's?

        :param repository: CVS.Repository instance for the job.
        :precondition: `treeExists` is true.
        """
        tree = self.cscvsCvsTree()
        assert tree.module().name() == self._job.module, (
            'checkout and job point to different modules: %r and %r'
            % (tree.module().name(), self._job.module))
        return tree.repository() != repository

    def updateCscvsCache(self):
        """Initialise or update the cscvs cache.

        :precondition: `treeExists` is true.
        :precondition: the target branch exists for cscvs to scan for imported
            revisions.
        """
        tree = self.cscvsCvsTree()
        one_week = 168 # hours
        catalog = tree.catalog(
            False, False, None, one_week, "update",
            tlaBranchName=self._job.targetBranchName())
        for branch in sorted(catalog.branches):
            self.logger.critical(
                "%s revs on %s", len(catalog.getBranch(branch)), branch)

    def cvsReCheckOut(self, repository):
        """Make a new checkout to replace an existing one.

        Preserve the cscvs cache (that is the CVS/Catalog.sqlite file), and try
        to minimize the window where a failure would cause the cache to be lost

        :param repository; CVS.Repository to check out from.
        :precondition: `treeExists` is true.
        """
        assert self.cvsTreeExists()
        self.logger.error("Re-checking out, old root: %r",
                          self.cscvsCvsTree().repository().root)
        self._tree = None
        catalog_name = 'CVS/Catalog.sqlite'
        path = self._path

        # Check that the catalog exists in the current checkout
        existing_catalog = os.path.join(path, catalog_name)
        assert os.path.exists(existing_catalog), (
            "no existing catalog: %r" % existing_catalog)

        # Make a new clean checkout. Remove it if there is already one: that
        # means that a previous cvsReCheckOut was interrupted before the
        # critical section.
        clean_dir = path + '.clean'
        if os.path.isdir(clean_dir):
            shutil.rmtree(clean_dir)
        self._internalCvsCheckOut(repository, clean_dir)

        # Check that the destination directory for the catalog exists in the
        # new checkout.
        catalog_destination = os.path.dirname(
            os.path.join(clean_dir, catalog_name))
        assert os.path.isdir(catalog_destination), (
            "no catalog destination: %r" % catalog_destination)

        # Check that there is no leftover checkout from a previous run. If
        # there is one, assume that means cvsReCheckout was interrupted after
        # the critical section, and delete it.
        swap_dir = path + '.swap'
        if os.path.isdir(swap_dir):
            shutil.rmtree(swap_dir)

        # Critical section, just renames, to minimize the race window.
        os.rename(path, swap_dir)
        os.rename(clean_dir, path)
        catalog_orig = os.path.join(swap_dir, catalog_name)
        catalog_dest = os.path.join(path, catalog_name)
        os.rename(catalog_orig, catalog_dest)
        # End of critical section

        # Remove the leftover checkout
        shutil.rmtree(swap_dir)

    def _internalCvsCheckOut(self, repository, path):
        module = self._job.module
        self.logger.error("Checking out: %r %r", repository.root, module)
        try:
            tree = repository.get(module, path)
        except:
            # don't leave partial CVS checkouts around
            if os.path.exists(path):
                shutil.rmtree(path)
            raise
        return tree

    def cvsCheckOut(self, repository):
        """Create a CVS checkout to operate on.

        :param repository: CVS.Repository to check out from.
        :param module: CVS module, as a string, to check out from.
        :precondition: `treeExists` is false.
        :postcondition: `treeExists` is true.
        """
        assert not self.cvsTreeExists()
        return self._internalCvsCheckOut(repository, self._path)

    def cvsTreeHasChanges(self):
        """Whether the CVS tree has source changes.

        :precondition: `treeExists` is true.
        """
        tree = self.cscvsCvsTree()
        return tree.has_changes()

    def cvsUpdate(self):
        """Update the CVS tree from the repository.

        :precondition: `treeExists` is true.
        """
        tree = self.cscvsCvsTree()
        return tree.update()



class SVNStrategy(CSCVSStrategy):

    def __init__(self):
        CSCVSStrategy.__init__(self)
        self._svn_url_whitelist = set([
            'http://mg.pov.lt/gtimelog/svn',
            'http://opensvn.csie.org/srb2d6',
            'http://www.eigenheimstrasse.de/svn/josm',
            'http://www2.cs.tum.edu/repos/cup/develop',
            'https://svn.sourceforge.net/svnroot/aptoncd/0.1',
            'https://svn.sourceforge.net/svnroot/comix',
            'https://svn.sourceforge.net/svnroot/jubler/src',
            'https://svn.sourceforge.net/svnroot/listengnome/releases/0.5.x',
            'https://svn.sourceforge.net/svnroot/listengnome/trunk-0.5',
            'https://svn.sourceforge.net/svnroot/scherzo',
            'svn://elgg.net/elgg/devel',
            'svn://mielke.cc/main/brltty',
            'svn://svn.debian.org/gcccvs/branches/sid/gcc-defaults',
            'svn://svn.xara.com/Trunk/XaraLX',
            'svn://svnanon.samba.org/samba/branches/SAMBA_4_0/source/lib/talloc',
            'https://numexp.org/svn/numexp-core',
            'svn://svn.berlios.de/sax/sax-head',
            'http://codespeak.net/svn/pypy/dist',
            ('https://mailman.svn.sourceforge.net/svnroot/mailman/'
             'branches/Release_2_1-maint/mailman'),
            ('https://stage.maemo.org/svn/maemo/projects/haf/branches/'
             'hildon-control-panel/refactoring'),
         ])

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
                    # XXX: David Allouche 2006-01-31 bug=82483: A bug in
                    # pysvn prevents us from ignoring svn:externals. We work
                    # around it by shelling out to svn. When cscvs no longer
                    # uses pysvn, we will use the cscvs API again.
                    arguments = ['svn', 'update', '--ignore-externals']
                    retcode = subprocess.call(arguments, cwd=path)
                    if retcode != 0:
                        sys.exit(retcode)
                else:
                    self.logger.debug("getting from SVN: %s %s",
                        repository, self.aJob.module)
                    client=pysvn.Client()
                    # XXX: David Allouche 2007-01-29:
                    # This should use the cscvs API, but it is currently
                    # hardcoded to only work with repositories on the
                    # filesystem.
                    client.checkout(repository, path, ignore_externals=True)
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

    def _checkSanity(self):
        """Run sanity checks to avoid putting excessive load on server."""
        if self._sanityIsOverridden():
            return
        url = self.job.repository
        if URI(url).path.endswith('/'):
            # Non-canonicalized URLs will cause old unpatched svn servers to
            # crash. We should also canonicalize the URLs to catch duplicates,
            # but this provides belt-and-suspenders to avoid harming remote
            # servers.
            raise ImportSanityError(
                'URL ends with a slash: %s' % url)
        if '/trunk/' in URI(url).ensureSlash().path:
            return
        raise ImportSanityError(
            'URL does not appear to be a SVN trunk: %s' % url)

    def _sanityIsOverridden(self):
        """Whether the sanity check for this import has been overridden.

        At the moment, that just checks that the svn url is in an hardcoded
        while-list. Eventually, that will check for a flag set by the operator
        in the Launchpad web UI.
        """
        if not self.job.autotest:
            # Only perform the sanity check on autotest.
            return True
        return self.job.repository in self._svn_url_whitelist
