# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

import select
import socket
import subprocess
import sys
import time

import paramiko


class AcceptAllPolicy:
    """We accept all unknown host key."""

    # Normally the console output is supposed to contain the Host key
    # but it doesn't seem to be the case here, so we trust that the host
    # we are connecting to is the correct one.
    def missing_host_key(self, client, hostname, key):
        pass


class EC2Instance:
    """A single EC2 instance."""

    # XXX: JonathanLange 2009-05-31: Make it so that we pass one of these to
    # EC2 test runner, rather than the test runner knowing how to make one.
    # Right now, the test runner makes one of these directly. Instead, we want
    # to make an EC2Account and ask it for one of these instances and then
    # pass it to the test runner on construction.

    # XXX: JonathanLange 2009-05-31: Separate out demo server maybe?

    # XXX: JonathanLange 2009-05-31: Possibly separate out "get an instance"
    # and "set up instance for Launchpad testing" logic.

    def __init__(self, name, image, instance_type, demo_networks, controller,
                 vals):
        self._name = name
        self._image = image
        self._controller = controller
        self._instance_type = instance_type
        self._demo_networks = demo_networks
        self._boto_instance = None
        self._vals = vals

    def error_and_quit(self, msg):
        """Print error message and exit."""
        sys.stderr.write(msg)
        sys.exit(1)

    def log(self, msg):
        """Log a message on stdout, flushing afterwards."""
        # XXX: JonathanLange 2009-05-31 bug=383076: Should delete this and use
        # Python logging module instead.
        sys.stdout.write(msg)
        sys.stdout.flush()

    def start(self):
        """Start the instance."""
        if self._boto_instance is not None:
            self.log('Instance %s already started' % self._boto_instance.id)
            return
        start = time.time()
        self.private_key = self._controller.acquire_private_key()
        self._controller.acquire_security_group(
            demo_networks=self._demo_networks)
        reservation = self._image.run(
            key_name=self._name, security_groups=[self._name],
            instance_type=self._instance_type)
        self._boto_instance = reservation.instances[0]
        self.log('Instance %s starting..' % self._boto_instance.id)
        while self._boto_instance.state == 'pending':
            self.log('.')
            time.sleep(5)
            self._boto_instance.update()
        if self._boto_instance.state == 'running':
            self.log(' started on %s\n' % self.hostname)
            elapsed = time.time() - start
            self.log('Started in %d minutes %d seconds\n' %
                     (elapsed // 60, elapsed % 60))
            self._output = self._boto_instance.get_console_output()
            self.log(self._output.output)
        else:
            self.error_and_quit(
                'failed to start: %s\n' % self._boto_instance.state)

    def shutdown(self):
        """Shut down the instance."""
        if self._boto_instance is None:
            self.log('no instance created\n')
            return
        self._boto_instance.update()
        if self._boto_instance.state not in ('shutting-down', 'terminated'):
            # terminate instance
            self._boto_instance.stop()
            self._boto_instance.update()
        self.log('instance %s\n' % (self._boto_instance.state,))

    @property
    def hostname(self):
        if self._boto_instance is None:
            return None
        return self._boto_instance.public_dns_name

    def connect_as_root(self):
        """Connect to the instance as root.

        All subsequent 'perform' and 'subprocess' operations will be done with
        root privileges.
        """
        # XXX: JonathanLange 2009-06-02: This state-changing method could
        # perhaps be written as a function such as run_as_root, or as a method
        # that returns a root connection.
        for count in range(10):
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(AcceptAllPolicy())
            self.username = 'root'
            try:
                self.ssh.connect(
                    self.hostname, username='root',
                    pkey=self.private_key,
                    allow_agent=False, look_for_keys=False)
            except (socket.error, paramiko.AuthenticationException), e:
                self.log('connect_as_root: %r' % (e,))
                if count < 9:
                    time.sleep(5)
                    self.log('retrying...')
                else:
                    raise
            else:
                break

    def connect_as_user(self):
        """Connect as user.

        All subsequent 'perform' and 'subprocess' operations will be done with
        user-level privileges.
        """
        # XXX: JonathanLange 2009-06-02: This state-changing method could
        # perhaps be written as a function such as run_as_user, or as a method
        # that returns a user connection.
        #
        # This does not have the retry logic of connect_as_root because the
        # circumstances that make the retries necessary appear to only happen
        # on start-up, and connect_as_root is called first.
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(AcceptAllPolicy())
        self.username = self._vals['USER']
        self.ssh.connect(self.hostname)

    def perform(self, cmd, ignore_failure=False, out=None):
        """Perform 'cmd' on server.

        :param ignore_failure: If False, raise an error on non-zero exit
            statuses.
        :param out: A stream to write the output of the remote command to.
        """
        cmd = cmd % self._vals
        self.log('%s@%s$ %s\n' % (self.username, self._boto_instance.id, cmd))
        session = self.ssh.get_transport().open_session()
        session.exec_command(cmd)
        session.shutdown_write()
        while 1:
            select.select([session], [], [], 0.5)
            if session.recv_ready():
                data = session.recv(4096)
                if data:
                    sys.stdout.write(data)
                    sys.stdout.flush()
                    if out is not None:
                        out.write(data)
            if session.recv_stderr_ready():
                data = session.recv_stderr(4096)
                if data:
                    sys.stderr.write(data)
                    sys.stderr.flush()
            if session.exit_status_ready():
                break
        session.close()
        # XXX: JonathanLange 2009-05-31: If the command is killed by a signal
        # on the remote server, the SSH protocol does not send an exit_status,
        # it instead sends a different message with the number of the signal
        # that killed the process. AIUI, this code will fail confusingly if
        # that happens.
        res = session.recv_exit_status()
        if res and not ignore_failure:
            raise RuntimeError('Command failed: %s' % (cmd,))
        return res

    def run_with_ssh_agent(self, cmd, ignore_failure=False):
        """Run 'cmd' in a subprocess.

        Use this to run commands that require local SSH credentials. For
        example, getting private branches from Launchpad.
        """
        cmd = cmd % self._vals
        self.log('%s@%s$ %s\n' % (self.username, self._boto_instance.id, cmd))
        call = ['ssh', '-A', self.hostname,
               '-o', 'CheckHostIP no',
               '-o', 'StrictHostKeyChecking no',
               '-o', 'UserKnownHostsFile ~/.ec2/known_hosts',
               cmd]
        res = subprocess.call(call)
        if res and not ignore_failure:
            raise RuntimeError('Command failed: %s' % (cmd,))
        return res
