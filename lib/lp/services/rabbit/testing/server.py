# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test server fixture for RabbitMQ."""

import errno
import os
import re
import sys
import socket
import optparse
import subprocess
import time

import bzrlib.branch
from fixtures import (
    EnvironmentVariableFixture,
    Fixture,
    TempDir,
    )
from testtools.content import Content
from testtools.content_type import UTF8_TEXT

from amqplib import client_0_8 as amqp

# The default binaries have a check that the running use is uid 0 or uname
# 'rabbitmq', neither of which are needed to operate correctly. So we run the
# actual erlang binaries.
RABBITBIN = "/usr/lib/rabbitmq/bin"


def setup_exchange(conf, port):
    """ create an exchange """
    # Not ported yet.
    conn = _get_connection(conf, port)
    # see if we already have the exchange
    must_create = False
    chan = conn.channel()
    try:
        chan.exchange_declare(exchange=conf.exchange_name + BRANCH_NICK,
                              type=conf.exchange_type, passive=True)
    except (amqp.AMQPConnectionException, amqp.AMQPChannelException), e:
        if e.amqp_reply_code == 404:
            must_create = True
            # amqplib kills the channel on error.... we dispose of it too
            chan.close()
            chan = conn.channel()
        else:
            raise
    # now create the exchange if needed
    if must_create:
        chan.exchange_declare(exchange=conf.exchange_name + BRANCH_NICK,
                              type=conf.exchange_type,
                              durable=True, auto_delete=False,)
        print "Created new exchange %s (%s)" % (
            conf.exchange_name + BRANCH_NICK, conf.exchange_type)
    else:
        print "Exchange %s (%s) is already declared" % (
            conf.exchange_name + BRANCH_NICK, conf.exchange_type)
    chan.close()
    conn.close()
    return True


def os_exec(*args):
    """ warpper for os.execve() that catches execution errors """
    try:
        os.execv(args[0], args)
        os._exit(1)
    except OSError:
        sys.stderr.write("\nERROR:\nCould not exec: %s\n" % (args,))
    # if we reach here, it's an error anyway
    os._exit(-1)


def daemon(name, logfilename, pidfilename, *args, **kwargs):
    """Execute a double fork to start up a daemon """

    # fork 1 - close fds and start new process group
    pid = os.fork()
    if pid:
        # parent process - we wait for the first child to exit
        os.waitpid(pid, 0)
        return
    # start a new process group and detach ttys
    # print '## Starting', name, '##'
    fnullr = os.open(os.devnull, os.O_RDONLY)
    os.dup2(fnullr, 0)
    fnullw = os.open(os.devnull, os.O_WRONLY)
    os.dup2(fnullw, 1)
    os.dup2(fnullw, 2)
    os.setsid()

    # fork 2 - now detach once more free and clear
    pid = os.fork()
    if pid:
        # this is the first fork - its job is done
        os._exit(0)
    # open up the logfile and start up the process
    f = os.open(logfilename,
                os.O_WRONLY|os.O_CREAT|os.O_TRUNC)
    os.dup2(f, 1)
    os.dup2(f, 2)
    os.close(f)
    if 'command' in kwargs:
        args = (kwargs['command'],) + args
    else:
        args = ('/usr/bin/env', 'python', '-u',) + args
    # this should get logged
    print '## Starting %s as %s' % (name, args)
    # write the pidfile file
    with open(pidfilename, "w") as pidfile:
        pidfile.write("%d" % os.getpid())
        pidfile.flush()
    os_exec(*args)


def status():
    """ provides status information about the RabbitMQ server """
    # Not ported yet.
    nodename = _get_nodename()
    if not _check_running():
        print "ERROR: RabbitMQ node %s is not running" % nodename
        return
    for act in ["list_exchanges", "list_queues"]:
        outstr, errstr = _rabbitctl(act, strip=True)
        if errstr:
            print >> sys.stderr, errstr
        if outstr:
            print outstr
    return


def allocate_ports(n=1):
    """
    Allocate n unused ports

    There is a small race condition here (between the time we allocate
    the port, and the time it actually gets used), but for the purposes
    for which this function gets used it isn't a problem in practice.
    """
    sockets = map(lambda _: socket.socket(), xrange(n))
    try:
        for s in sockets:
            s.bind(('localhost', 0))
        ports = map(lambda s: s.getsockname()[1], sockets)
    finally:
        for s in sockets: 
            s.close()
    return ports


class AllocateRabbitServer(Fixture):
    """Allocate the resources a rabbit server needs.

    :ivar hostname: The host the rabbit is on (always localhost for
        AllocateRabbitServer).
    :ivar port: A port that was free at the time setUp() was called.
    :ivar rabbitdir: A directory to put the rabbit logs in.
    :ivar mnesiadir: A directory for the rabbit db.
    :ivar logfile: The logfile allocated for the server.
    :ivar pidfile: The file the pid should be written to.
    :ivar nodename: The name of the node.
    """
    def setUp(self):
        super(AllocateRabbitServer, self).setUp()
        self.hostname = 'localhost'
        self.port = allocate_ports()[0]
        self.rabbitdir = self.useFixture(TempDir()).path
        self.mnesiadir = self.useFixture(TempDir()).path
        self.logfile = os.path.join(self.rabbitdir, 'rabbit.log')
        self.pidfile = os.path.join(self.rabbitdir, 'rabbit.pid')
        self.nodename = os.path.basename(self.useFixture(TempDir()).path)

    def fq_nodename(self):
        """Get the node of the rabbit that is being exported."""
        # Note that socket.gethostname is recommended by the rabbitctl manpage
        # even though we're always on localhost, its what the erlang cluster
        # code wants.
        return "%s@%s" % (self.nodename, socket.gethostname())


