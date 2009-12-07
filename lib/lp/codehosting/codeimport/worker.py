# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The code import worker. This imports code from foreign repositories."""

__metaclass__ = type
__all__ = [
    'BazaarBranchStore',
    'BzrSvnImportWorker',
    'CSCVSImportWorker',
    'CodeImportSourceDetails',
    'ForeignTreeStore',
    'GitImportWorker',
    'ImportWorker',
    'get_default_bazaar_branch_store',
    ]


import os
import shutil

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir, BzrDirFormat
from bzrlib.transport import get_transport
from bzrlib.errors import NoSuchFile, NotBranchError
import bzrlib.ui
from bzrlib.urlutils import join as urljoin
from bzrlib.upgrade import upgrade

from canonical.cachedproperty import cachedproperty
from lp.codehosting.bzrutils import ensure_base
from lp.codehosting.codeimport.foreigntree import (
    CVSWorkingTree, SubversionWorkingTree)
from lp.codehosting.codeimport.tarball import (
    create_tarball, extract_tarball)
from lp.codehosting.codeimport.uifactory import LoggingUIFactory
from canonical.config import config
from lp.code.enums import RevisionControlSystems

from cscvs.cmds import totla
import cscvs
import CVS
import SCM


class BazaarBranchStore:
    """A place where Bazaar branches of code imports are kept."""

    def __init__(self, transport):
        """Construct a Bazaar branch store based at `transport`."""
        self.transport = transport

    def _getMirrorURL(self, db_branch_id):
        """Return the URL that `db_branch` is stored at."""
        return urljoin(self.transport.base, '%08x' % db_branch_id)

    def pull(self, db_branch_id, target_path, required_format):
        """Pull down the Bazaar branch for `code_import` to `target_path`.

        :return: A Bazaar working tree for the branch of `code_import`.
        """
        remote_url = self._getMirrorURL(db_branch_id)
        try:
            bzr_dir = BzrDir.open(remote_url)
        except NotBranchError:
            return BzrDir.create_standalone_workingtree(
                target_path, required_format)
        # XXX Tim Penhey 2009-09-18 bug 432217 Automatic upgrade of import
        # branches disabled.  Need an orderly upgrade process.
        if False and bzr_dir.needs_format_conversion(format=required_format):
            try:
                bzr_dir.root_transport.delete_tree('backup.bzr')
            except NoSuchFile:
                pass
            upgrade(remote_url, required_format)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def push(self, db_branch_id, bzr_tree, required_format):
        """Push up `bzr_tree` as the Bazaar branch for `code_import`."""
        ensure_base(self.transport)
        branch_from = bzr_tree.branch
        target_url = self._getMirrorURL(db_branch_id)
        try:
            branch_to = Branch.open(target_url)
        except NotBranchError:
            branch_to = BzrDir.create_branch_and_repo(
                target_url, format=required_format)
        branch_to.pull(branch_from, overwrite=True)


def get_default_bazaar_branch_store():
    """Return the default `BazaarBranchStore`."""
    return BazaarBranchStore(
        get_transport(config.codeimport.bazaar_branch_store))


