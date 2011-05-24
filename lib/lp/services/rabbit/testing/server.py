# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test server fixtures for RabbitMQ."""

__metaclass__ = type

__all__ = [
    "RabbitServer",
    ]

import errno
import itertools
import os
import re
import socket
import subprocess
from textwrap import dedent
import sys
import time

from amqplib import client_0_8 as amqp
from fixtures import (
    EnvironmentVariableFixture,
    Fixture,
    TempDir,
    )
from testtools.content import (
    Content,
    content_from_file,
    )
from testtools.content_type import UTF8_TEXT

# The default binaries have a check that the running use is uid 0 or uname
# 'rabbitmq', neither of which are needed to operate correctly. So we run the
# actual erlang binaries.
RABBITBIN = "/usr/lib/rabbitmq/bin"


# def setup_exchange(conf, port):
#     """ create an exchange """
#     # Not ported yet.
#     conn = _get_connection(conf, port)
#     # see if we already have the exchange
#     must_create = False
#     chan = conn.channel()
#     try:
#         chan.exchange_declare(exchange=conf.exchange_name + BRANCH_NICK,
#                               type=conf.exchange_type, passive=True)
#     except (amqp.AMQPConnectionException, amqp.AMQPChannelException), e:
#         if e.amqp_reply_code == 404:
#             must_create = True
#             # amqplib kills the channel on error.... we dispose of it too
#             chan.close()
#             chan = conn.channel()
#         else:
#             raise
#     # now create the exchange if needed
#     if must_create:
#         chan.exchange_declare(exchange=conf.exchange_name + BRANCH_NICK,
#                               type=conf.exchange_type,
#                               durable=True, auto_delete=False,)
#         print "Created new exchange %s (%s)" % (
#             conf.exchange_name + BRANCH_NICK, conf.exchange_type)
#     else:
#         print "Exchange %s (%s) is already declared" % (
#             conf.exchange_name + BRANCH_NICK, conf.exchange_type)
#     chan.close()
#     conn.close()
#     return True


def os_exec(*args):
    """Wrapper for `os.execve()` that catches execution errors."""
    try:
        os.execv(args[0], args)
        os._exit(1)
    except OSError:
        sys.stderr.write("\nERROR:\nCould not exec: %s\n" % (args,))
    # if we reach here, it's an error anyway
    os._exit(-1)


