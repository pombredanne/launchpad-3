# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The code import worker. This imports code from foreign repositories."""

__metaclass__ = type
__all__ = [
    'BazaarBranchStore',
    'BzrImportWorker',
    'BzrSvnImportWorker',
    'CSCVSImportWorker',
    'CodeImportBranchOpenPolicy',
    'CodeImportSourceDetails',
    'CodeImportWorkerExitCode',
    'ForeignTreeStore',
    'GitImportWorker',
    'ImportWorker',
    'ToBzrImportWorker',
    'get_default_bazaar_branch_store',
    ]


import io
import os
import shutil
import subprocess
from urlparse import (
    urlsplit,
    urlunsplit,
    )

# FIRST Ensure correct plugins are loaded. Do not delete this comment or the
# line below this comment.
import lp.codehosting

from bzrlib.branch import (
    Branch,
    InterBranch,
    )
from bzrlib.bzrdir import (
    BzrDir,
    BzrDirFormat,
    )
from bzrlib.errors import (
    ConnectionError,
    InvalidEntryName,
    NoRepositoryPresent,
    NoSuchFile,
    NotBranchError,
    TooManyRedirections,
    )
from bzrlib.transport import (
    get_transport_from_path,
    get_transport_from_url,
    )
import bzrlib.ui
from bzrlib.upgrade import upgrade
from bzrlib.urlutils import (
    join as urljoin,
    local_path_from_url,
    )
import cscvs
from cscvs.cmds import totla
import CVS
from dulwich.errors import GitProtocolError
from dulwich.protocol import (
    pkt_line,
    Protocol,
    )
from lazr.uri import (
    InvalidURIError,
    URI,
    )
from pymacaroons import Macaroon
import SCM

from lp.code.interfaces.branch import get_blacklisted_hostnames
from lp.codehosting.codeimport.foreigntree import CVSWorkingTree
from lp.codehosting.codeimport.tarball import (
    create_tarball,
    extract_tarball,
    )
from lp.codehosting.codeimport.uifactory import LoggingUIFactory
from lp.codehosting.safe_open import (
    BadUrl,
    BranchOpenPolicy,
    SafeBranchOpener,
    )
from lp.services.config import config
from lp.services.propertycache import cachedproperty
from lp.services.timeout import urlfetch
from lp.services.utils import sanitise_urls


class CodeImportBranchOpenPolicy(BranchOpenPolicy):
    """Branch open policy for code imports.

    In summary:
     - follow references,
     - only open non-Launchpad URLs for imports from Bazaar to Bazaar or
       from Git to Git
     - only open the allowed schemes
    """

    allowed_schemes = ['http', 'https', 'svn', 'git', 'ftp', 'bzr']

    def __init__(self, rcstype, target_rcstype):
        self.rcstype = rcstype
        self.target_rcstype = target_rcstype

    def shouldFollowReferences(self):
        """See `BranchOpenPolicy.shouldFollowReferences`.

        We traverse branch references for MIRRORED branches because they
        provide a useful redirection mechanism and we want to be consistent
        with the bzr command line.
        """
        return True

    def transformFallbackLocation(self, branch, url):
        """See `BranchOpenPolicy.transformFallbackLocation`.

        For mirrored branches, we stack on whatever the remote branch claims
        to stack on, but this URL still needs to be checked.
        """
        return urljoin(branch.base, url), True

    def checkOneURL(self, url):
        """See `BranchOpenPolicy.checkOneURL`.

        We refuse to mirror Bazaar branches from Launchpad, or any branches
        from a ssh-like or file URL.
        """
        try:
            uri = URI(url)
        except InvalidURIError:
            raise BadUrl(url)
        if self.rcstype == self.target_rcstype:
            launchpad_domain = config.vhost.mainsite.hostname
            if uri.underDomain(launchpad_domain):
                raise BadUrl(url)
        for hostname in get_blacklisted_hostnames():
            if uri.underDomain(hostname):
                raise BadUrl(url)
        if uri.scheme not in self.allowed_schemes:
            raise BadUrl(url)