class CodeImportSourceDetails:
    """The information needed to process an import.

    As the worker doesn't talk to the database, we don't use
    `CodeImport` objects for this.

    The 'fromArguments' and 'asArguments' methods convert to and from a form
    of the information suitable for passing around on executables' command
    lines.

    :ivar branch_id: The id of the branch associated to this code import, used
        for locating the existing import and the foreign tree.
    :ivar rcstype: 'svn' or 'cvs' as appropriate.
    :ivar svn_branch_url: The branch URL if rcstype in ['svn', 'bzr-svn'],
        None otherwise.
    :ivar cvs_root: The $CVSROOT if rcstype == 'cvs', None otherwise.
    :ivar cvs_module: The CVS module if rcstype == 'cvs', None otherwise.
    :ivar git_repo_url: The URL of the git repo, if rcstype == 'git', None,
        otherwise.
    """

    def __init__(self, branch_id, rcstype, svn_branch_url=None, cvs_root=None,
                 cvs_module=None, git_repo_url=None):
        self.branch_id = branch_id
        self.rcstype = rcstype
        self.svn_branch_url = svn_branch_url
        self.cvs_root = cvs_root
        self.cvs_module = cvs_module
        self.git_repo_url = git_repo_url

    @classmethod
    def fromArguments(cls, arguments):
        """Convert command line-style arguments to an instance."""
        branch_id = int(arguments.pop(0))
        rcstype = arguments.pop(0)
        if rcstype in ['svn', 'bzr-svn']:
            [svn_branch_url] = arguments
            cvs_root = cvs_module = git_repo_url = None
        elif rcstype == 'cvs':
            svn_branch_url = git_repo_url = None
            [cvs_root, cvs_module] = arguments
        elif rcstype == 'git':
            cvs_root = cvs_module = svn_branch_url = None
            [git_repo_url] = arguments
        else:
            raise AssertionError("Unknown rcstype %r." % rcstype)
        return cls(
            branch_id, rcstype, svn_branch_url, cvs_root, cvs_module,
            git_repo_url)

    @classmethod
    def fromCodeImport(cls, code_import):
        """Convert a `CodeImport` to an instance."""
        if code_import.rcs_type == RevisionControlSystems.SVN:
            rcstype = 'svn'
            svn_branch_url = str(code_import.svn_branch_url)
            cvs_root = cvs_module = git_repo_url = None
        elif code_import.rcs_type == RevisionControlSystems.BZR_SVN:
            rcstype = 'bzr-svn'
            svn_branch_url = str(code_import.svn_branch_url)
            cvs_root = cvs_module = git_repo_url = None
        elif code_import.rcs_type == RevisionControlSystems.CVS:
            rcstype = 'cvs'
            svn_branch_url = git_repo_url = None
            cvs_root = str(code_import.cvs_root)
            cvs_module = str(code_import.cvs_module)
        elif code_import.rcs_type == RevisionControlSystems.GIT:
            rcstype = 'git'
            svn_branch_url = cvs_root = cvs_module = None
            git_repo_url = str(code_import.git_repo_url)
        else:
            raise AssertionError("Unknown rcstype %r." % code_import.rcs_type)
        return cls(
            code_import.branch.id, rcstype, svn_branch_url,
            cvs_root, cvs_module, git_repo_url)

    def asArguments(self):
        """Return a list of arguments suitable for passing to a child process.
        """
        result = [str(self.branch_id), self.rcstype]
        if self.rcstype in ['svn', 'bzr-svn']:
            result.append(self.svn_branch_url)
        elif self.rcstype == 'cvs':
            result.append(self.cvs_root)
            result.append(self.cvs_module)
        elif self.rcstype == 'git':
            result.append(self.git_repo_url)
        else:
            raise AssertionError("Unknown rcstype %r." % self.rcstype)
        return result


class ImportDataStore:
    """A store for data associated with an import.

    Import workers can store and retreive files into and from the store using
    `put()` and `fetch()`.

    So this store can find files stored by previous versions of this code, the
    files are stored at ``<BRANCH ID IN HEX>.<EXT>`` where BRANCH ID comes
    from the CodeImportSourceDetails used to construct the instance and EXT
    comes from the local name passed to `put` or `fetch`.
    """

    def __init__(self, transport, source_details):
        """Initialize an `ImportDataStore`.

        :param transport: The transport files will be stored on.
        :param source_details: The `CodeImportSourceDetails` object, used to
            know where to store files on the remote transport.
        """
        self.source_details = source_details
        self._transport = transport
        self._branch_id = source_details.branch_id

    def _getRemoteName(self, local_name):
        """Convert `local_name` to the name used to store a file.

        The algorithm is a little stupid for historical reasons: we chop off
        the extension and stick that on the end of the branch id from the
        source_details we were constructed with, in hex padded to 8
        characters.  For example 'tree.tar.gz' might become '0000a23d.tar.gz'
        or 'git.db' might become '00003e4.db'.

        :param local_name: The local name of the file to be stored.
        :return: The name to store the file as on the remote transport.
        """
        if '/' in local_name:
            raise AssertionError("local_name must be a name, not a path")
        dot_index = local_name.index('.')
        if dot_index < 0:
            raise AssertionError("local_name must have an extension.")
        ext = local_name[dot_index:]
        return '%08x%s' % (self._branch_id, ext)

    def fetch(self, filename, dest_transport=None):
        """Retrieve `filename` from the store.

        :param filename: The name of the file to retrieve (must be a filename,
            not a path).
        :param dest_transport: The transport to retrieve the file to,
            defaulting to ``get_transport('.')``.
        :return: A boolean, true if the file was found and retrieved, false
            otherwise.
        """
        if dest_transport is None:
            dest_transport = get_transport('.')
        remote_name = self._getRemoteName(filename)
        if self._transport.has(remote_name):
            dest_transport.put_file(
                filename, self._transport.get(remote_name))
            return True
        else:
            return False

    def put(self, filename, source_transport=None):
        """Put `filename` into the store.

        :param filename: The name of the file to store (must be a filename,
            not a path).
        :param source_transport: The transport to look for the file on,
            defaulting to ``get_transport('.')``.
        """
        if source_transport is None:
            source_transport = get_transport('.')
        remote_name = self._getRemoteName(filename)
        local_file = source_transport.get(filename)
        ensure_base(self._transport)
        try:
            self._transport.put_file(remote_name, local_file)
        finally:
            local_file.close()


