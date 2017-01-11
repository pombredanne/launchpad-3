# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Server classes that know how to create various kinds of foreign archive."""

__all__ = [
    'BzrServer',
    'CVSServer',
    'GitServer',
    'SubversionServer',
    ]

__metaclass__ = type

from cStringIO import StringIO
import errno
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
from wsgiref.simple_server import make_server

from bzrlib.branch import Branch
from bzrlib.branchbuilder import BranchBuilder
from bzrlib.bzrdir import BzrDir
from bzrlib.tests.test_server import (
    ReadonlySmartTCPServer_for_testing,
    TestServer,
    )
from bzrlib.tests.treeshape import build_tree_contents
from bzrlib.transport import Server
from bzrlib.urlutils import (
    escape,
    join as urljoin,
    )
import CVS
from dulwich.errors import NotGitRepository
import dulwich.index
from dulwich.objects import Blob
from dulwich.repo import Repo as GitRepo
from dulwich.server import (
    Backend,
    Handler,
    )
from dulwich.web import (
    GunzipFilter,
    handle_service_request,
    HTTPGitApplication,
    LimitedInputFilter,
    WSGIRequestHandlerLogger,
    WSGIServerLogger,
    )
from subvertpy import SubversionException
import subvertpy.ra
import subvertpy.repos

from lp.services.log.logger import BufferLogger


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

    def _get_ra(self, url):
        return subvertpy.ra.RemoteAccess(url,
            auth=subvertpy.ra.Auth([subvertpy.ra.get_username_provider()]))

    def createRepository(self, path):
        """Create a Subversion repository at `path`."""
        subvertpy.repos.create(path)

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
            with open(conf_path, 'w') as conf_file:
                conf_file.write('[general]\nanon-access = write\n')
            self._svnserve = subprocess.Popen(
                ['svnserve', '--daemon', '--foreground', '--threads',
                 '--root', self.repository_path])
            delay = 0.1
            for i in range(10):
                try:
                    try:
                        self._get_ra(self.get_url())
                    except OSError as e:
                        # Subversion < 1.9 just produces OSError.
                        if e.errno == errno.ECONNREFUSED:
                            time.sleep(delay)
                            delay *= 1.5
                            continue
                        raise
                    except SubversionException as e:
                        # Subversion >= 1.9 turns the raw error into a
                        # SubversionException.  The code is
                        # SVN_ERR_RA_CANNOT_CREATE_SESSION, which is not yet
                        # in subvertpy.
                        if e.args[1] == 170013:
                            time.sleep(delay)
                            delay *= 1.5
                            continue
                        raise
                    else:
                        break
                except Exception as e:
                    self._kill_svnserve()
                    raise
            else:
                self._kill_svnserve()
                raise AssertionError(
                    "svnserve didn't start accepting connections")

    def _kill_svnserve(self):
        os.kill(self._svnserve.pid, signal.SIGINT)
        self._svnserve.communicate()

    def stop_server(self):
        super(SubversionServer, self).stop_server()
        if self._use_svn_serve:
            self._kill_svnserve()

    def makeBranch(self, branch_name, tree_contents):
        """Create a branch on the Subversion server called `branch_name`.

        :param branch_name: The name of the branch to create.
        :param tree_contents: The contents of the module. This is a list of
            tuples of (relative filename, file contents).
        """
        branch_url = self.makeDirectory(branch_name)
        ra = self._get_ra(branch_url)
        editor = ra.get_commit_editor({"svn:log": "Import"})
        root = editor.open_root()
        for filename, content in tree_contents:
            f = root.add_file(filename)
            try:
                subvertpy.delta.send_stream(StringIO(content),
                    f.apply_textdelta())
            finally:
                f.close()
        root.close()
        editor.close()
        return branch_url

    def makeDirectory(self, directory_name, commit_message=None):
        """Make a directory on the repository."""
        if commit_message is None:
            commit_message = 'Make %r' % (directory_name,)
        ra = self._get_ra(self.get_url())
        editor = ra.get_commit_editor({"svn:log": commit_message})
        root = editor.open_root()
        root.add_directory(directory_name).close()
        root.close()
        editor.close()
        return urljoin(self.get_url(), directory_name)


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
        return CVS.init(path, BufferLogger())

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


class GitStoreBackend(Backend):
    """A backend that looks up repositories under a store directory."""

    def __init__(self, root):
        self.root = root

    def open_repository(self, path):
        full_path = os.path.normpath(os.path.join(self.root, path.lstrip("/")))
        if not full_path.startswith(self.root + "/"):
            raise NotGitRepository("Repository %s not under store" % path)
        return GitRepo(full_path)


