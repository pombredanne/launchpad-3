# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The code import worker. This imports code from foreign repositories."""

__metaclass__ = type
__all__ = [
    'BazaarBranchStore',
    'CodeImportSourceDetails',
    'ForeignTreeStore',
    'ImportWorker',
    'get_default_bazaar_branch_store',
    'get_default_foreign_tree_store']


import os
import shutil
import tempfile

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.transport import get_transport
from bzrlib.errors import NoSuchFile, NotBranchError
from bzrlib.osutils import pumpfile
from bzrlib.urlutils import join as urljoin

from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.codeimport.foreigntree import (
    CVSWorkingTree, SubversionWorkingTree)
from canonical.codehosting.codeimport.tarball import (
    create_tarball, extract_tarball)
from canonical.config import config
from canonical.launchpad.interfaces import RevisionControlSystems

from cscvs.cmds import totla
import cscvs
import CVS
import SCM


class BazaarBranchStore:
    """A place where Bazaar branches of code imports are kept."""

    # This code is intended to replace c.codehosting.codeimport.publish and
    # canonical.codeimport.codeimport.gettarget.

    def __init__(self, transport):
        """Construct a Bazaar branch store based at `transport`."""
        self.transport = transport

    def _getMirrorURL(self, db_branch_id):
        """Return the URL that `db_branch` is stored at."""
        return urljoin(self.transport.base, '%08x' % db_branch_id)

    def pull(self, db_branch_id, target_path):
        """Pull down the Bazaar branch for `code_import` to `target_path`.

        :return: A Bazaar working tree for the branch of `code_import`.
        """
        try:
            bzr_dir = BzrDir.open(self._getMirrorURL(db_branch_id))
        except NotBranchError:
            return BzrDir.create_standalone_workingtree(target_path)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def push(self, db_branch_id, bzr_tree):
        """Push up `bzr_tree` as the Bazaar branch for `code_import`."""
        ensure_base(self.transport)
        branch_from = bzr_tree.branch
        target_url = self._getMirrorURL(db_branch_id)
        try:
            branch_to = Branch.open(target_url)
        except NotBranchError:
            branch_to = BzrDir.create_branch_and_repo(target_url)
        branch_to.pull(branch_from)


def get_default_bazaar_branch_store():
    """Return the default `BazaarBranchStore`."""
    return BazaarBranchStore(
        get_transport(config.codeimport.bazaar_branch_store))