class ForeignTreeStore:
    """Manages retrieving and storing foreign working trees.

    The code import system stores tarballs of CVS and SVN working trees on
    another system. The tarballs are kept in predictable locations based on
    the ID of the branch associated to the `CodeImport`.

    The tarballs are all kept in one directory. The filename of a tarball is
    XXXXXXXX.tar.gz, where 'XXXXXXXX' is the ID of the `CodeImport`'s branch
    in hex.
    """

    def __init__(self, import_data_store):
        """Construct a `ForeignTreeStore`.

        :param transport: A writable transport that points to the base
            directory where the tarballs are stored.
        :ptype transport: `bzrlib.transport.Transport`.
        """
        self.import_data_store = import_data_store

    def _getForeignTree(self, target_path):
        """Return a foreign tree object for `target_path`."""
        source_details = self.import_data_store.source_details
        if source_details.rcstype == 'svn':
            return SubversionWorkingTree(
                source_details.svn_branch_url, str(target_path))
        elif source_details.rcstype == 'cvs':
            return CVSWorkingTree(
                source_details.cvs_root, source_details.cvs_module,
                target_path)
        else:
            raise AssertionError(
                "unknown RCS type: %r" % source_details.rcstype)

    def archive(self, foreign_tree):
        """Archive the foreign tree."""
        local_name = 'foreign_tree.tar.gz'
        create_tarball(foreign_tree.local_path, 'foreign_tree.tar.gz')
        self.import_data_store.put(local_name)

    def fetch(self, target_path):
        """Fetch the foreign branch for `source_details` to `target_path`.

        If there is no tarball archived for `source_details`, then try to
        download (i.e. checkout) the foreign tree from its source repository,
        generally on a third party server.
        """
        try:
            return self.fetchFromArchive(target_path)
        except NoSuchFile:
            return self.fetchFromSource(target_path)

    def fetchFromSource(self, target_path):
        """Fetch the foreign tree for `source_details` to `target_path`."""
        branch = self._getForeignTree(target_path)
        branch.checkout()
        return branch

    def fetchFromArchive(self, target_path):
        """Fetch the foreign tree for `source_details` from the archive."""
        local_name = 'foreign_tree.tar.gz'
        if not self.import_data_store.fetch(local_name):
            raise NoSuchFile(local_name)
        extract_tarball(local_name, target_path)
        tree = self._getForeignTree(target_path)
        tree.update()
        return tree


