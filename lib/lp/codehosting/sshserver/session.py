# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SSH session implementations for the codehosting SSH server."""

__metaclass__ = type
__all__ = [
    'launch_smart_server',
    ]

import os
import signal
import socket
import urlparse

from zope.event import notify
from zope.interface import implements

from twisted.internet import (
    error,
    fdesc,
    interfaces,
    main,
    process,
    )
from twisted.python import log

from canonical.config import config
from lp.codehosting import get_bzr_path
from lp.services.sshserver.events import AvatarEvent
from lp.services.sshserver.session import DoNothingSession


class BazaarSSHStarted(AvatarEvent):

    template = '[%(session_id)s] %(username)s started bzr+ssh session.'


class BazaarSSHClosed(AvatarEvent):

    template = '[%(session_id)s] %(username)s closed bzr+ssh session.'


class ForbiddenCommand(Exception):
    """Raised when a session is asked to execute a forbidden command."""


class _WaitForExit(process.ProcessReader):
    """Wait on a socket for the exit status."""

    def __init__(self, reactor, proc, sock):
        super(_WaitForExit, self).__init__(reactor, proc, 'exit',
                                           sock.fileno())
        self._sock = sock
        self.connected = 1

    def close(self):
        self._sock.close()

    def dataReceived(self, data):
        # This is the only thing we do differently from the standard
        # ProcessReader. When we get data on this socket, we need to treat it
        # as a return code, or a failure.
        if not data.startswith('exited'):
            # Bad data, we want to signal that we are closing the connection
            # TODO: How?
            # self.proc.?
            self.close()
            # I don't know what to put here if we get bogus data, but I *do*
            # want to say that the process is now considered dead to me
            log.err('Got invalid exit information: %r' % (data,))
            exit_status = (255 << 8)
        else:
            exit_status = int(data.split('\n')[1])
        self.proc.processEnded(exit_status)


