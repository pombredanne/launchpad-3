# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Server classes that know how to create various kinds of foreign archive."""

__all__ = [
    'CVSServer',
    'GitServer',
    'MercurialServer',
    'SubversionServer',
    ]

__metaclass__ = type

import os
import shutil
import signal
import subprocess
import tempfile
import time

from bzrlib.tests.treeshape import build_tree_contents
from bzrlib.transport import Server
from bzrlib.urlutils import (
    escape,
    join as urljoin,
    )
import CVS
from dulwich.repo import Repo as GitRepo
import pysvn
import svn_oo

from canonical.launchpad.scripts.logger import QuietFakeLogger


def local_path_to_url(local_path):
    """Return a file:// URL to `local_path`.

    This implementation is unusual in that it returns a file://localhost/ URL.
    This is to work around the valid_vcs_details constraint on CodeImport.
    """
    return 'file://localhost' + escape(
        os.path.normpath(os.path.abspath(local_path)))


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

    def __init__(self, repository_path, use_svn_serve=False):
        super(SubversionServer, self).__init__()
        self.repository_path = os.path.abspath(repository_path)
        self._use_svn_serve = use_svn_serve

    def createRepository(self, path):
        """Create a Subversion repository at `path`."""
        svn_oo.Repository.Create(path, QuietFakeLogger())

    def get_url(self):
        """Return a URL to the Subversion repository."""
        if self._use_svn_serve:
            return 'svn://localhost/'
        else:
            return local_path_to_url(self.repository_path)

    def start_server(self):
        super(SubversionServer, self).start_server()
        self.createRepository(self.repository_path)
        if self._use_svn_serve:
            conf_path = os.path.join(
                self.repository_path, 'conf/svnserve.conf')
            with open(conf_path , 'w') as conf_file:
                conf_file.write('[general]\nanon-access = write\n')
            self._svnserve = subprocess.Popen(
                ['svnserve', '--daemon', '--foreground', '--root',
                 self.repository_path])
            delay = 0.1
            for i in range(10):
                try:
                    client = pysvn.Client()
                    client.ls(self.get_url())
                except pysvn.ClientError, e:
                    if 'Connection refused' in str(e):
                        time.sleep(delay)
                        delay *= 1.5
                        continue
                else:
                    break
            else:
                raise AssertionError(
                    "svnserve didn't start accepting connections")

    def stop_server(self):
        super(SubversionServer, self).stop_server()
        if self._use_svn_serve:
            os.kill(self._svnserve.pid, signal.SIGINT)
            self._svnserve.communicate()

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
        return CVS.init(path, QuietFakeLogger())

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

    def start_server(self):
        # Initialize the repository.
        super(CVSServer, self).start_server()
        self._repository = self.createRepository(self._repository_path)


class GitServer(Server):

    def __init__(self, repo_url):
        super(GitServer, self).__init__()
        self.repo_url = repo_url

    def makeRepo(self, tree_contents):
        from bzrlib.plugins.git.tests import GitBranchBuilder
        wd = os.getcwd()
        try:
            os.chdir(self.repo_url)
            GitRepo.init(".")
            builder = GitBranchBuilder()
            for filename, contents in tree_contents:
                builder.set_file(filename, contents, False)
            builder.commit('Joe Foo <joe@foo.com>', u'<The commit message>')
            builder.finish()
        finally:
            os.chdir(wd)


class MercurialServer(Server):

    def __init__(self, repo_url):
        super(MercurialServer, self).__init__()
        self.repo_url = repo_url

    def makeRepo(self, tree_contents):
        from mercurial.ui import ui
        from mercurial.localrepo import localrepository
        repo = localrepository(ui(), self.repo_url, create=1)
        for filename, contents in tree_contents:
            f = open(os.path.join(self.repo_url, filename), 'w')
            try:
                f.write(contents)
            finally:
                f.close()
            repo[None].add([filename])
        repo.commit(text='<The commit message>', user='jane Foo <joe@foo.com>')