class ImportWorker:
    """Oversees the actual work of a code import."""

    # Where the Bazaar working tree will be stored.
    BZR_WORKING_TREE_PATH = 'bzr_working_tree'

    required_format = BzrDirFormat.get_default_format()

    def __init__(self, source_details, import_data_transport,
                 bazaar_branch_store, logger):
        """Construct an `ImportWorker`.

        :param source_details: A `CodeImportSourceDetails` object.
        :param bazaar_branch_store: A `BazaarBranchStore`. The import worker
            uses this to fetch and store the Bazaar branches that are created
            and updated during the import process.
        :param logger: A `Logger` to pass to cscvs.
        """
        self.source_details = source_details
        self.bazaar_branch_store = bazaar_branch_store
        self.import_data_store = ImportDataStore(
            import_data_transport, self.source_details)
        self._logger = logger

    def getBazaarWorkingTree(self):
        """Return the Bazaar `WorkingTree` that we are importing into."""
        if os.path.isdir(self.BZR_WORKING_TREE_PATH):
            shutil.rmtree(self.BZR_WORKING_TREE_PATH)
        return self.bazaar_branch_store.pull(
            self.source_details.branch_id, self.BZR_WORKING_TREE_PATH,
            self.required_format)

    def pushBazaarWorkingTree(self, bazaar_tree):
        """Push the updated Bazaar working tree to the server."""
        self.bazaar_branch_store.push(
            self.source_details.branch_id, bazaar_tree, self.required_format)

    def getWorkingDirectory(self):
        """The directory we should change to and store all scratch files in.
        """
        base = config.codeimportworker.working_directory_root
        dirname = 'worker-for-branch-%s' % self.source_details.branch_id
        return os.path.join(base, dirname)

    def run(self):
        """Run the code import job.

        This is the primary public interface to the `ImportWorker`. This
        method:

         1. Retrieves an up-to-date foreign tree to import.
         2. Gets the Bazaar branch to import into.
         3. Imports the foreign tree into the Bazaar branch. If we've
            already imported this before, we synchronize the imported Bazaar
            branch with the latest changes to the foreign tree.
         4. Publishes the newly-updated Bazaar branch, making it available to
            Launchpad users.
         5. Archives the foreign tree, so that we can update it quickly next
            time.
        """
        working_directory = self.getWorkingDirectory()
        if os.path.exists(working_directory):
            shutil.rmtree(working_directory)
        os.makedirs(working_directory)
        saved_pwd = os.getcwd()
        os.chdir(working_directory)
        try:
            self._doImport()
        finally:
            shutil.rmtree(working_directory)
            os.chdir(saved_pwd)

    def _doImport(self):
        raise NotImplementedError()


class CSCVSImportWorker(ImportWorker):
    """An ImportWorker for imports that use CSCVS.

    As well as invoking cscvs to do the import, this class also needs to
    manage a foreign working tree.
    """

    # Where the foreign working tree will be stored.
    FOREIGN_WORKING_TREE_PATH = 'foreign_working_tree'

    @cachedproperty
    def foreign_tree_store(self):
        return ForeignTreeStore(self.import_data_store)

    def getForeignTree(self):
        """Return the foreign branch object that we are importing from.

        :return: A `SubversionWorkingTree` or a `CVSWorkingTree`.
        """
        if os.path.isdir(self.FOREIGN_WORKING_TREE_PATH):
            shutil.rmtree(self.FOREIGN_WORKING_TREE_PATH)
        os.mkdir(self.FOREIGN_WORKING_TREE_PATH)
        return self.foreign_tree_store.fetch(self.FOREIGN_WORKING_TREE_PATH)

    def importToBazaar(self, foreign_tree, bazaar_tree):
        """Actually import `foreign_tree` into `bazaar_tree`.

        :param foreign_tree: A `SubversionWorkingTree` or a `CVSWorkingTree`.
        :param bazaar_tree: A `bzrlib.workingtree.WorkingTree`.
        """
        foreign_directory = foreign_tree.local_path
        bzr_directory = str(bazaar_tree.basedir)

        scm_branch = SCM.branch(bzr_directory)
        last_commit = cscvs.findLastCscvsCommit(scm_branch)

        # If branch in `bazaar_tree` doesn't have any identifiable CSCVS
        # revisions, CSCVS "initialises" the branch.
        if last_commit is None:
            self._runToBaz(
                foreign_directory, "-SI", "MAIN.1", bzr_directory)

        # Now we synchronise the branch, that is, import all new revisions
        # from the foreign branch into the Bazaar branch. If we've just
        # initialized the Bazaar branch, then this means we import *all*
        # revisions.
        last_commit = cscvs.findLastCscvsCommit(scm_branch)
        self._runToBaz(
            foreign_directory, "-SC", "%s::" % last_commit, bzr_directory)

    def _runToBaz(self, source_dir, flags, revisions, bazpath):
        """Actually run the CSCVS utility that imports revisions.

        :param source_dir: The directory containing the foreign working tree
            that we are importing from.
        :param flags: Flags to pass to `totla.totla`.
        :param revisions: The revisions to import.
        :param bazpath: The directory containing the Bazaar working tree that
            we are importing into.
        """
        # XXX: JonathanLange 2008-02-08: We need better documentation for
        # `flags` and `revisions`.
        config = CVS.Config(source_dir)
        config.args = ["--strict", "-b", bazpath,
                       flags, revisions, bazpath]
        totla.totla(config, self._logger, config.args, SCM.tree(source_dir))

    def _doImport(self):
        foreign_tree = self.getForeignTree()
        bazaar_tree = self.getBazaarWorkingTree()
        self.importToBazaar(foreign_tree, bazaar_tree)
        self.pushBazaarWorkingTree(bazaar_tree)
        self.foreign_tree_store.archive(foreign_tree)


