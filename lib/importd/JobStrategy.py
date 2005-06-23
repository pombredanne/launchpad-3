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

from canonical.librarian.client import FileDownloadClient

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

    def setupArchiveStuff(self, archive, gpguser):
        """I need refactoring"""
        importerbase=self.aJob.slave_home
        self.baz_make_archives(archive, importerbase, self.aJob.archive_mirror_dir)
        self.baz_setup_signing(archive, importerbase, gpguser)

    def signing_path(self,basename):
        return os.path.expanduser("~/.arch-params/signing/" + basename)

    def signing_open(self, basename):
        return open(self.signing_path(basename), 'w')

    def gpg_path(self, basedir, gpguser, suffix):
        return basedir + "/gpg/" + gpguser + suffix

    def baz_setup_readonly_signing(self, name, basedir, gpguser):
        print >> self.signing_open(name + "-MIRROR"), name
        print >> self.signing_open(name + ".check"), "tla-gpg-check gpg_command=\"gpg --verify-files -q --no-show-notation --batch --no-tty --no-default-keyring --keyring " + self.gpg_path(basedir,gpguser,".pub") +" -\" 2>&1 | grep \"^gpg: Good signature from\" 1>&2"
        print >> self.signing_open(name + "-MIRROR.check"), "tla-gpg-check gpg_command=\"gpg --verify-files -q --no-show-notation --batch --no-tty --no-default-keyring --keyring " + self.gpg_path(basedir,gpguser,".pub") +" -\" 2>&1 | grep \"^gpg: Good signature from\" 1>&2"

    def baz_setup_signing(self, name, basedir, gpguser):
        self.baz_setup_readonly_signing(name, basedir, gpguser)
        print >> self.signing_open(name), "gpg --clearsign --no-default-keyring --keyring " + self.gpg_path(basedir,gpguser,".pub") + " --secret-keyring " + self.gpg_path(basedir, gpguser, ".secret") + " --default-key " + gpguser

    def baz_make_archives(self, name, basedir, mirrordir):
        from pybaz import make_archive, iter_archives, Archive
        archive=Archive(name)
        if not archive.is_registered():
            archive=make_archive(name,os.path.join(basedir, 'archives', name) ,signed=True)
        if not Archive(name + '-MIRROR').is_registered():
            archive.make_mirror(name + '-MIRROR', os.path.join(mirrordir, name),
                                        signed=True, listing=True)

    def baz_make_mirror(self, name, mirrordir, signed=False):
        from pybaz import make_archive, iter_archives, Archive
        archive=Archive(name)
        mirror = arch.Archive(name + '-MIRROR')
        if not mirror.is_registered():
            mirror.make_mirror(name + '-MIRROR', os.path.join(mirrordir, name),
                               signed=signed, listing=True)


def get(rcs, type=None):
    """I create a JobStrategy that can implement a specific command on
    a specific RCS system"""
    if rcs.lower()=="arch":
        return ArchStrategy().mirror
    if rcs.lower()=="package":
        assert type=='sourcerer', 'Pkg imports must have type "sourcerer"'
        return PackageStrategy().run
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


