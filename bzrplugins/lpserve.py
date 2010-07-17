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
            # OS_NDELAY/OS_NONBLOCK?
            # Opening a fifo for reading/writing blocks until someone opens the
            # other end
            fd_in = os.open(stdin_name, os.O_RDONLY | osutils.O_BINARY)
            fd_out = os.open(stdout_name, os.O_WRONLY | osutils.O_BINARY)
            # TODO: self.add_cleanup(os.close, fd_in)
            # TODO: self.add_cleanup(os.close, fd_out)
            # TODO: self.add_cleanup(os.close, fd_err)
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


class cmd_trivial_forwarder(Command):
    """Take the path given and forward pipes back to stdin/out/err."""

    _timeout = 10000
    _buf_size = 5

    takes_args = ['base_path']

    def run(self, base_path):
        import select
        from bzrlib import osutils, ui

        stdin_path = os.path.join(base_path, 'child_stdin')
        stdout_path = os.path.join(base_path, 'child_stdout')
        stderr_path = os.path.join(base_path, 'child_stderr')

        in_buffer = []
        out_buffer = []
        err_buffer = []

        poller = select.poll()
        fd_in = sys.stdin.fileno()
        poller.register(fd_in, select.POLLIN)
        fd_out = sys.stdout.fileno()
        # poller.register(fd_out)
        # fd_err = sys.stderr.fileno()
        # poller.register(fd_err)
        sys.stderr.write('opening %s\n' % (stdin_path,))
        fd_child_in = os.open(stdin_path,
            os.O_WRONLY | osutils.O_BINARY | os.O_NONBLOCK)
        # poller.register(fd_child_in)
        sys.stderr.write('opening %s\n' % (stdout_path,))
        fd_child_out = os.open(stdout_path,
            os.O_RDONLY | osutils.O_BINARY | os.O_NONBLOCK)
        poller.register(fd_child_out, select.POLLIN)
        # fd_child_err = os.open(stdout_path, os.O_RDONLY | osutils.O_BINARY)
        # poller.register(fd_child_err)
        in_to_out = {}
        in_to_out[fd_in] = fd_child_in
        in_to_out[fd_child_out] = fd_out
        inout_to_buffer = {}
        inout_to_buffer[fd_in] = in_buffer
        inout_to_buffer[fd_child_in] = in_buffer
        inout_to_buffer[fd_out] = out_buffer
        inout_to_buffer[fd_child_out] = out_buffer
        should_close = set()
        while True:
            events = poller.poll(self._timeout) # TIMEOUT?
            if not events:
                sys.stderr.write('** timeout\n')
                # TODO: check if all buffers are indicated 'closed' so we
                #       should exit
                continue
            for fd, event in events:
                sys.stderr.write('event: %s %s\n' % (fd, event))
                if event & select.POLLIN:
                    # Register the output buffer, buffer a bit, and wait for
                    # the output to be available
                    buf = inout_to_buffer[fd]
                    # TODO: We could set a maximum size for buf, and if we go
                    #       beyond that, we stop reading
                    # n_buffered = sum(map(len, buf))
                    thebytes = os.read(fd, self._buf_size)
                    buf.append(thebytes)
                    out_fd = in_to_out[fd]
                    sys.stderr.write('%d read %d => %d register %d\n'
                                     % (fd, len(thebytes), sum(map(len, buf)),
                                        out_fd))
                    # Let the poller know that we need to do non-blocking output
                    # We always re-register, we could know that it is already
                    # active
                    poller.register(out_fd, select.POLLOUT)
                elif event & select.POLLOUT:
                    # We can write some bytes without blocking, do so
                    buf = inout_to_buffer[fd]
                    if not buf:
                        # the buffer is now empty, we have written everything
                        # so unregister this buffer so we don't keep polling
                        # for the ability to write without blocking
                        sys.stderr.write('%d unregistered\n' % (fd,))
                        poller.unregister(fd)
                        # Check to see if the input has been closed, and close
                        # if true
                        if fd in should_close:
                            os.close(fd)
                        continue
                    thebytes = ''.join(buf)
                    n_written = os.write(fd, thebytes)
                    thebytes = thebytes[n_written:]
                    sys.stderr.write('%d wrote %d => %d remain\n'
                                     % (fd, n_written, len(thebytes)))
                    if thebytes:
                        buf[:] = [thebytes]
                    else:
                        del buf[:]
                        # We *could* unregister the output here, but I have the
                        # feeling waiting for another poll loop will be better
                        # because it will avoid looping, oh we have bytes,
                        # register, loop, find bytes, write them, unregister,
                        # loop, find more bytes, register, loop, etc.
                        # I don't know for sure, but I think this gives us at
                        # least a chance to have more bytes to write before we
                        # unregister
                elif event & select.POLLHUP:
                    # The connection hung up, I'm assuming these only occur on
                    # the inputs for now..., but carry across the action.
                    # Importantly, we don't close the out_fd yet, because we
                    # want to flush the buffer first
                    poller.unregister(fd)
                    out_fd = in_to_out[fd]
                    should_close.add(out_fd)
                    sys.stderr.write('%d closed, closing %d\n'
                                     % (fd, out_fd))

register_command(cmd_trivial_forwarder)