class CodeImportWorkerExitCode:
    """Exit codes used by the code import worker script."""

    SUCCESS = 0
    FAILURE = 1
    SUCCESS_NOCHANGE = 2
    SUCCESS_PARTIAL = 3
    FAILURE_INVALID = 4
    FAILURE_UNSUPPORTED_FEATURE = 5
    FAILURE_FORBIDDEN = 6
    FAILURE_REMOTE_BROKEN = 7


class BazaarBranchStore:
    """A place where Bazaar branches of code imports are kept."""

    def __init__(self, transport):
        """Construct a Bazaar branch store based at `transport`."""
        self.transport = transport

    def _getMirrorURL(self, db_branch_id, push=False):
        """Return the URL that `db_branch` is stored at."""
        base_url = self.transport.base
        if push:
            # Pulling large branches over sftp is less CPU-intensive, but
            # pushing over bzr+ssh seems to be more reliable.
            split = urlsplit(base_url)
            if split.scheme == 'sftp':
                base_url = urlunsplit([
                    'bzr+ssh', split.netloc, split.path, split.query,
                    split.fragment])
        return urljoin(base_url, '%08x' % db_branch_id)

    def pull(self, db_branch_id, target_path, required_format,
             needs_tree=False, stacked_on_url=None):
        """Pull down the Bazaar branch of an import to `target_path`.

        :return: A Bazaar branch for the code import corresponding to the
            database branch with id `db_branch_id`.
        """
        remote_url = self._getMirrorURL(db_branch_id)
        try:
            remote_bzr_dir = BzrDir.open(remote_url)
        except NotBranchError:
            local_branch = BzrDir.create_branch_and_repo(
                target_path, format=required_format)
            if needs_tree:
                local_branch.bzrdir.create_workingtree()
            if stacked_on_url:
                local_branch.set_stacked_on_url(stacked_on_url)
            return local_branch
        # The proper thing to do here would be to call
        # "remote_bzr_dir.sprout()".  But 2a fetch slowly checks which
        # revisions are in the ancestry of the tip of the remote branch, which
        # we strictly don't care about, so we just copy the whole thing down
        # at the vfs level.
        control_dir = remote_bzr_dir.root_transport.relpath(
            remote_bzr_dir.transport.abspath('.'))
        target = get_transport_from_path(target_path)
        target_control = target.clone(control_dir)
        target_control.create_prefix()
        remote_bzr_dir.transport.copy_tree_to_transport(target_control)
        local_bzr_dir = BzrDir.open_from_transport(target)
        if local_bzr_dir.needs_format_conversion(format=required_format):
            try:
                local_bzr_dir.root_transport.delete_tree('backup.bzr')
            except NoSuchFile:
                pass
            upgrade(target_path, required_format, clean_up=True)
        if needs_tree:
            local_bzr_dir.create_workingtree()
        return local_bzr_dir.open_branch()

    def push(self, db_branch_id, bzr_branch, required_format,
             stacked_on_url=None):
        """Push up `bzr_branch` as the Bazaar branch for `code_import`.

        :return: A boolean that is true if the push was non-trivial
            (i.e. actually transferred revisions).
        """
        self.transport.create_prefix()
        target_url = self._getMirrorURL(db_branch_id, push=True)
        try:
            remote_branch = Branch.open(target_url)
        except NotBranchError:
            remote_branch = BzrDir.create_branch_and_repo(
                target_url, format=required_format)
            old_branch = None
        else:
            if remote_branch.bzrdir.needs_format_conversion(
                    required_format):
                # For upgrades, push to a new branch in
                # the new format. When done pushing,
                # retire the old .bzr directory and rename
                # the new one in place.
                old_branch = remote_branch
                upgrade_url = urljoin(target_url, "backup.bzr")
                try:
                    remote_branch.bzrdir.root_transport.delete_tree(
                        'backup.bzr')
                except NoSuchFile:
                    pass
                remote_branch = BzrDir.create_branch_and_repo(
                    upgrade_url, format=required_format)
            else:
                old_branch = None
        # This can be done safely, since only modern formats are used to
        # import to.
        if stacked_on_url is not None:
            remote_branch.set_stacked_on_url(stacked_on_url)
        pull_result = remote_branch.pull(bzr_branch, overwrite=True)
        # Because of the way we do incremental imports, there may be revisions
        # in the branch's repo that are not in the ancestry of the branch tip.
        # We need to transfer them too.
        remote_branch.repository.fetch(bzr_branch.repository)
        if old_branch is not None:
            # The format has changed; move the new format
            # branch in place.
            base_transport = old_branch.bzrdir.root_transport
            base_transport.delete_tree('.bzr')
            base_transport.rename("backup.bzr/.bzr", ".bzr")
            base_transport.rmdir("backup.bzr")
        return pull_result.old_revid != pull_result.new_revid