class ExportRabbitServer(Fixture):
    """Export the environmen variables needed to talk to a rabbit instance.
    
    When setup this exports the key rabbit variables::
     * RABBITMQ_MNESIA_BASE
     * RABBITMQ_LOG_BASE
     * RABBITMQ_NODE_PORT
     * RABBITMQ_NODENAME
    """

    def __init__(self, config):
        """Create a ExportRabbitServer instance.

        :param config: An object exporting the variables `AllocateRabbitServer`
            exports.
        """
        super(ExportRabbitServer, self).__init__()
        self.config = config

    def setUp(self):
        super(ExportRabbitServer, self).setUp()
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_MNESIA_BASE", self.config.mnesiadir))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_LOG_BASE", self.config.rabbitdir))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_NODE_PORT", str(self.config.port)))
        self.useFixture(EnvironmentVariableFixture(
            "RABBITMQ_NODENAME", self.config.nodename))

    def rabbitctl(self, command, strip=False):
        """ executes a rabbitctl command and returns status """
        ctlbin = RABBITBIN + "/rabbitmqctl"
        nodename = self.config.fq_nodename()
        ctl = subprocess.Popen((ctlbin, "-n", nodename, command),
                               stdout = subprocess.PIPE,
                               stderr = subprocess.PIPE)
        outstr, errstr = ctl.communicate()
        if strip:
            return outstr.strip(), errstr.strip()
        return outstr, errstr

    def check_running(self):
        """ checks that the rabbitmq process is up and running """
        nodename = self.config.fq_nodename()
        outdata, errdata = self.rabbitctl("status")
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
                ,?                      # may be multiple nodes, comma-separated
              \]                        # end list
            \}                          # end section
        """, re.VERBOSE)
        match = regex.search(outdata)
        if not match:
            return False
        found_node = match.groupdict()['nodename']
        return found_node == nodename

    def get_connection(self):
        """Get an AMQP connection to the RabbitMQ server.
        
        :raises socket.error: If the connection cannot be made.
        """
        host_port = "%s:%s" % (self.config.hostname, self.config.port)
        conn = amqp.Connection(host=host_port, userid="guest",
                               password="guest", virtual_host="/", insist=False)
        return conn


class RunRabbitServer(Fixture):
    """Run a rabbit server.
    
    :ivar pid: The pid of the server.
    """

    def __init__(self, config):
        """Create a RunRabbitServer instance.

        :param config: An object exporting the variables `AllocateRabbitServer`
            exports.
        """
        super(RunRabbitServer, self).__init__()
        self.config = config

    def setUp(self):
        super(RunRabbitServer, self).setUp()
        self.rabbit = self.useFixture(ExportRabbitServer(self.config))
        self.addDetail('log',
            Content(UTF8_TEXT, lambda:[file(self.config.logfile, 'rb').read()]))
        cmd = RABBITBIN + '/rabbitmq-server'
        name = "RabbitMQ server node:%s on port:%d" % (
            self.config.nodename, self.config.port)
        daemon(name, self.config.logfile, self.config.pidfile, command=cmd)
        # now wait about 5 secs for it to start
        timeout = time.time() + 5
        while True:
            if self.rabbit.check_running():
                break
            elif time.time() > timeout:
                raise Exception('Rabbit server did not start.')
        # The erlang OTP is up, but rabbit may not be usable. We need to
        # cleanup up the process from here on in even if the full service fails
        # to get together.
        self.addCleanup(self.stop)
        while True:
            # rabbitctl can say a node is up before it is ready to
            # accept connections ... :-(
            try:
                conn = self.rabbit.get_connection()
            except socket.error:
                pass
            else:
                conn.close()
                break
            time.sleep(0.1)
            if time.time() > timeout:
                raise Exception('Rabbit server did not start.')
        # all should be well here
        with open(self.config.pidfile, "r") as f:
            self.pid = int(f.read().strip())

    def stop(self):
        """Stop the running server. Normally called by cleanups."""
        if not self.rabbit.check_running():
            # If someone has shut it down already, we're done.
            return
        outstr, errstr = self.rabbit.rabbitctl("stop", strip=True)
        if outstr:
            self.addDetail('stop-out', Content(UTF8_TEXT, lambda:[outstr]))
        if errstr:
            self.addDetail('stop-err', Content(UTF8_TEXT, lambda:[errstr]))
        # wait for the process to finish...
        timeout = time.time() + 15
        while self.rabbit.check_running():
            time.sleep(0.3)
            if time.time() > timeout:
                raise Exception(
                    "Error - reached timeout waiting for RabbitMQ shutdown")
        while time.time() < timeout:
            try:
                os.kill(self.pid, 0)
            except OSError, e:
                if e.errno == errno.ESRCH:
                    break
            time.sleep(0.1)
            if time.time() > timeout:
                raise Exception(
                    "Error - rabbit pid %d did not quit." % (pid,))


class RabbitServer(Fixture):
    """A RabbitMQ server fixture.

    When setup a rabbit instance will be running and the environment variables
    needed to talk to it will be already configured.

    :ivar config: The `AllocateRabbitServer` used to start the rabbit.
    """

    def setUp(self):
        super(RabbitServer, self).setUp()
        self.config = self.useFixture(AllocateRabbitServer())
        self.server = self.useFixture(RunRabbitServer(self.config))

    def getDetails(self):
        return self.server.getDetails()