def _download(transport, relpath, local_path):
    """Download the file at `relpath` from `transport` to `local_path`."""
    local_file = open(local_path, 'wb')
    try:
        remote_file = transport.get(relpath)
        try:
            pumpfile(remote_file, local_file)
        finally:
            remote_file.close()
    finally:
        local_file.close()


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
    :ivar svn_branch_url: The branch URL if rcstype == 'svn', None otherwise.
    :ivar cvs_root: The $CVSROOT if rcstype == 'cvs', None otherwise.
    :ivar cvs_module: The CVS module if rcstype == 'cvs', None otherwise.
    :ivar source_product_series_id: The id of the ProductSeries the
        code import was created from, if any.  This attribute will be
        deleted when the transition to the new system is complete.
    """

    def __init__(self, branch_id, rcstype, svn_branch_url=None, cvs_root=None,
                 cvs_module=None, source_product_series_id=0):
        self.branch_id = branch_id
        self.rcstype = rcstype
        self.svn_branch_url = svn_branch_url
        self.cvs_root = cvs_root
        self.cvs_module = cvs_module
        # XXX: MichaelHudson 2008-05-19 bug=231819: The
        # source_product_series_id attribute is to do with the new system
        # looking in legacy locations for foreign trees and can be deleted
        # when the new system has been running for a while.
        self.source_product_series_id = source_product_series_id

    @classmethod
    def fromArguments(cls, arguments):
        """Convert command line-style arguments to an instance."""
        branch_id = int(arguments.pop(0))
        rcstype = arguments.pop(0)
        # XXX: MichaelHudson 2008-05-19 bug=231819: The
        # source_product_series_id attribute is to do with the new system
        # looking in legacy locations for foreign trees and can be deleted
        # when the new system has been running for a while.
        source_product_series_id = int(arguments.pop(0))
        if rcstype == 'svn':
            [svn_branch_url] = arguments
            cvs_root = cvs_module = None
        elif rcstype == 'cvs':
            svn_branch_url = None
            [cvs_root, cvs_module] = arguments
        else:
            raise AssertionError("Unknown rcstype %r." % rcstype)
        return cls(
            branch_id, rcstype, svn_branch_url, cvs_root, cvs_module,
            source_product_series_id)

    @classmethod
    def fromCodeImport(cls, code_import):
        """Convert a `CodeImport` to an instance."""
        # XXX: MichaelHudson 2008-05-19 bug=231819: The
        # source_product_series_id attribute is to do with the new system
        # looking in legacy locations for foreign trees and can be deleted
        # when the new system has been running for a while.
        source_product_series_id = 0
        if code_import.rcs_type == RevisionControlSystems.SVN:
            rcstype = 'svn'
            svn_branch_url = str(code_import.svn_branch_url)
            cvs_root = cvs_module = None
        elif code_import.rcs_type == RevisionControlSystems.CVS:
            rcstype = 'cvs'
            svn_branch_url = None
            cvs_root = str(code_import.cvs_root)
            cvs_module = str(code_import.cvs_module)
        else:
            raise AssertionError("Unknown rcstype %r." % rcstype)
        return cls(
            code_import.branch.id, rcstype, svn_branch_url,
            cvs_root, cvs_module, source_product_series_id)

    def asArguments(self):
        """Return a list of arguments suitable for passing to a child process.
        """
        result = [str(self.branch_id), self.rcstype, str(self.source_product_series_id)]
        if self.rcstype == 'svn':
            result.append(self.svn_branch_url)
        elif self.rcstype == 'cvs':
            result.append(self.cvs_root)
            result.append(self.cvs_module)
        else:
            raise AssertionError("Unknown rcstype %r." % self.rcstype)
        return result


class ForeignTreeStore:
    """Manages retrieving and storing foreign working trees.

    The code import system stores tarballs of CVS and SVN working trees on
    another system. The tarballs are kept in predictable locations based on
    the ID of the branch associated to the `CodeImport`.

    The tarballs are all kept in one directory. The filename of a tarball is
    XXXXXXXX.tar.gz, where 'XXXXXXXX' is the ID of the `CodeImport`'s branch
    in hex.
    """

    def __init__(self, transport):
        """Construct a `ForeignTreeStore`.

        :param transport: A writable transport that points to the base
            directory where the tarballs are stored.
        :ptype transport: `bzrlib.transport.Transport`.
        """
        self.transport = transport

    def _getForeignTree(self, source_details, target_path):
        """Return a foreign tree object for `source_details`."""
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

    def _getTarballName(self, branch_id):
        """Return the name of the tarball for the code import."""
        return '%08x.tar.gz' % branch_id

    def _getOldTarballName(self, source_details):
        """Return the name of the tarball for the code import."""
        dirname = '%08x' % source_details.source_product_series_id
        if source_details.rcstype == 'svn':
            filename = 'svnworking.tgz'
        elif source_details.rcstype == 'cvs':
            filename = 'cvsworking.tgz'
        else:
            raise AssertionError(
                "unknown RCS type: %r" % source_details.rcstype)
        return '%s/%s' % (dirname, filename)

    def archive(self, source_details, foreign_tree):
        """Archive the foreign tree."""
        tarball_name = self._getTarballName(source_details.branch_id)
        create_tarball(foreign_tree.local_path, tarball_name)
        tarball = open(tarball_name, 'rb')
        ensure_base(self.transport)
        try:
            self.transport.put_file(tarball_name, tarball)
        finally:
            tarball.close()

    def fetch(self, source_details, target_path):
        """Fetch the foreign branch for `source_details` to `target_path`.

        If there is no tarball archived for `source_details`, then try to
        download (i.e. checkout) the foreign tree from its source repository,
        generally on a third party server.
        """
        try:
            return self.fetchFromArchive(source_details, target_path)
        except NoSuchFile:
            try:
                # XXX: MichaelHudson 2008-05-19 bug=231819: This code is to do
                # with the new system looking in legacy locations for foreign
                # trees and can be deleted when the new system has been
                # running for a while.
                return self.fetchFromOldLocationAndUploadToNewLocation(
                    source_details, target_path)
            except NoSuchFile:
                return self.fetchFromSource(source_details, target_path)

    def fetchFromSource(self, source_details, target_path):
        """Fetch the foreign tree for `source_details` to `target_path`."""
        branch = self._getForeignTree(source_details, target_path)
        branch.checkout()
        return branch

    def fetchFromArchive(self, source_details, target_path):
        """Fetch the foreign tree for `source_details` from the archive."""
        tarball_name = self._getTarballName(source_details.branch_id)
        if not self.transport.has(tarball_name):
            raise NoSuchFile(tarball_name)
        _download(self.transport, tarball_name, tarball_name)
        extract_tarball(tarball_name, target_path)
        tree = self._getForeignTree(source_details, target_path)
        tree.update()
        return tree

    def fetchFromOldLocationAndUploadToNewLocation(self, source_details,
                                                   target_path):
        """Transitional code."""
        # XXX: MichaelHudson 2008-05-19 bug=231819: This code is to do with
        # the new system looking in legacy locations for foreign trees and can
        # be deleted when the new system has been running for a while.
        if source_details.source_product_series_id == 0:
            raise NoSuchFile("")
        old_tarball_name = self._getOldTarballName(source_details)
        if not self.transport.has(old_tarball_name):
            raise NoSuchFile(old_tarball_name)
        basename = os.path.basename(old_tarball_name)
        _download(self.transport, old_tarball_name, basename)
        extract_tarball(basename, target_path)
        tree = self._getForeignTree(source_details, target_path)
        self.archive(source_details, tree)
        tree.update()
        return tree


def get_default_foreign_tree_store():
    """Get the default `ForeignTreeStore`."""
    return ForeignTreeStore(
        get_transport(config.codeimport.foreign_tree_store))


class ImportWorker:
    """Oversees the actual work of a code import."""

    # Where the Bazaar working tree will be stored.
    BZR_WORKING_TREE_PATH = 'bzr_working_tree'

    # Where the foreign working tree will be stored.
    FOREIGN_WORKING_TREE_PATH = 'foreign_working_tree'

    def __init__(self, source_details, foreign_tree_store,
                 bazaar_branch_store, logger):
        """Construct an `ImportWorker`.

        :param source_details: A `CodeImportSourceDetails` object.
        :param foreign_tree_store: A `ForeignTreeStore`. The import worker
            uses this to fetch and store foreign branches.
        :param bazaar_branch_store: A `BazaarBranchStore`. The import worker
            uses this to fetch and store the Bazaar branches that are created
            and updated during the import process.
        :param logger: A `Logger` to pass to cscvs.
        """
        self.source_details = source_details
        self.foreign_tree_store = foreign_tree_store
        self.bazaar_branch_store = bazaar_branch_store
        self.working_directory = tempfile.mkdtemp()
        self._foreign_branch = None
        self._logger = logger
        self._bazaar_working_tree_path = os.path.join(
            self.working_directory, self.BZR_WORKING_TREE_PATH)
        self._foreign_working_tree_path = os.path.join(
            self.working_directory, self.FOREIGN_WORKING_TREE_PATH)

    def getBazaarWorkingTree(self):
        """Return the Bazaar `WorkingTree` that we are importing into."""
        if os.path.isdir(self._bazaar_working_tree_path):
            shutil.rmtree(self._bazaar_working_tree_path)
        return self.bazaar_branch_store.pull(
            self.source_details.branch_id, self._bazaar_working_tree_path)

    def getForeignTree(self):
        """Return the foreign branch object that we are importing from.

        :return: A `SubversionWorkingTree` or a `CVSWorkingTree`.
        """
        if os.path.isdir(self._foreign_working_tree_path):
            shutil.rmtree(self._foreign_working_tree_path)
        os.mkdir(self._foreign_working_tree_path)
        return self.foreign_tree_store.fetch(
            self.source_details, self._foreign_working_tree_path)

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
        foreign_tree = self.getForeignTree()
        bazaar_tree = self.getBazaarWorkingTree()
        self.importToBazaar(foreign_tree, bazaar_tree)
        self.bazaar_branch_store.push(
            self.source_details.branch_id, bazaar_tree)
        self.foreign_tree_store.archive(
            self.source_details, foreign_tree)
        shutil.rmtree(bazaar_tree.basedir)
        shutil.rmtree(foreign_tree.local_path)