def get_default_bazaar_branch_store():
    """Return the default `BazaarBranchStore`."""
    return BazaarBranchStore(
        get_transport_from_url(config.codeimport.bazaar_branch_store))


class CodeImportSourceDetails:
    """The information needed to process an import.

    As the worker doesn't talk to the database, we don't use
    `CodeImport` objects for this.

    The 'fromArguments' method builds an instance of this class from a form
    of the information suitable for passing around on executables' command
    lines.

    :ivar target_id: The id of the Bazaar branch or the path of the Git
        repository associated with this code import, used for locating the
        existing import and the foreign tree.
    :ivar rcstype: 'cvs', 'git', 'bzr-svn', 'bzr' as appropriate.
    :ivar target_rcstype: 'bzr' or 'git' as appropriate.
    :ivar url: The branch URL if rcstype in ['bzr-svn', 'git', 'bzr'], None
        otherwise.
    :ivar cvs_root: The $CVSROOT if rcstype == 'cvs', None otherwise.
    :ivar cvs_module: The CVS module if rcstype == 'cvs', None otherwise.
    :ivar stacked_on_url: The URL of the branch that the associated branch
        is stacked on, if any.
    :ivar macaroon: A macaroon granting authority to push to the target
        repository if target_rcstype == 'git', None otherwise.
    """

    def __init__(self, target_id, rcstype, target_rcstype, url=None,
                 cvs_root=None, cvs_module=None, stacked_on_url=None,
                 macaroon=None):
        self.target_id = target_id
        self.rcstype = rcstype
        self.target_rcstype = target_rcstype
        self.url = url
        self.cvs_root = cvs_root
        self.cvs_module = cvs_module
        self.stacked_on_url = stacked_on_url
        self.macaroon = macaroon

    @classmethod
    def fromArguments(cls, arguments):
        """Convert command line-style arguments to an instance."""
        # Keep this in sync with CodeImportJob.makeWorkerArguments.
        arguments = list(arguments)
        target_id = arguments.pop(0)
        rcstype = arguments.pop(0)
        # XXX cjwatson 2016-10-12: Remove compatibility code once the
        # scheduler always passes both source and target types.
        if ':' in rcstype:
            rcstype, target_rcstype = rcstype.split(':', 1)
        else:
            target_rcstype = 'bzr'
        if rcstype in ['bzr-svn', 'git', 'bzr']:
            url = arguments.pop(0)
            if target_rcstype == 'bzr':
                try:
                    stacked_on_url = arguments.pop(0)
                except IndexError:
                    stacked_on_url = None
            else:
                stacked_on_url = None
            cvs_root = cvs_module = None
        elif rcstype == 'cvs':
            url = None
            stacked_on_url = None
            [cvs_root, cvs_module] = arguments
        else:
            raise AssertionError("Unknown rcstype %r." % rcstype)
        if target_rcstype == 'bzr':
            target_id = int(target_id)
            macaroon = None
        elif target_rcstype == 'git':
            macaroon = Macaroon.deserialize(arguments.pop(0))
        else:
            raise AssertionError("Unknown target_rcstype %r." % target_rcstype)
        return cls(
            target_id, rcstype, target_rcstype, url, cvs_root, cvs_module,
            stacked_on_url, macaroon)


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
        self._target_id = source_details.target_id

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
        return '%08x%s' % (self._target_id, ext)

    def fetch(self, filename, dest_transport=None):
        """Retrieve `filename` from the store.

        :param filename: The name of the file to retrieve (must be a filename,
            not a path).
        :param dest_transport: The transport to retrieve the file to,
            defaulting to ``get_transport_from_path('.')``.
        :return: A boolean, true if the file was found and retrieved, false
            otherwise.
        """
        if dest_transport is None:
            dest_transport = get_transport_from_path('.')
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
            source_transport = get_transport_from_path('.')
        remote_name = self._getRemoteName(filename)
        local_file = source_transport.get(filename)
        self._transport.create_prefix()
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
        if source_details.rcstype == 'cvs':
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

    def __init__(self, source_details, logger, opener_policy):
        """Construct an `ImportWorker`.

        :param source_details: A `CodeImportSourceDetails` object.
        :param logger: A `Logger` to pass to cscvs.
        :param opener_policy: Policy object that decides what branches can
             be imported
        """
        self.source_details = source_details
        self._logger = logger
        self._opener_policy = opener_policy

    def getWorkingDirectory(self):
        """The directory we should change to and store all scratch files in.
        """
        base = config.codeimportworker.working_directory_root
        dirname = 'worker-for-branch-%s' % self.source_details.target_id
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
            return self._doImport()
        finally:
            shutil.rmtree(working_directory)
            os.chdir(saved_pwd)

    def _doImport(self):
        """Perform the import.

        :return: A CodeImportWorkerExitCode
        """
        raise NotImplementedError()


