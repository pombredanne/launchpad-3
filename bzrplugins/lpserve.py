# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bazaar plugin to run the smart server on Launchpad.

Cribbed from bzrlib.builtins.cmd_serve from Bazaar 0.16.
"""

__metaclass__ = type

__all__ = ['cmd_launchpad_server']


import os
import resource
import sys

from bzrlib.commands import Command, register_command
from bzrlib.option import Option
from bzrlib import lockdir, ui

from bzrlib.smart import medium, server
from bzrlib.transport import get_transport


class cmd_launchpad_server(Command):
    """Run a Bazaar server that maps Launchpad branch URLs to the internal
    file-system format.
    """

    aliases = ['lp-serve']

    takes_options = [
        Option('inet',
               help='serve on stdin/out for use from inetd or sshd'),
        Option('port',
               help='listen for connections on nominated port of the form '
                    '[hostname:]portnumber. Passing 0 as the port number will'
                    ' result in a dynamically allocated port. Default port is'
                    ' 4155.',
               type=str),
        Option('upload-directory',
               help='upload branches to this directory. Defaults to '
                    'config.codehosting.hosted_branches_root.',
               type=unicode),
        Option('mirror-directory',
               help='serve branches from this directory. Defaults to '
                    'config.codehosting.mirrored_branches_root.'),
        Option('codehosting-endpoint',
               help='the url of the internal XML-RPC server. Defaults to '
                    'config.codehosting.codehosting_endpoint.',
               type=unicode),
        ]

    takes_args = ['user_id']

    def get_smart_server(self, transport, port, inet):
        """Construct a smart server."""
        if inet:
            smart_server = medium.SmartServerPipeStreamMedium(
                sys.stdin, sys.stdout, transport)
        else:
            host = medium.BZR_DEFAULT_INTERFACE
            if port is None:
                port = medium.BZR_DEFAULT_PORT
            else:
                if ':' in port:
                    host, port = port.split(':')
                port = int(port)
            smart_server = server.SmartTCPServer(
                transport, host=host, port=port)
            print 'listening on port: ', smart_server.port
            sys.stdout.flush()
        return smart_server

    def run_server(self, smart_server):
        """Run the given smart server."""
        # for the duration of this server, no UI output is permitted.
        # note that this may cause problems with blackbox tests. This should
        # be changed with care though, as we dont want to use bandwidth
        # sending progress over stderr to smart server clients!
        old_factory = ui.ui_factory
        try:
            ui.ui_factory = ui.SilentUIFactory()
            smart_server.serve()
        finally:
            ui.ui_factory = old_factory

    def run(self, user_id, port=None, branch_directory=None,
            codehosting_endpoint_url=None, inet=False):
        from lp.codehosting.bzrutils import install_oops_handler
        from lp.codehosting.vfs import get_lp_server, hooks
        install_oops_handler(user_id)
        four_gig = int(4e9)
        resource.setrlimit(resource.RLIMIT_AS, (four_gig, four_gig))
        seen_new_branch = hooks.SetProcTitleHook()
        lp_server = get_lp_server(
            int(user_id), codehosting_endpoint_url, branch_directory,
            seen_new_branch.seen)
        lp_server.start_server()

        old_lockdir_timeout = lockdir._DEFAULT_TIMEOUT_SECONDS
        try:
            lp_transport = get_transport(lp_server.get_url())
            smart_server = self.get_smart_server(lp_transport, port, inet)
            lockdir._DEFAULT_TIMEOUT_SECONDS = 0
            self.run_server(smart_server)
        finally:
            lockdir._DEFAULT_TIMEOUT_SECONDS = old_lockdir_timeout
            lp_server.stop_server()


register_command(cmd_launchpad_server)


class cmd_test_named_outputs(Command):
    """Spawn a process that remaps stdin and stdout to named pipes.

    Report what those are onto stdout, but otherwise write nothing to stdout.
    """

    def run(self):
        from bzrlib import osutils, ui
        tempdir = osutils.mkdtemp(prefix='lpserve-')
        # self.add_cleanup for bzr >= 2.1
        try:
            sys.stdout.write('%s\n' % (tempdir,))
            stdin_name = os.path.join(tempdir, 'child_stdin')
            stdout_name = os.path.join(tempdir, 'child_stdout')
            stderr_name = os.path.join(tempdir, 'child_stderr')
            os.mkfifo(stdin_name)
            os.mkfifo(stdout_name)
            os.mkfifo(stderr_name)
            # OS_NDELAY/OS_NBLOCK?
            # Opening a fifo for reading/writing blocks until someone opens the
            # other end
            fd_out = os.open(stdout_name, os.O_WRONLY | osutils.O_BINARY)
            fd_in = os.open(stdin_name, os.O_RDONLY | osutils.O_BINARY)
            # Close the existing file handles, to make sure that they don't
            # accidentally get used.
            # Also, redirect everything to the new handles
            sys.stdin.close()
            sys.stdout.close()
            os.dup2(fd_in, 0)
            os.dup2(fd_out, 1)
            #sys.stderr.write('Opening stderr\n')
            # fd_err = os.open(stderr_name, os.O_WRONLY | osutils.O_BINARY)
            # os.dup2(fd_err, 2)
            # TODO: buffering?
            sys.stdin = os.fdopen(fd_in, 'rb')
            sys.stdout = os.fdopen(fd_out, 'wb')
            sys.stderr.write('ready for input\n')
            # TODO: reset ui.ui_factory if we need to
            #       reset self.outf if we need to
            #       Handle sys.stderr, I just didn't want to have to manually
            #       read from it right now
            # sys.stderr = os.fdopen(fd_err)
            # sys.stdout.write(sys.stderr.read())
            # sys.stderr.write('error')
            thebytes = sys.stdin.read()
            sys.stdout.write(thebytes)
            sys.stdout.flush()
            sys.stderr.write('wrote %d bytes\n' % (len(thebytes),))
            # os.write(fd_err, 'error')
            # sys.stderr.write('wrote %d bytes to error\n' % (len(thebytes),))
            # os.flush(fd_err)
            # sys.stderr.write('flushed %d bytes\n' % (len(thebytes),))
        finally:
            osutils.rmtree(tempdir)
            

register_command(cmd_test_named_outputs)