def daemon(name, logfilename, pidfilename, *args, **kwargs):
    """Execute a double fork to start up a daemon."""

    # fork 1 - close fds and start new process group
    pid = os.fork()
    if pid:
        # parent process - we collect the first child to avoid ghosts.
        os.waitpid(pid, 0)
        return
    # start a new process group and detach ttys
    # print '## Starting', name, '##'
    os.setsid()

    # fork 2 - now detach once more free and clear
    pid = os.fork()
    if pid:
        # this is the first fork - its job is done
        os._exit(0)
    # make attempts to read from stdin fail.
    fnullr = os.open(os.devnull, os.O_RDONLY)
    os.dup2(fnullr, 0)
    if fnullr:
        os.close(fnullr)
    # open up the logfile and start up the process
    f = os.open(logfilename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.dup2(f, 1)
    os.dup2(f, 2)
    if f > 2:
        os.close(f)
    # With output setup to log we can start running code again.
    if 'command' in kwargs:
        args = (kwargs['command'],) + args
    else:
        args = ('/usr/bin/env', 'python', '-u',) + args
    if 'homedir' in kwargs:
        os.environ['HOME'] = kwargs['homedir']
    print os.environ['HOME']
    print os.stat(os.environ['HOME'])
    # this should get logged
    print '## Starting %s as %s' % (name, args)
    # write the pidfile file
    with open(pidfilename, "w") as pidfile:
        pidfile.write("%d" % os.getpid())
        pidfile.flush()
    os_exec(*args)


# def status():
#     """ provides status information about the RabbitMQ server """
#     # Not ported yet.
#     nodename = _get_nodename()
#     if not _check_running():
#         print "ERROR: RabbitMQ node %s is not running" % nodename
#         return
#     for act in ["list_exchanges", "list_queues"]:
#         outstr, errstr = _rabbitctl(act, strip=True)
#         if errstr:
#             print >> sys.stderr, errstr
#         if outstr:
#             print outstr
#     return


def allocate_ports(n=1):
    """Allocate `n` unused ports.

    There is a small race condition here (between the time we allocate the
    port, and the time it actually gets used), but for the purposes for which
    this function gets used it isn't a problem in practice.
    """
    sockets = map(lambda _: socket.socket(), xrange(n))
    try:
        for s in sockets:
            s.bind(('localhost', 0))
        return map(lambda s: s.getsockname()[1], sockets)
    finally:
        for s in sockets:
            s.close()


class RabbitFixture(Fixture):
    """Common fixture stuff for dealing with RabbitMQ servers.

    In particular this adopts detail handling code from `testtools` so that
    details from sub-fixtures are propagated up to the test case.
    """

    def useFixture(self, fixture):
        super(RabbitFixture, self).useFixture(fixture)
        self.addCleanup(self._gather_details, fixture.getDetails)
        return fixture

    def _gather_details(self, getDetails):
        """Merge the details from getDetails() into self.getDetails().

        Shamelessly adapted from `testtools.TestCase._gather_details`.
        """
        details = getDetails()
        my_details = self.getDetails()
        for name, content_object in details.items():
            new_name = name
            disambiguator = itertools.count(1)
            while new_name in my_details:
                new_name = '%s-%d' % (name, next(disambiguator))
            name = new_name
            content_bytes = list(content_object.iter_bytes())
            content_callback = lambda: content_bytes
            self.addDetail(name,
                Content(content_object.content_type, content_callback))


class RabbitServerResources(RabbitFixture):
    """Allocate the resources a RabbitMQ server needs.

    :ivar hostname: The host the RabbitMQ is on (always localhost for
        `RabbitServerResources`).
    :ivar port: A port that was free at the time setUp() was called.
    :ivar rabbitdir: A directory to put the RabbitMQ logs in.
    :ivar mnesiadir: A directory for the RabbitMQ db.
    :ivar logfile: The logfile allocated for the server.
    :ivar pidfile: The file the pid should be written to.
    :ivar nodename: The name of the node.
    """
    def setUp(self):
        super(RabbitServerResources, self).setUp()
        self.hostname = 'localhost'
        self.port = allocate_ports()[0]
        self.rabbitdir = self.useFixture(TempDir()).path
        self.mnesiadir = self.useFixture(TempDir()).path
        self.logfile = os.path.join(self.rabbitdir, 'rabbit.log')
        self.pidfile = os.path.join(self.rabbitdir, 'rabbit.pid')
        self.nodename = os.path.basename(self.useFixture(TempDir()).path)
        self.service_config = dedent("""\
            [rabbitmq]
            host: localhost:%d
            userid: guest
            password: guest
            virtual_host: /
            """ % self.port)

    @property
    def fq_nodename(self):
        """The node of the RabbitMQ that is being exported."""
        # Note that socket.gethostname is recommended by the rabbitctl manpage
        # even though we're always on localhost, its what the erlang cluster
        # code wants.
        return "%s@%s" % (self.nodename, socket.gethostname())


class RabbitServerEnvironment(RabbitFixture):
    """Export the environment variables needed to talk to a RabbitMQ instance.

    When setup this exports the key RabbitMQ variables:

    - ``RABBITMQ_MNESIA_BASE``
    - ``RABBITMQ_LOG_BASE``
    - ``RABBITMQ_NODE_PORT``
    - ``RABBITMQ_NODENAME``

    """

    def __init__(self, config):
        """Create a `RabbitServerEnvironment` instance.

        :param config: An object exporting the variables
            `RabbitServerResources` exports.
        """
        super(RabbitServerEnvironment, self).__init__()
        self.config = config

    def setUp(self):
        super(RabbitServerEnvironment, self).setUp()
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_MNESIA_BASE", self.config.mnesiadir))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_LOG_BASE", self.config.rabbitdir))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_NODE_PORT", str(self.config.port)))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_NODENAME", self.config.nodename))
        self._errors = []
        self.addDetail('rabbit-errors',
            Content(UTF8_TEXT, self._get_errors))

    def _get_errors(self):
        """Yield all errors as UTF-8 encoded text."""
        for error in self._errors:
            if type(error) is unicode:
                yield error.encode('utf8')
            else:
                yield error
            yield '\n'

    def rabbitctl(self, command, strip=False):
        """Executes a ``rabbitctl`` command and returns status."""
        ctlbin = os.path.join(RABBITBIN, "rabbitmqctl")
        nodename = self.config.fq_nodename
        env = dict(os.environ)
        env['HOME'] = self.config.rabbitdir
        ctl = subprocess.Popen(
            (ctlbin, "-n", nodename, command), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outstr, errstr = ctl.communicate()
        if strip:
            return outstr.strip(), errstr.strip()
        return outstr, errstr

    def check_running(self):
        """Checks that RabbitMQ is up and running."""
        nodename = self.config.fq_nodename
        outdata, errdata = self.rabbitctl("status")
        if errdata:
            self._errors.append(errdata)
        if not outdata:
            return False
        # try to parse the output to find if this nodename is running
        regex = re.compile(r"""
            \{running_nodes,            # search for running_node section
              \[                        # begin list of nodes
                '?                      # individual node may be quoted
                (?P<nodename>           # begin capture group
                  [^@]+                 # a node is name@hostname: name
                  @                     # @
                  [^@']+                # hostname
                )                       # end capturing group
                '?                      # individual node may be quoted
                ,?                      # may be multiple nodes, comma-sep
              \]                        # end list
            \}                          # end section
        """, re.VERBOSE)
        match = regex.search(outdata)
        if not match:
            self._errors.append(outdata)
            return False
        found_node = match.group('nodename')
        return found_node == nodename

    def get_connection(self):
        """Get an AMQP connection to the RabbitMQ server.

        :raises socket.error: If the connection cannot be made.
        """
        host_port = "%s:%s" % (self.config.hostname, self.config.port)
        return amqp.Connection(
            host=host_port, userid="guest",
            password="guest", virtual_host="/", insist=False)


class RabbitServerRunner(RabbitFixture):
    """Run a RabbitMQ server.

    :ivar pid: The pid of the server.
    """

    def __init__(self, config):
        """Create a `RabbitServerRunner` instance.

        :param config: An object exporting the variables
            `RabbitServerResources` exports.
        """
        super(RabbitServerRunner, self).__init__()
        self.config = config

    def setUp(self):
        super(RabbitServerRunner, self).setUp()
        self.environment = self.useFixture(
            RabbitServerEnvironment(self.config))
        self._start()

    def _start(self):
        cmd = os.path.join(RABBITBIN, 'rabbitmq-server')
        name = "RabbitMQ server node:%s on port:%d" % (
            self.config.nodename, self.config.port)
        daemon(name, self.config.logfile, self.config.pidfile, command=cmd,
            homedir=self.config.rabbitdir)
        self.addDetail(
            os.path.basename(self.config.logfile),
            content_from_file(self.config.logfile))
        # Wait for the server to come up...
        timeout = time.time() + 15
        while time.time() < timeout:
            if self.environment.check_running():
                break
            time.sleep(0.3)
        else:
            raise Exception(
                "Timeout waiting for RabbitMQ OTP server to start.")
        # The erlang OTP is up, but RabbitMQ may not be usable. We need to
        # cleanup up the process from here on in even if the full service
        # fails to get together.
        self.addCleanup(self._stop)
        # Wait until the server is ready...
        while time.time() < timeout:
            # rabbitctl can say a node is up before it is ready to
            # accept connections ... :-(
            try:
                conn = self.environment.get_connection()
            except socket.error:
                time.sleep(0.1)
            else:
                conn.close()
                break
        else:
            raise Exception(
                "Timeout waiting for RabbitMQ to start listening.")
        # All should be well here.
        with open(self.config.pidfile, "r") as f:
            self.pid = int(f.read().strip())

    def _stop(self):
        """Stop the running server. Normally called by cleanups."""
        if not self.environment.check_running():
            # If someone has shut it down already, we're done.
            return
        outstr, errstr = self.environment.rabbitctl("stop", strip=True)
        if outstr:
            self.addDetail('stop-out', Content(UTF8_TEXT, lambda: [outstr]))
        if errstr:
            self.addDetail('stop-err', Content(UTF8_TEXT, lambda: [errstr]))
        # Wait for the server to go down...
        timeout = time.time() + 15
        while time.time() < timeout:
            if not self.environment.check_running():
                break
            time.sleep(0.3)
        else:
            raise Exception(
                "Timeout waiting for RabbitMQ shutdown.")
        # Wait for the process to end...
        while time.time() < timeout:
            try:
                os.kill(self.pid, 0)
            except OSError, e:
                if e.errno == errno.ESRCH:
                    break
                raise
            else:
                time.sleep(0.1)
        else:
            raise Exception(
                "RabbitMQ (pid=%d) did not quit." % (self.pid,))


class RabbitServer(RabbitFixture):
    """A RabbitMQ server fixture.

    When setup a RabbitMQ instance will be running and the environment
    variables needed to talk to it will be already configured.

    :ivar config: The `RabbitServerResources` used to start the server.
    :ivar runner: The `RabbitServerRunner` that bootstraps the server.
    """

    def setUp(self):
        super(RabbitServer, self).setUp()
        self.config = self.useFixture(RabbitServerResources())
        self.runner = self.useFixture(RabbitServerRunner(self.config))