class ToBzrImportWorker(ImportWorker):
    """Oversees the actual work of a code import to Bazaar."""

    # Where the Bazaar working tree will be stored.
    BZR_BRANCH_PATH = 'bzr_branch'

    # Should `getBazaarBranch` create a working tree?
    needs_bzr_tree = True

    required_format = BzrDirFormat.get_default_format()

    def __init__(self, source_details, import_data_transport,
                 bazaar_branch_store, logger, opener_policy):
        """Construct a `ToBzrImportWorker`.

        :param source_details: A `CodeImportSourceDetails` object.
        :param bazaar_branch_store: A `BazaarBranchStore`. The import worker
            uses this to fetch and store the Bazaar branches that are created
            and updated during the import process.
        :param logger: A `Logger` to pass to cscvs.
        :param opener_policy: Policy object that decides what branches can
             be imported
        """
        super(ToBzrImportWorker, self).__init__(
            source_details, logger, opener_policy)
        self.bazaar_branch_store = bazaar_branch_store
        self.import_data_store = ImportDataStore(
            import_data_transport, self.source_details)

    def getBazaarBranch(self):
        """Return the Bazaar `Branch` that we are importing into."""
        if os.path.isdir(self.BZR_BRANCH_PATH):
            shutil.rmtree(self.BZR_BRANCH_PATH)
        return self.bazaar_branch_store.pull(
            self.source_details.target_id, self.BZR_BRANCH_PATH,
            self.required_format, self.needs_bzr_tree,
            stacked_on_url=self.source_details.stacked_on_url)

    def pushBazaarBranch(self, bazaar_branch):
        """Push the updated Bazaar branch to the server.

        :return: True if revisions were transferred.
        """
        return self.bazaar_branch_store.push(
            self.source_details.target_id, bazaar_branch,
            self.required_format,
            stacked_on_url=self.source_details.stacked_on_url)