class TurnipSetSymbolicRefHandler(Handler):
    """Dulwich protocol handler for setting a symbolic ref.

    Transcribed from turnip.pack.git.PackBackendProtocol.
    """

    def __init__(self, backend, args, proto, http_req=None):
        super(TurnipSetSymbolicRefHandler, self).__init__(
            backend, proto, http_req=http_req)
        self.repo = backend.open_repository(args[0])

    def handle(self):
        line = self.proto.read_pkt_line()
        if line is None:
            self.proto.write_pkt_line(b"ERR Invalid set-symbolic-ref-line\n")
            return
        name, target = line.split(b" ", 1)
        if name != b"HEAD":
            self.proto.write_pkt_line(
                b'ERR Symbolic ref name must be "HEAD"\n')
            return
        if target.startswith(b"-"):
            self.proto.write_pkt_line(
                b'ERR Symbolic ref target may not start with "-"\n')
            return
        try:
            self.repo.refs.set_symbolic_ref(name, target)
        except Exception as e:
            self.proto.write_pkt_line(b'ERR %s\n' % e)
        else:
            self.proto.write_pkt_line(b'ACK %s\n' % name)


class HTTPGitServerThread(threading.Thread):
    """Thread that runs an HTTP Git server."""

    def __init__(self, backend, address, port=None):
        super(HTTPGitServerThread, self).__init__()
        self.setName("HTTP Git server on %s:%s" % (address, port))
        app = HTTPGitApplication(
            backend,
            handlers={'turnip-set-symbolic-ref': TurnipSetSymbolicRefHandler})
        app.services[('POST', re.compile('/turnip-set-symbolic-ref$'))] = (
            handle_service_request)
        app = GunzipFilter(LimitedInputFilter(app))
        self.server = make_server(
            address, port, app, handler_class=WSGIRequestHandlerLogger,
            server_class=WSGIServerLogger)

    def run(self):
        self.server.serve_forever()

    def get_address(self):
        return self.server.server_address

    def stop(self):
        self.server.shutdown()


class GitServer(Server):

    def __init__(self, repository_store, use_server=False):
        super(GitServer, self).__init__()
        self.repository_store = repository_store
        self._use_server = use_server

    def get_url(self, repository_name):
        """Return a URL to the Git repository."""
        if self._use_server:
            host, port = self._server.get_address()
            return 'http://%s:%d/%s' % (host, port, repository_name)
        else:
            return local_path_to_url(
                os.path.join(self.repository_store, repository_name))

    def createRepository(self, path, bare=False):
        if bare:
            GitRepo.init_bare(path)
        else:
            GitRepo.init(path)

    def start_server(self):
        super(GitServer, self).start_server()
        if self._use_server:
            self._server = HTTPGitServerThread(
                GitStoreBackend(self.repository_store), "localhost", 0)
            self._server.start()

    def stop_server(self):
        super(GitServer, self).stop_server()
        if self._use_server:
            self._server.stop()

    def makeRepo(self, repository_name, tree_contents):
        repository_path = os.path.join(self.repository_store, repository_name)
        os.makedirs(repository_path)
        self.createRepository(repository_path, bare=self._use_server)
        repo = GitRepo(repository_path)
        blobs = [
            (Blob.from_string(contents), filename) for (filename, contents)
            in tree_contents]
        repo.object_store.add_objects(blobs)
        root_id = dulwich.index.commit_tree(repo.object_store, [
            (filename, b.id, stat.S_IFREG | 0o644)
            for (b, filename) in blobs])
        repo.do_commit(committer='Joe Foo <joe@foo.com>',
            message=u'<The commit message>', tree=root_id)


class BzrServer(Server):

    def __init__(self, repository_path, use_server=False):
        super(BzrServer, self).__init__()
        self.repository_path = repository_path
        self._use_server = use_server

    def createRepository(self, path):
        BzrDir.create_branch_convenience(path)

    def makeRepo(self, tree_contents):
        branch = Branch.open(self.repository_path)
        branch.get_config().set_user_option("create_signatures", "never")
        builder = BranchBuilder(branch=branch)
        actions = [('add', ('', 'tree-root', 'directory', None))]
        actions += [
            ('add', (path, path + '-id', 'file', content))
            for (path, content) in tree_contents]
        builder.build_snapshot(
            None, None, actions, committer='Joe Foo <joe@foo.com>',
                message=u'<The commit message>')

    def get_url(self):
        if self._use_server:
            return self._bzrserver.get_url()
        else:
            return local_path_to_url(self.repository_path)

    def start_server(self):
        super(BzrServer, self).start_server()
        self.createRepository(self.repository_path)

        class LocalURLServer(TestServer):
            def __init__(self, repository_path):
                self.repository_path = repository_path

            def start_server(self):
                pass

            def get_url(self):
                return local_path_to_url(self.repository_path)

        if self._use_server:
            self._bzrserver = ReadonlySmartTCPServer_for_testing()
            self._bzrserver.start_server(
                LocalURLServer(self.repository_path))

    def stop_server(self):
        super(BzrServer, self).stop_server()
        if self._use_server:
            self._bzrserver.stop_server()
