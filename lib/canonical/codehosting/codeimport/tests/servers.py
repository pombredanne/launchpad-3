# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Server classes that know how to create various kinds of foreign archive."""

__all__ = [
    'CVSServer',
    'GitServer',
    'SubversionServer',
    ]

__metaclass__ = type

import logging
import os
import shutil
import tempfile

import CVS
import pysvn
import svn_oo

from bzrlib.urlutils import escape, join as urljoin
from bzrlib.transport import Server
from bzrlib.tests.treeshape import build_tree_contents


def local_path_to_url(local_path):
    """Return a file:// URL to `local_path`.

    This implementation is unusual in that it returns a file://localhost/ URL.
    This is to work around the valid_vcs_details constraint on CodeImport.
    """
    return 'file://localhost' + escape(
        os.path.normpath(os.path.abspath(local_path)))


def _make_silent_logger():
    """Create a logger that prints nothing."""

    class SilentLogHandler(logging.Handler):
        def emit(self, record):
            pass

    logger = logging.Logger("collector")
    handler = SilentLogHandler()
    logger.addHandler(handler)
    return logger


def run_in_temporary_directory(function):
    """Decorate `function` to be run in a temporary directory.

    Creates a new temporary directory and changes to it for the duration of
    `function`.
    """

    def decorated(*args, **kwargs):
        old_cwd = os.getcwd()
        new_dir = tempfile.mkdtemp()
        os.chdir(new_dir)
        try:
            return function(*args, **kwargs)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(new_dir)

    decorated.__name__ = function.__name__
    decorated.__doc__ = function.__doc__
    return decorated


class SubversionServer(Server):
    """A controller for an Subversion repository, used for testing."""

    def __init__(self, repository_path):
        super(SubversionServer, self).__init__()
        self.repository_path = os.path.abspath(repository_path)

    def createRepository(self, path):
        """Create a Subversion repository at `path`."""
        svn_oo.Repository.Create(path, _make_silent_logger())

    def get_url(self):
        """Return a URL to the Subversion repository."""
        return local_path_to_url(self.repository_path)

    def setUp(self):
        super(SubversionServer, self).setUp()
        self.createRepository(self.repository_path)

    @run_in_temporary_directory
    def makeBranch(self, branch_name, tree_contents):
        """Create a branch on the Subversion server called `branch_name`.

        :param branch_name: The name of the branch to create.
        :param tree_contents: The contents of the module. This is a list of
            tuples of (relative filename, file contents).
        """
        branch_url = self.makeDirectory(branch_name)
        client = pysvn.Client()
        branch_path = os.path.abspath(branch_name)
        client.checkout(branch_url, branch_path)
        build_tree_contents(
            [(os.path.join(branch_path, filename), content)
             for filename, content in tree_contents])
        client.add(
            [os.path.join(branch_path, filename)
             for filename in os.listdir(branch_path)
             if not filename.startswith('.')], recurse=True)
        client.checkin(branch_path, 'Import', recurse=True)
        return branch_url

    def makeDirectory(self, directory_name, commit_message=None):
        """Make a directory on the repository."""
        if commit_message is None:
            commit_message = 'Make %r' % (directory_name,)
        url = urljoin(self.get_url(), directory_name)
        client = pysvn.Client()
        client.mkdir(url, commit_message)
        return url


class CVSServer(Server):
    """A CVS server for testing."""

    def __init__(self, repository_path):
        """Construct a `CVSServer`.

        :param repository_path: The path to the directory that will contain
            the CVS repository.
        """
        super(CVSServer, self).__init__()
        self._repository_path = os.path.abspath(repository_path)

    def createRepository(self, path):
        """Create a CVS repository at `path`.

        :param path: The local path to create a repository in.
        :return: A CVS.Repository`.
        """
        return CVS.init(path, _make_silent_logger())

    def getRoot(self):
        """Return the CVS root for this server."""
        return self._repository_path

    @run_in_temporary_directory
    def makeModule(self, module_name, tree_contents):
        """Create a module on the CVS server called `module_name`.

        A 'module' in CVS roughly corresponds to a project.

        :param module_name: The name of the module to create.
        :param tree_contents: The contents of the module. This is a list of
            tuples of (relative filename, file contents).
        """
        build_tree_contents(tree_contents)
        self._repository.Import(
            module=module_name, log="import", vendor="vendor",
            release=['release'], dir='.')

    def setUp(self):
        # Initialize the repository.
        super(CVSServer, self).setUp()
        self._repository = self.createRepository(self._repository_path)


class GitServer(Server):

    def __init__(self, repo_url):
        self.repo_url = repo_url

    def makeRepo(self, tree_contents):
        from bzrlib.plugins.git.tests import GitBranchBuilder, run_git
        wd = os.getcwd()
        try:
            os.chdir(self.repo_url)
            run_git('init')
            builder = GitBranchBuilder()
            for filename, contents in tree_contents:
                builder.set_file(filename, contents, False)
            builder.commit('Joe Foo <joe@foo.com>', u'<The commit message>')
            builder.finish()
        finally:
            os.chdir(wd)