class ForkedProcessTransport(process.BaseProcess):
    """Wrap the forked process in a ProcessTransport so we can talk to it.

    Note that instantiating the class creates the fork and sets it up in the
    reactor.
    """

    implements(interfaces.IProcessTransport)

    # Design decisions
    # [Decision #a]
    #   Inherit from process.BaseProcess
    #       This seems slightly risky, as process.BaseProcess is actually
    #       imported from twisted.internet._baseprocess.BaseProcess. The
    #       real-world Process then actually inherits from process._BaseProcess
    #       I've also had to copy a fair amount from the actual Process
    #       command.
    #       One option would be to inherit from process.Process, and just
    #       override stuff like __init__ and reapProcess which I don't want to
    #       do in the same way. (Is it ok not to call your Base classes
    #       __init__ if you don't want to do that exact work?)
    # [Decision #b]
    #   prefork vs max children vs ?
    # 

    # TODO: process._BaseProcess implements 'reapProcess' as an ability. Which
    #       then tries to 'os.waitpid()' on the given file handle. Testing
    #       shows that calling waitpid() on a pid that isn't a *direct* child
    #       fails. (Even if it is a grandchild). So we intentionally do not
    #       implement it. However the forking service reaps its own zombie
    #       children, so we should be ok.
    # TODO: It looks like we want to be able to pass along at least BZR_EMAIL
    #       to the fork request
    def __init__(self, reactor, executable, args, proto):
        process.BaseProcess.__init__(self, proto)
        self.pipes = {}
        pid, path, sock = self._spawn(executable, args)
        self._fifo_path = path
        self.pid = pid
        # TODO: We nee to set up a Reader on this socket, so that we know when
        #       the process has actually closed. The possible actions are:
        #       a) sock closes (say master process has exited), in which case
        #          we probably treat this as a 'process has exited' flag
        #       b) we get data, which if it conforms to our expectations means
        #          the process *has* exited. We probably need to be aware of
        #          whether we get the expected 'fifo has closed' on the other
        #          file descriptors
        #       Either way, when stuff happens on the socket, we should be
        #       prepared to call self.processEnded(), though I'm a bit confused
        #       with processEnded, maybeCallProcessEnded and processExited...
        self.process_sock = sock
        # Map from standard file descriptor to the associated pipe
        self._fifo_path = path
        self._connectSpawnToReactor(reactor)
        if self.proto is not None:
            self.proto.makeConnection(self)

    def _sendMessageToService(self, message):
        """Send a message to the Forking service and get the response"""
        # TODO: Config entries for what port this will be found in?
        DEFAULT_SERVICE_PORT = 4156
        addrs = socket.getaddrinfo('127.0.0.1', DEFAULT_SERVICE_PORT,
            socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        (family, socktype, proto, canonname, sockaddr) = addrs[0]
        client_sock = socket.socket(family, socktype, proto)
        log.msg('Connecting to Forking Service @ port: %d for %r'
                % (DEFAULT_SERVICE_PORT, message))
        # TODO: How do we do logging in this codebase?
        try:
            client_sock.connect(sockaddr)
            client_sock.sendall(message)
            # We define the requests to be no bigger than 1kB. (For now)
            response = client_sock.recv(1024)
        except socket.error, e:
            # TODO: What exceptions should be raised?
            #       Raising the raw exception seems to kill the twisted reactor
            #       Note that if the connection is refused, we *could* just
            #       fall back on a regular 'spawnProcess' call.
            log.err('Connection failed: %s' % (e,))
            raise
        if response.startswith("FAILURE"):
            raise RuntimeError('Failed to send message: %r' % (response,))
        return response, client_sock

    def _spawn(self, executable, args):
        assert executable == 'bzr', executable # Maybe .endswith()
        assert args[0] == 'bzr', args[0]
        # XXX: We must send BZR_EMAIL to the process, or we get failures to
        #      run because of no 'whoami' information.
        response, sock = self._sendMessageToService('fork %s\n'
                                                    % ' '.join(args[1:]))
        ok, pid, path, tail = response.split('\n')
        assert ok == 'ok'
        assert tail == ''
        pid = int(pid)
        # TODO: Log this information
        return pid, path, sock

    def _connectSpawnToReactor(self, reactor):
        stdin_path = os.path.join(self._fifo_path, 'stdin')
        stdout_path = os.path.join(self._fifo_path, 'stdout')
        stderr_path = os.path.join(self._fifo_path, 'stderr')
        child_stdin_fd = os.open(stdin_path, os.O_WRONLY)
        self.pipes[0] = process.ProcessWriter(reactor, self, 0, child_stdin_fd)
        child_stdout_fd = os.open(stdout_path, os.O_RDONLY)
        # TODO: forceReadHack=True ? Used in process.py
        self.pipes[1] = process.ProcessReader(reactor, self, 1, child_stdout_fd)
        child_stderr_fd = os.open(stderr_path, os.O_RDONLY)
        self.pipes[2] = process.ProcessReader(reactor, self, 2, child_stderr_fd)
        # TODO: gc cycle, _exiter points to self, and we point to _exiter
        self._exiter = _WaitForExit(reactor, self, self.process_sock)
        self.pipes['exit'] = self._exiter

    def _getReason(self, status):
        # Copied from twisted.internet.process._BaseProcess
        exitCode = sig = None
        if os.WIFEXITED(status):
            exitCode = os.WEXITSTATUS(status)
        else:
            sig = os.WTERMSIG(status)
        if exitCode or sig:
            return error.ProcessTerminated(exitCode, sig, status)
        return error.ProcessDone(status)

    def signalProcess(self, signalID):
        """
        Send the given signal C{signalID} to the process. It'll translate a
        few signals ('HUP', 'STOP', 'INT', 'KILL', 'TERM') from a string
        representation to its int value, otherwise it'll pass directly the
        value provided

        @type signalID: C{str} or C{int}
        """
        # Copied from twisted.internet.process._BaseProcess
        if signalID in ('HUP', 'STOP', 'INT', 'KILL', 'TERM'):
            signalID = getattr(signal, 'SIG%s' % (signalID,))
        if self.pid is None:
            raise process.ProcessExitedAlready()
        os.kill(self.pid, signalID)

    # Implemented because conch.ssh.session uses it, the Process implementation
    # ignores writes if channel '0' is not available
    def write(self, data):
        self.pipes[0].write(data)

    def writeToChild(self, childFD, data):
        # Copied from twisted.internet.process.Process
        self.pipes[childFD].write(data)

    def closeChildFD(self, childFD):
        if childFD in self.pipes:
            self.pipes[childFD].loseConnection()

    def closeStdin(self):
        self.closeChildFD(0)

    def closeStdout(self):
        self.closeChildFD(1)

    def closeStderr(self):
        self.closeChildFD(2)

    def loseConnection(self):
        self.closeStdin()
        self.closeStdout()
        self.closeStderr()


    # Implemented because ProcessWriter/ProcessReader want to call it
    # Copied from twisted.internet.Process
    def childDataReceived(self, name, data):
        self.proto.childDataReceived(name, data)

    # Implemented because ProcessWriter/ProcessReader want to call it
    # Copied from twisted.internet.Process
    def childConnectionLost(self, childFD, reason):
        close = getattr(self.pipes[childFD], 'close', None)
        if close is not None:
            close()
        else:
            os.close(self.pipes[childFD].fileno())
        del self.pipes[childFD]
        try:
            self.proto.childConnectionLost(childFD)
        except:
            log.err()
        self.maybeCallProcessEnded()

    # Implemented because of childConnectionLost
    # Adapted from twisted.internet.Process
    # Note: Process.maybeCallProcessEnded() tries to reapProcess() at this
    #       point, but the daemon will be doing the reaping for us (we can't
    #       because the process isn't a direct child.)
    def maybeCallProcessEnded(self):
        if self.pipes:
            # Not done if we still have open pipes
            return
        if not self.lostProcess:
            return
        process.BaseProcess.maybeCallProcessEnded(self)

    # pauseProducing, present in process.py, not a IProcessTransport interface
    # childDataReceived, childConnectionLost, etc, etc.


class ExecOnlySession(DoNothingSession):
    """Conch session that only allows executing commands."""

    def __init__(self, avatar, reactor, environment=None):
        super(ExecOnlySession, self).__init__(avatar)
        self.reactor = reactor
        self.environment = environment
        self._transport = None

    @classmethod
    def getAvatarAdapter(klass, environment=None):
        from twisted.internet import reactor
        return lambda avatar: klass(avatar, reactor, environment)

    def closed(self):
        """See ISession."""
        if self._transport is not None:
            # XXX: JonathanLange 2010-04-15: This is something of an
            # abstraction violation. Apart from this line and its twin, this
            # class knows nothing about Bazaar.
            notify(BazaarSSHClosed(self.avatar))
            try:
                self._transport.signalProcess('HUP')
            except (OSError, process.ProcessExitedAlready):
                pass
            self._transport.loseConnection()

    def eofReceived(self):
        """See ISession."""
        if self._transport is not None:
            self._transport.closeStdin()

    def execCommand(self, protocol, command):
        """Executes `command` using `protocol` as the ProcessProtocol.

        See ISession.

        :param protocol: a ProcessProtocol, usually SSHSessionProcessProtocol.
        :param command: A whitespace-separated command line. The first token is
        used as the name of the executable, the rest are used as arguments.
        """
        # XXX: What do do with the protocol argument? It implements
        #      IProcessProtocol, which is how the process gets spawned, but we
        #      are intentionally overriding that. Are we supposed to be
        #      implementing a custom IProcessProtocol, and
        #      installing/registering that higher up?
        try:
            executable, arguments = self.getCommandToRun(command)
        except ForbiddenCommand, e:
            self.errorWithMessage(protocol, str(e) + '\r\n')
            return
        log.msg('Running: %r, %r' % (executable, arguments))
        if self._transport is not None:
            log.err(
                "ERROR: %r already running a command on transport %r"
                % (self, self._transport))
        # XXX: JonathanLange 2008-12-23: This is something of an abstraction
        # violation. Apart from this line and its twin, this class knows
        # nothing about Bazaar.
        notify(BazaarSSHStarted(self.avatar))
        if executable == 'bzr': # Endswith?
            self._transport = ForkedProcessTransport(self.reactor, executable,
                                                     arguments, protocol)
        else:
            self._transport = self.reactor.spawnProcess(
                protocol, executable, arguments, env=self.environment)

    def getCommandToRun(self, command):
        """Return the command that will actually be run given `command`.

        :param command: A command line to run.
        :return: `(executable, arguments)` where `executable` is the name of an
            executable and arguments is a sequence of command-line arguments
            with the name of the executable as the first value.
        """
        args = command.split()
        return args[0], args


class RestrictedExecOnlySession(ExecOnlySession):
    """Conch session that only allows a single command to be executed."""

    def __init__(self, avatar, reactor, allowed_command,
                 executed_command_template, environment=None):
        """Construct a RestrictedExecOnlySession.

        :param avatar: See `ExecOnlySession`.
        :param reactor: See `ExecOnlySession`.
        :param allowed_command: The sole command that can be executed.
        :param executed_command_template: A Python format string for the actual
            command that will be run. '%(user_id)s' will be replaced with the
            'user_id' attribute of the current avatar.
        """
        ExecOnlySession.__init__(self, avatar, reactor, environment)
        self.allowed_command = allowed_command
        self.executed_command_template = executed_command_template

    @classmethod
    def getAvatarAdapter(klass, allowed_command, executed_command_template,
                         environment=None):
        from twisted.internet import reactor
        return lambda avatar: klass(
            avatar, reactor, allowed_command, executed_command_template,
            environment)

    def getCommandToRun(self, command):
        """As in ExecOnlySession, but only allow a particular command.

        :raise ForbiddenCommand: when `command` is not the allowed command.
        """
        if command != self.allowed_command:
            raise ForbiddenCommand("Not allowed to execute %r." % (command,))
        return ExecOnlySession.getCommandToRun(
            self, self.executed_command_template
            % {'user_id': self.avatar.user_id})


def launch_smart_server(avatar):
    from twisted.internet import reactor

    command = (
        "bzr lp-serve --inet %(user_id)s"
        )

    environment = dict(os.environ)

    # Extract the hostname from the supermirror root config.
    hostname = urlparse.urlparse(config.codehosting.supermirror_root)[1]
    environment['BZR_EMAIL'] = '%s@%s' % (avatar.username, hostname)
    return RestrictedExecOnlySession(
        avatar,
        reactor,
        'bzr serve --inet --directory=/ --allow-writes',
        command,
        environment=environment)