class PullingImportWorker(ImportWorker):
    """An import worker for imports that can be done by a bzr plugin.

    Subclasses need to implement `pull_url` and `format_classes`.
    """
    @property
    def pull_url(self):
        """Return the URL that should be pulled from."""
        raise NotImplementedError

    @property
    def format_classes(self):
        """The format classes that should be tried for this import."""
        raise NotImplementedError

    def _doImport(self):
        bazaar_tree = self.getBazaarWorkingTree()
        self.bazaar_branch_store.push(
            self.source_details.branch_id, bazaar_tree, self.required_format)
        saved_factory = bzrlib.ui.ui_factory
        bzrlib.ui.ui_factory = LoggingUIFactory(
            writer=lambda m: self._logger.info('%s', m))
        try:
            transport = get_transport(self.pull_url)
            for format_class in self.format_classes:
                try:
                    format = format_class.probe_transport(transport)
                    break
                except NotBranchError:
                    pass
            else:
                raise NotBranchError(self.pull_url)
            foreign_branch = format.open(transport).open_branch()
            bazaar_tree.branch.pull(foreign_branch, overwrite=True)
        finally:
            bzrlib.ui.ui_factory = saved_factory
        self.pushBazaarWorkingTree(bazaar_tree)


class GitImportWorker(PullingImportWorker):
    """An import worker for Git imports.

    The only behaviour we add is preserving the 'git.db' shamap between runs.
    """

    @property
    def pull_url(self):
        """See `PullingImportWorker.pull_url`."""
        return self.source_details.git_repo_url

    @property
    def format_classes(self):
        """See `PullingImportWorker.opening_format`."""
        # We only return LocalGitBzrDirFormat for tests.
        from bzrlib.plugins.git import (
            LocalGitBzrDirFormat, RemoteGitBzrDirFormat)
        return [LocalGitBzrDirFormat, RemoteGitBzrDirFormat]

    def getBazaarWorkingTree(self):
        """See `ImportWorker.getBazaarWorkingTree`.

        In addition to the superclass' behaviour, we retrieve the 'git.db'
        shamap from the import data store and put it where bzr-git will find
        it in the Bazaar tree, that is at '.bzr/repository/git.db'.
        """
        tree = PullingImportWorker.getBazaarWorkingTree(self)
        self.import_data_store.fetch(
            'git.db', tree.branch.repository._transport)
        return tree

    def pushBazaarWorkingTree(self, bazaar_tree):
        """See `ImportWorker.pushBazaarWorkingTree`.

        In addition to the superclass' behaviour, we store the 'git.db' shamap
        that bzr-git will have created at .bzr/repository/bzr.git into the
        import data store.
        """
        PullingImportWorker.pushBazaarWorkingTree(self, bazaar_tree)
        self.import_data_store.put(
            'git.db', bazaar_tree.branch.repository._transport)


class BzrSvnImportWorker(PullingImportWorker):
    """An import worker for importing Subversion via bzr-svn."""

    @property
    def pull_url(self):
        """See `PullingImportWorker.pull_url`."""
        return self.source_details.svn_branch_url

    @property
    def format_classes(self):
        """See `PullingImportWorker.opening_format`."""
        from bzrlib.plugins.svn.format import SvnRemoteFormat
        return [SvnRemoteFormat]