class CSCVSImportWorker(ToBzrImportWorker):
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

        :return: A `CVSWorkingTree`.
        """
        if os.path.isdir(self.FOREIGN_WORKING_TREE_PATH):
            shutil.rmtree(self.FOREIGN_WORKING_TREE_PATH)
        os.mkdir(self.FOREIGN_WORKING_TREE_PATH)
        return self.foreign_tree_store.fetch(self.FOREIGN_WORKING_TREE_PATH)

    def importToBazaar(self, foreign_tree, bazaar_branch):
        """Actually import `foreign_tree` into `bazaar_branch`.

        :param foreign_tree: A `CVSWorkingTree`.
        :param bazaar_tree: A `bzrlib.branch.Branch`, which must have a
            colocated working tree.
        """
        foreign_directory = foreign_tree.local_path
        bzr_directory = str(bazaar_branch.bzrdir.open_workingtree().basedir)

        scm_branch = SCM.branch(bzr_directory)
        last_commit = cscvs.findLastCscvsCommit(scm_branch)

        # If branch in `bazaar_tree` doesn't have any identifiable CSCVS
        # revisions, CSCVS "initializes" the branch.
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
        bazaar_branch = self.getBazaarBranch()
        self.importToBazaar(foreign_tree, bazaar_branch)
        non_trivial = self.pushBazaarBranch(bazaar_branch)
        self.foreign_tree_store.archive(foreign_tree)
        if non_trivial:
            return CodeImportWorkerExitCode.SUCCESS
        else:
            return CodeImportWorkerExitCode.SUCCESS_NOCHANGE


class PullingImportWorker(ToBzrImportWorker):
    """An import worker for imports that can be done by a bzr plugin.

    Subclasses need to implement `probers`.
    """

    needs_bzr_tree = False

    @property
    def invalid_branch_exceptions(self):
        """Exceptions that indicate no (valid) remote branch is present."""
        raise NotImplementedError

    @property
    def unsupported_feature_exceptions(self):
        """The exceptions to consider for unsupported features."""
        raise NotImplementedError

    @property
    def broken_remote_exceptions(self):
        """The exceptions to consider for broken remote branches."""
        raise NotImplementedError

    @property
    def probers(self):
        """The probers that should be tried for this import."""
        raise NotImplementedError

    def getRevisionLimit(self):
        """Return maximum number of revisions to fetch (None for no limit).
        """
        return None

    def _doImport(self):
        self._logger.info("Starting job.")
        saved_factory = bzrlib.ui.ui_factory
        opener = SafeBranchOpener(self._opener_policy, self.probers)
        bzrlib.ui.ui_factory = LoggingUIFactory(logger=self._logger)
        try:
            self._logger.info(
                "Getting exising bzr branch from central store.")
            bazaar_branch = self.getBazaarBranch()
            try:
                remote_branch = opener.open(self.source_details.url)
            except TooManyRedirections:
                self._logger.info("Too many redirections.")
                return CodeImportWorkerExitCode.FAILURE_INVALID
            except NotBranchError:
                self._logger.info("No branch found at remote location.")
                return CodeImportWorkerExitCode.FAILURE_INVALID
            except BadUrl as e:
                self._logger.info("Invalid URL: %s" % e)
                return CodeImportWorkerExitCode.FAILURE_FORBIDDEN
            except ConnectionError as e:
                self._logger.info("Unable to open remote branch: %s" % e)
                return CodeImportWorkerExitCode.FAILURE_INVALID
            try:
                remote_branch_tip = remote_branch.last_revision()
                inter_branch = InterBranch.get(remote_branch, bazaar_branch)
                self._logger.info("Importing branch.")
                revision_limit = self.getRevisionLimit()
                inter_branch.fetch(limit=revision_limit)
                if bazaar_branch.repository.has_revision(remote_branch_tip):
                    pull_result = inter_branch.pull(overwrite=True)
                    if pull_result.old_revid != pull_result.new_revid:
                        result = CodeImportWorkerExitCode.SUCCESS
                    else:
                        result = CodeImportWorkerExitCode.SUCCESS_NOCHANGE
                else:
                    result = CodeImportWorkerExitCode.SUCCESS_PARTIAL
            except Exception as e:
                if e.__class__ in self.unsupported_feature_exceptions:
                    self._logger.info(
                        "Unable to import branch because of limitations in "
                        "Bazaar.")
                    self._logger.info(str(e))
                    return (
                        CodeImportWorkerExitCode.FAILURE_UNSUPPORTED_FEATURE)
                elif e.__class__ in self.invalid_branch_exceptions:
                    self._logger.info("Branch invalid: %s", str(e))
                    return CodeImportWorkerExitCode.FAILURE_INVALID
                elif e.__class__ in self.broken_remote_exceptions:
                    self._logger.info("Remote branch broken: %s", str(e))
                    return CodeImportWorkerExitCode.FAILURE_REMOTE_BROKEN
                else:
                    raise
            self._logger.info("Pushing local import branch to central store.")
            self.pushBazaarBranch(bazaar_branch)
            self._logger.info("Job complete.")
            return result
        finally:
            bzrlib.ui.ui_factory = saved_factory


class GitImportWorker(PullingImportWorker):
    """An import worker for Git imports.

    The only behaviour we add is preserving the 'git.db' shamap between runs.
    """

    @property
    def invalid_branch_exceptions(self):
        return [
            NoRepositoryPresent,
            NotBranchError,
            ConnectionError,
        ]

    @property
    def unsupported_feature_exceptions(self):
        from bzrlib.plugins.git.fetch import SubmodulesRequireSubtrees
        return [
            InvalidEntryName,
            SubmodulesRequireSubtrees,
        ]

    @property
    def broken_remote_exceptions(self):
        return []

    @property
    def probers(self):
        """See `PullingImportWorker.probers`."""
        from bzrlib.plugins.git import (
            LocalGitProber, RemoteGitProber)
        return [LocalGitProber, RemoteGitProber]

    def getRevisionLimit(self):
        """See `PullingImportWorker.getRevisionLimit`."""
        return config.codeimport.git_revisions_import_limit

    def getBazaarBranch(self):
        """See `ToBzrImportWorker.getBazaarBranch`.

        In addition to the superclass' behaviour, we retrieve bzr-git's
        caches, both legacy and modern, from the import data store and put
        them where bzr-git will find them in the Bazaar tree, that is at
        '.bzr/repository/git.db' and '.bzr/repository/git'.
        """
        branch = PullingImportWorker.getBazaarBranch(self)
        # Fetch the legacy cache from the store, if present.
        self.import_data_store.fetch(
            'git.db', branch.repository._transport)
        # The cache dir from newer bzr-gits is stored as a tarball.
        local_name = 'git-cache.tar.gz'
        if self.import_data_store.fetch(local_name):
            repo_transport = branch.repository._transport
            repo_transport.mkdir('git')
            git_db_dir = os.path.join(
                local_path_from_url(repo_transport.base), 'git')
            extract_tarball(local_name, git_db_dir)
        return branch

    def pushBazaarBranch(self, bazaar_branch):
        """See `ToBzrImportWorker.pushBazaarBranch`.

        In addition to the superclass' behaviour, we store bzr-git's cache
        directory at .bzr/repository/git in the import data store.
        """
        non_trivial = PullingImportWorker.pushBazaarBranch(
            self, bazaar_branch)
        repo_base = bazaar_branch.repository._transport.base
        git_db_dir = os.path.join(local_path_from_url(repo_base), 'git')
        local_name = 'git-cache.tar.gz'
        create_tarball(git_db_dir, local_name)
        self.import_data_store.put(local_name)
        return non_trivial


class BzrSvnImportWorker(PullingImportWorker):
    """An import worker for importing Subversion via bzr-svn."""

    @property
    def invalid_branch_exceptions(self):
        return [
            NoRepositoryPresent,
            NotBranchError,
            ConnectionError,
        ]

    @property
    def unsupported_feature_exceptions(self):
        from bzrlib.plugins.svn.errors import InvalidFileName
        return [
            InvalidEntryName,
            InvalidFileName,
        ]

    @property
    def broken_remote_exceptions(self):
        from bzrlib.plugins.svn.errors import IncompleteRepositoryHistory
        return [IncompleteRepositoryHistory]

    def getRevisionLimit(self):
        """See `PullingImportWorker.getRevisionLimit`."""
        return config.codeimport.svn_revisions_import_limit

    @property
    def probers(self):
        """See `PullingImportWorker.probers`."""
        from bzrlib.plugins.svn import SvnRemoteProber
        return [SvnRemoteProber]


class BzrImportWorker(PullingImportWorker):
    """An import worker for importing Bazaar branches."""

    invalid_branch_exceptions = [
        NotBranchError,
        ConnectionError,
        ]
    unsupported_feature_exceptions = []
    broken_remote_exceptions = []

    def getRevisionLimit(self):
        """See `PullingImportWorker.getRevisionLimit`."""
        # For now, just grab the whole branch at once.
        # bzr does support fetch(limit=) but it isn't very efficient at
        # the moment.
        return None

    @property
    def probers(self):
        """See `PullingImportWorker.probers`."""
        from bzrlib.bzrdir import BzrProber, RemoteBzrProber
        return [BzrProber, RemoteBzrProber]


class GitToGitImportWorker(ImportWorker):
    """An import worker for imports from Git to Git."""

    def _runGit(self, *args, **kwargs):
        """Run git with arguments, sending output to the logger."""
        cmd = ["git"] + list(args)
        git_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        for line in git_process.stdout:
            line = line.decode("UTF-8", "replace").rstrip("\n")
            self._logger.info(sanitise_urls(line))
        retcode = git_process.wait()
        if retcode:
            raise subprocess.CalledProcessError(retcode, cmd)

    def _getHead(self, repository, remote_name):
        """Get HEAD from a configured remote in a local repository.

        The returned ref name will be adjusted in such a way that it can be
        passed to `_setHead` (e.g. refs/remotes/origin/master ->
        refs/heads/master).
        """
        # This is a bit weird, but set-head will bail out if the target
        # doesn't exist in the correct remotes namespace.  git 2.8.0 has
        # "git ls-remote --symref <repository> HEAD" which would involve
        # less juggling.
        self._runGit(
            "fetch", "-q", ".", "refs/heads/*:refs/remotes/%s/*" % remote_name,
            cwd=repository)
        self._runGit(
            "remote", "set-head", remote_name, "--auto", cwd=repository)
        ref_prefix = "refs/remotes/%s/" % remote_name
        target_ref = subprocess.check_output(
            ["git", "symbolic-ref", ref_prefix + "HEAD"],
            cwd=repository, universal_newlines=True).rstrip("\n")
        if not target_ref.startswith(ref_prefix):
            raise GitProtocolError(
                "'git remote set-head %s --auto' did not leave remote HEAD "
                "under %s" % (remote_name, ref_prefix))
        real_target_ref = "refs/heads/" + target_ref[len(ref_prefix):]
        # Ensure the result is a valid ref name, just in case.
        self._runGit("check-ref-format", real_target_ref, cwd="repository")
        return real_target_ref

    def _setHead(self, target_url, target_ref):
        """Set HEAD on a remote repository.

        This relies on the turnip-set-symbolic-ref extension.
        """
        service = "turnip-set-symbolic-ref"
        url = urljoin(target_url, service)
        headers = {
            "Content-Type": "application/x-%s-request" % service,
            }
        body = pkt_line("HEAD %s" % target_ref) + pkt_line(None)
        try:
            response = urlfetch(url, method="POST", headers=headers, data=body)
            response.raise_for_status()
        except Exception as e:
            raise GitProtocolError(str(e))
        content_type = response.headers.get("Content-Type")
        if content_type != ("application/x-%s-result" % service):
            raise GitProtocolError(
                "Invalid Content-Type from server: %s" % content_type)
        content = io.BytesIO(response.content)
        proto = Protocol(content.read, None)
        pkt = proto.read_pkt_line()
        if pkt is None:
            raise GitProtocolError("Unexpected flush-pkt from server")
        elif pkt.rstrip(b"\n") == b"ACK HEAD":
            pass
        elif pkt.startswith(b"ERR "):
            raise GitProtocolError(
                pkt[len(b"ERR "):].rstrip(b"\n").decode("UTF-8"))
        else:
            raise GitProtocolError("Unexpected packet %r from server" % pkt)

    def _deleteRefs(self, repository, pattern):
        """Delete all refs in `repository` matching `pattern`."""
        # XXX cjwatson 2016-11-08: We might ideally use something like:
        # "git for-each-ref --format='delete %(refname)%00%(objectname)%00' \
        #   <pattern> | git update-ref --stdin -z
        # ... which would be faster, but that requires git 1.8.5.
        remote_refs = subprocess.check_output(
            ["git", "for-each-ref", "--format=%(refname)", pattern],
            cwd="repository").splitlines()
        for remote_ref in remote_refs:
            self._runGit("update-ref", "-d", remote_ref, cwd="repository")

    def _doImport(self):
        self._logger.info("Starting job.")
        try:
            self._opener_policy.checkOneURL(self.source_details.url)
        except BadUrl as e:
            self._logger.info("Invalid URL: %s" % e)
            return CodeImportWorkerExitCode.FAILURE_FORBIDDEN
        unauth_target_url = urljoin(
            config.codehosting.git_browse_root, self.source_details.target_id)
        split = urlsplit(unauth_target_url)
        target_netloc = ":%s@%s" % (
            self.source_details.macaroon.serialize(), split.hostname)
        if split.port:
            target_netloc += ":%s" % split.port
        target_url = urlunsplit([
            split.scheme, target_netloc, split.path, "", ""])
        # XXX cjwatson 2016-10-11: Ideally we'd put credentials in a
        # credentials store instead.  However, git only accepts credentials
        # that have both a non-empty username and a non-empty password.
        self._logger.info("Getting existing repository from hosting service.")
        try:
            self._runGit("clone", "--mirror", target_url, "repository")
        except subprocess.CalledProcessError as e:
            self._logger.info(
                "Unable to get existing repository from hosting service: "
                "git clone exited %s" % e.returncode)
            return CodeImportWorkerExitCode.FAILURE
        self._logger.info("Fetching remote repository.")
        try:
            self._runGit("config", "gc.auto", "0", cwd="repository")
            # Remove any stray remote-tracking refs from the last time round.
            self._deleteRefs("repository", "refs/remotes/source/**")
            self._runGit(
                "remote", "add", "source", self.source_details.url,
                cwd="repository")
            self._runGit(
                "fetch", "--prune", "source", "+refs/*:refs/*",
                cwd="repository")
            try:
                new_head = self._getHead("repository", "source")
            except (subprocess.CalledProcessError, GitProtocolError) as e2:
                self._logger.info("Unable to fetch default branch: %s" % e2)
                new_head = None
            self._runGit("remote", "rm", "source", cwd="repository")
            # XXX cjwatson 2016-11-03: For some reason "git remote rm"
            # doesn't actually remove the refs.
            self._deleteRefs("repository", "refs/remotes/source/**")
        except subprocess.CalledProcessError as e:
            self._logger.info("Unable to fetch remote repository: %s" % e)
            return CodeImportWorkerExitCode.FAILURE_INVALID
        self._logger.info("Pushing repository to hosting service.")
        try:
            if new_head is not None:
                # Push the target of HEAD first to ensure that it is always
                # available.
                self._runGit(
                    "push", target_url, "+%s:%s" % (new_head, new_head),
                    cwd="repository")
                try:
                    self._setHead(target_url, new_head)
                except GitProtocolError as e:
                    self._logger.info("Unable to set default branch: %s" % e)
            self._runGit("push", "--mirror", target_url, cwd="repository")
        except subprocess.CalledProcessError as e:
            self._logger.info(
                "Unable to push to hosting service: git push exited %s" %
                e.returncode)
            return CodeImportWorkerExitCode.FAILURE
        return CodeImportWorkerExitCode.SUCCESS