class PackageStrategy(JobStrategy):
    """I process deb, rpm and related distro package source imports"""

    def archiveName(self):
        '''determine the archive name we should use'''
        return self.aJob.archivename
        
    def run(self, aJob, dir, logger, handler=None):
        """Import a package into arch"""
        assert (aJob is not None)
        assert (dir is not None)
        assert (aJob.sourcepackagerelease is not None)
        assert (aJob.distrorelease is not None)
        self.aJob=aJob
        self.dir=dir
        self.logger=logger

        if os.path.isdir(dir):
            shutil.rmtree(dir, ignore_errors=True)
        os.makedirs(dir)

        # what archive name do you want..
        archive=self.archiveName()
        self.setupArchiveStuff(archive, "arch@canonical.com")

        # RBC 20050216 TODO if any bubblewrap fails, rollback them all.
        # bubblewrap to return listof branches it used when it succeeds.
        
        # make sure that the sourcepackagerelease has not been imported
        # before
        assert aJob.sourcepackagerelease.manifest is None
        
        # make sure that the sourcepackagerelease has files to be imported
        assert len(aJob.sourcepackagerelease.files) > 0
        
        # ok, get ready to fetch stuff from the librarian
        librarian_host = os.environ.get('LB_HOST', 'localhost')
        librarian_port = int(os.environ.get('LB_DPORT', '8000'))

        # fetch all the files for the sourcepackagerelease so we have them
        # locally in dir, with filenames in local_files
        local_files = []
        librarian = FileDownloadClient(librarian_host, librarian_port)
        librarian.logger = logger
        for srcpkgfile in aJob.sourcepackagerelease.files:
            filename = os.path.join(dir, srcpkgfile.libraryfile.filename)
            # we should not overwrite an existing file. we assume the
            # directory is freshly created so the file only exists if its in
            # local_files
            assert filename not in local_files
            f = librarian.getFileByAlias(srcpkgfile.libraryfile)
            lf.open(filename, 'wb')
            lf.write(f.read())
            lf.close()
            local_files.append(filename)
 
        # call the import handler
        if handler is None:
            from sourcerer import bubblewrap
            handler = bubblewrap.run
        handler (local_files, archive, aJob.distrorelease,
                 aJob.sourcepackagerelease, logger, dir,
                 success_func=aJob.RollbackToMirror)


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
        config.args =  ["--strict", "-b", self.job.bazFullPackageVersion(), flags, revisions, bazpath]
        totla.totla(config, logger, config.args, self.sourceTree())

    def Import (self, aJob, dir, logger):
        """import from a concrete type to baz"""
        from pybaz import Archive
        assert (aJob != None)
        assert (dir != None)
        self.job=aJob
        self.aJob=aJob
        self.dir=dir
        self.logger=logger
        self.setupArchiveStuff(aJob.archivename,"arch@canonical.com")
        bazpath=self.getTLADirPath(self.aJob, self.dir)
        if os.path.exists(bazpath):
            shutil.rmtree(bazpath)
        os.makedirs(bazpath)
        arch.init_tree(bazpath, aJob.bazFullPackageVersion(), nested=True)
        newtagging=open(os.path.join(bazpath, '{arch}/=tagging-method.new'), 'w')
        newtagging.write ("# id tagging method\n"
            "#\n"
            "# This determines how 'inventory ids', strings conveying\n"
            "# logical file identity, are computed for each file, directory\n"
            "# and symbolic link.\n"
            "#\n"
            "# The choices are:\n"
            "#\n"
            "# tagline: inventory ids may be set using add-id, or omitted\n"
            "#          (though tree-lint warns about omitted ids), or in\n"
            "#          text files, set in a comment line near the top or\n"
            "#          bottom of the file of a form like '<PUNCT> arch-tag: <STRING>'.\n"
            "#          Renames of files with no id are treated as a combined\n"
            "#          add and delete (e.g., local changes can be lost).\n"
            "#\n"
            "# explicit: ids must be set using add-id.  Files passing the naming\n"
            "#          conventions for source, but lacking add-id ids, are treated\n"
            "#          as unrecognized files (see below).\n"
            "#\n"
            "# names: ids are not used.  All renames are treated as add+delete\n"
            "#\n"
            "# implicit: similar to tagline, but in addition, the id comment\n"
            "#          may be of the form '<PUNCT> <BASENAME> - <STRING>', where\n"
            "#          <BASENAME> is the basename of the file.   This method\n"
            "#          is not recommended, but is retained for backwards\n"
            "#          compatibility.\n"
            "#\n"
            "\n"
            "explicit\n"
            "\n"
            "# disposition of untagged source files\n"
            "#\n"
            "# (NOTE: this option must follow the tagline/explicit/names/implicit\n"
            "# directive.)\n"
            "#\n"
            "# By default, the explicit method treats untagged files matching the naming\n"
            "# conventions for source files as unrecognized and the implicit and tagline\n"
            "# methods treat such untagged files as source.\n"
            "#\n"
            "# You can override those default treatments of untagged files by specifying\n"
            "# which inventory category (see below) should be used for files whose names\n"
            "# suggest they are source but which lack ids.\n"
            "#\n"
            "# This feature may be especially convenient when importing sources that do\n"
            "# not use file naming conventions that can be conveniently described with\n"
            "# the regexps below.\n"
            "#\n"
            "# Uncomment one of these lines as appropriate to override the default:\n"
            "#\n"
            "# untagged-source source\n"
            "untagged-source precious\n"
            "# untagged-source backup\n"
            "# untagged-source junk\n"
            "# untagged-source unrecognized\n"
            "#\n"
            "\n"
            "# naming convention regexps\n"
            "#\n"
            "# For various commands, arch traverses your project trees, categorizing\n"
            "# the files found there.  For example, when importing a project for\n"
            "# the first time, this traversal determines which files are included\n"
            "# in the import.\n"
            "#\n"
            "# The categories of greatest importance are defined in terms of three\n"
            "# questions:\n"
            "#\n"
            "# 1) If arch makes a local copy of this tree, should this file be included\n"
            "#    in the copy?\n"
            "#\n"
            "# 2) Is it generally safe to remove this file based only on how it is named?\n"
            "#    For example, can it be safely clobbered by a new file of the same name?\n"
            "#\n"
            "# 3) Should this file be archived along with the project?  For example,\n"
            "#    should it be included when importing the project for the first time?\n"
            "#\n"
            "# The primary categories are:\n"
            "#\n"
            "# category:      copy locally?       safe to clobber?      archive?\n"
            "#\n"
            "# junk           no                  yes                   no\n"
            "# backup         no                  no                    no\n"
            "# precious       yes                 no                    no\n"
            "# source         yes                 no                    yes\n"
            "#\n"
            "# There are two additional categories, unrelated to those questions:\n"
            "#\n"
            "# excluded -- during a traversal by inventory, this file (and,\n"
            "#             if a directory, its contents) are simply ignored unless the\n"
            "#             --all flag is specified.   This category is usually used to\n"
            "#             omit arch's own control files from a listing.\n"
            "#\n"
            "# unrecognized -- a category for files whose name fits no other pattern.\n"
            "#             Usually, the presence of unrecognized files is treated as an\n"
            "#             error.   You can use the naming conventions to define certain\n"
            "#             names as 'deliberately unrecognized' -- i.e., filenames whose\n"
            "#             presence in a source tree you _want_ to be treated as an error\n"
            "#\n"
            "# The traveral algorithm is described here, along with lines you can edit to\n"
            "# customize the naming conventions.\n"
            "#\n"
            "# Starting at '.' within a project tree (usually at the root of the\n"
            "# project tree) consider each filename in that directory.\n"
            "#\n"
            "# The files '.' and '..' are simply ignored.\n"
            "#\n"
            "# Files containing 'illegal characters' are characterized as unrecognized.\n"
            "# If they are directories, traversal does _not_ descend into those directories.\n"
            "# Currently, the illegal characters are *, ?, [, ], \, space, and tab.\n"
            "# (The set of illegal characters may shrink in future releases.)\n"
            "#\n"
            "# In an interactive call to inventory _without_ the --all flag,\n"
            "# names are next compared to the exclude regexp defined here.  Those that\n"
            "# are ignored and not descended below.  (Most arch operations performing\n"
            "# traversals internally, e.g. import, do not use this pattern\n"
            "# and skip this step of the algorithm.\n"
            "#\n"
            "\n"
            "exclude ^(.arch-ids|\{arch\}|\.arch-inventory)$\n"
            "\n"
            "# If the file has a name that begins with '++', it is categorized as\n"
            "# _precious_.  Names of this form are hard-wired and reserved for use by arch\n"
            "# itself.  Traversal does not descend into precious directories, but when a\n"
            "# precious directory is copied, its contents are recursively copied.\n"
            "#\n"
            "# Files and directories that reach this stage and which arch recognizes as its\n"
            "# own control files are classified at this step as source.   Traversal _does_\n"
            "# descend into source directories.\n"
            "#\n"
            "# If the file has a name that begins with ',,', it is categorized as _junk_.\n"
            "# Names of this form are hard-wired and reserved for use by arch and other tools,\n"
            "# and arch may clobber such files without warning.  In a project tree, when no \n"
            "# arch commands are running, it is safe for users to delete any ',,' files. \n"
            "# Although the general rule for junk files is that arch is free to clobber them,\n"
            "# in fact, arch will only ever clobber files starting with ',,'.\n"
            "#\n"
            "# Traversal does not descend into junk directories.\n"
            "#\n"
            "# For your convenience, at this step of the traversal, you can classify\n"
            "# additional files as junk or precious:\n"
            "#\n"
            "\n"
            "junk ^(,.*)$\n"
            "\n"
            "precious ^(\+.*|\.#ckpts-lock|=build\.*|=install\.*)$\n"
            "\n"
            "# Files matching the following regexp are classified as backup files, and\n"
            "# traversal does not descend into backup directories:\n"
            "#\n"
            "\n"
            "backup ^$\n"
            "\n"
            "# If you want to force certain filenames to be treated as errors when present,\n"
            "# you can add them to the regexp for deliberately unrecognized files.  Traversal\n"
            "# does not descend into unrecognized directories.\n"
            "\n"
            "unrecognized ^$\n"
            "\n"
            "# Files which match the following pattern are treated as source files.\n"
            "# Traversal _does_ descend into source directories:\n"
            "\n"
            "source .\n"
            "\n"
            "# Any files not classified by the above rules are classified as unrecognized.\n"
            "# Traversal does not descend into unrecognized directories.\n"
            "\n")

        for rule in aJob.tagging_rules:
            newtagging.write(rule + "\n")
        newtagging.close()
        os.rename(os.path.join(bazpath, '{arch}/=tagging-method.new'), os.path.join(bazpath, '{arch}/=tagging-method'))
        arch.Version(aJob.bazFullPackageVersion()).setup()
        self.runtobaz("-Si", "%s.1" % aJob.sourceBranch(), bazpath, logger)
        # for svn, the next revision is not 1::, rather lastCommit::
        aVersion=Version(aJob.bazFullPackageVersion())
        lastCommit = cscvs.arch.findLastCSCVSCommit(aVersion)
        self.runtobaz("-SCc", "%s::" % lastCommit, bazpath, logger)
        shutil.rmtree(bazpath)
        
    def sync(self, aJob, dir, logger):
        """sync from a concrete type to baz"""
        assert aJob is not None
        assert dir is not None
        self.job=aJob
        self.aJob=aJob
        self.logger=logger
        self.dir=dir
        aVersion=Version(self.job.bazFullPackageVersion())
        if self.job.mirrorNotEmpty(aVersion):
            self.job.RollbackToMirror(aVersion)
        lastCommit = cscvs.arch.findLastCSCVSCommit(aVersion)
        if lastCommit is None:
            raise RuntimeError ("No Commits have occured, cannot perform incremental tobaz")
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
        """ensure that there is a cvs checkout in the working dir/cvsworking, with a fresh cache"""
        import CVS
        self.job=aJob
        repository=self.repository()
        path=self.getCVSDirPath(aJob,dir)
        if os.access(path, os.F_OK):
            assert (not self._tree)
            self._tree=CVS.tree(path)
            self._tree.logger(self.logger)
            if self._tree.repository() != self.repo():
                self.logger.error('Current checkout is stale - wrong repository, regetting. Was %s, should be %s', self._tree.repository().root, self.repo().root)
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
            catalog = self._tree.catalog(False, False, None, 168, "update", tlaBranchName=self.job.bazFullPackageVersion())
            branches = catalog.branches
            branches.sort()
            for branch in branches:
                self.logger.critical("%s revs on %s" , len(catalog.getBranch(branch)), branch)
                    
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
            if os.access(path, os.F_OK):
                pass
                #argv=["-SBu"]
            else:      
                #argv=["-SBb"]
                try:
                    self.logger.debug("getting from SVN: %s %s" % (repository, self.aJob.module))
                    client=pysvn.Client()
                    client.checkout(repository, path)
                except Exception, foo: #don't leave partial checkouts around
                    if os.access(path, os.F_OK):
                        shutil.rmtree(path)
                    raise foo
        
            self.sourceDirectory = path
        return self.sourceDirectory
        
    def sourceTree(self):
        """return the svn tree we are using"""
        if self._tree is None:
            self._tree = SCM.tree(self.sourceDir())
        return self._tree

class ArchStrategy(JobStrategy):

    def mirror(self, aJob, dir, logger):
        arch_source_url = aJob.archsourceurl
        arch_source_archive = aJob.archsourcearchive
        arch_source_gpg = aJob.archsourcegpg
        archive_mirror_dir = aJob.archive_mirror_dir
        source = arch.Archive(arch_source_archive)
        importerbase = aJob.slave_home
        if source.is_registered(): source.unregister()
        source = arch.register_archive(None, arch_source_url)
        if source.name != arch_source_archive:
            raise ValueError, "Archive name mismatch: name=%s url=%s" \
                  % (arch_source_archive, arch_source_url)
        if arch_source_gpg:
            self.baz_setup_readonly_signing(
                arch_source_archive, importerbase, arch_source_gpg)
        mirror = arch.Archive(arch_source_archive + '-MIRROR')
        if not mirror.is_registered():
            source.make_mirror(
                mirror.name, archive_mirror_dir, bool(arch_source_gpg))
        source.mirror()


