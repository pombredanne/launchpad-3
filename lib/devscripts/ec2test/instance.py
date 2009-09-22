# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to represent a single machine instance in EC2."""

__metaclass__ = type
__all__ = [
    'EC2Instance',
    ]

import code
import glob
import os
import select
import socket
import subprocess
import sys
import time
import traceback

from bzrlib.errors import BzrCommandError
from bzrlib.plugins.launchpad.account import get_lp_login

import paramiko

from devscripts.ec2test.credentials import EC2Credentials


DEFAULT_INSTANCE_TYPE = 'c1.xlarge'
AVAILABLE_INSTANCE_TYPES = ('m1.large', 'm1.xlarge', 'c1.xlarge')

class AcceptAllPolicy:
    """We accept all unknown host key."""

    # Normally the console output is supposed to contain the Host key
    # but it doesn't seem to be the case here, so we trust that the host
    # we are connecting to is the correct one.
    def missing_host_key(self, client, hostname, key):
        pass


def get_user_key():
    """Get a SSH key from the agent.  Raise an error if not found.

    This key will be used to let the user log in (as $USER) to the instance.
    """
    agent = paramiko.Agent()
    keys = agent.get_keys()
    if len(keys) == 0:
        raise BzrCommandError(
            'You must have an ssh agent running with keys installed that '
            'will allow the script to rsync to devpad and get your '
            'branch.\n')
    user_key = agent.get_keys()[0]
    return user_key


class EC2Instance:
    """A single EC2 instance."""

    @classmethod
    def make(cls, name, instance_type, machine_id,
             demo_networks=None, credentials=None):
        """Construct an `EC2Instance`.

        :param name: The name to use for the key pair and security group for
            the instance.
        :param instance_type: One of the AVAILABLE_INSTANCE_TYPES.
        :param machine_id: The AMI to use, or None to do the usual regexp
            matching.
        :param demo_networks: A list of networks to add to the security group
            to allow access to the instance.
        :param credentials: An `EC2Credentials` object.
        """
        if instance_type not in AVAILABLE_INSTANCE_TYPES:
            raise ValueError('unknown instance_type %s' % (instance_type,))

        if credentials is None:
            credentials = EC2Credentials.load_from_file()

        # Make the EC2 connection.
        account = credentials.connect(name)

        # We do this here because it (1) cleans things up and (2) verifies
        # that the account is correctly set up. Both of these are appropriate
        # for initialization.
        #
        # We always recreate the keypairs because there is no way to
        # programmatically retrieve the private key component, unless we
        # generate it.
        account.delete_previous_key_pair()

        # get the image
        image = account.acquire_image(machine_id)

        vals = os.environ.copy()
        login = get_lp_login()
        if not login:
            raise BzrCommandError(
                'you must have set your launchpad login in bzr.')
        vals['launchpad-login'] = login

        return EC2Instance(
            name, image, instance_type, demo_networks, account, vals)

    # XXX: JonathanLange 2009-05-31: Separate out demo server

    def __init__(self, name, image, instance_type, demo_networks, account,
                 vals):
        self._name = name
        self._image = image
        self._account = account
        self._instance_type = instance_type
        self._demo_networks = demo_networks
        self._boto_instance = None
        self._vals = vals

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
        self.private_key = self._account.acquire_private_key()
        self.security_group = self._account.acquire_security_group(
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
            raise BzrCommandError(
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

    def connect(self):
        """Connect to the instance as `user`. """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(AcceptAllPolicy())
        connect_args = {
            'username': 'ubuntu',
            'pkey': self.private_key,
            'allow_agent': False,
            'look_for_keys': False,
            }
        for count in range(10):
            try:
                ssh.connect(self.hostname, **connect_args)
            except (socket.error, paramiko.AuthenticationException), e:
                self.log('_connect: %r\n' % (e,))
                if count < 9:
                    time.sleep(5)
                    self.log('retrying...')
                else:
                    raise
            else:
                break
        return EC2InstanceConnection(self, 'ubuntu', ssh)

    def set_up_user(self, user_key):
        """Set up an account named after the local user."""
        ubuntu_connection = self.connect()
        # Update the system.
        #ubuntu_connection.perform('sudo aptitude update')
        #ubuntu_connection.perform('sudo aptitude -y full-upgrade')
        # Set up ssh for user
        # Make user's .ssh directory
        ubuntu_sftp = ubuntu_connection.ssh.open_sftp()
        # create authorized_keys
        self.log('Setting up /home/ubuntu/.ssh/authorized_keys\n')
        authorized_keys_file = ubuntu_sftp.open(
            "/home/ubuntu/.ssh/authorized_keys", 'a')
        authorized_keys_file.write(
            "%s %s\n" % (user_key.get_name(), user_key.get_base64()))
        authorized_keys_file.close()
        ubuntu_sftp.close()
        self.log(
            'You can now use ssh -A ubuntu@%s to log in the instance.\n' %
            self.hostname)
        # Clean out left-overs from the instance image.
        ubuntu_connection.perform('sudo rm -fr /var/tmp/*')
        ubuntu_connection.close()

    def set_up_and_run(self, postmortem, shutdown, func, *args, **kw):
        """Start, set up a user account, run `func` and then maybe shut down.

        :param postmortem: If true, any exceptions will be caught and an
            interactive session run to allow debugging the problem.
        :param shutdown: If true, shut down the instance after `func` and
            postmortem (if any) are completed.
        :param func: A callable that will be called when the instance is
            running and a user account has been set up on it.
        :param args: Passed to `func`.
        :param kw: Passed to `func`.
        """
        user_key = get_user_key()
        self.start()
        try:
            try:
                self.set_up_user(user_key)
                return func(*args, **kw)
            except Exception:
                # When running in postmortem mode, it is really helpful to see if
                # there are any exceptions before it waits in the console (in the
                # finally block), and you can't figure out why it's broken.
                traceback.print_exc()
        finally:
            try:
                if postmortem:
                    console = code.InteractiveConsole(locals())
                    console.interact((
                        'Postmortem Console.  EC2 instance is not yet dead.\n'
                        'It will shut down when you exit this prompt (CTRL-D).\n'
                        '\n'
                        'Tab-completion is enabled.'
                        '\n'
                        'EC2Instance is available as `instance`.\n'
                        'Also try these:\n'
                        '  http://%(dns)s/current_test.log\n'
                        '  ssh -A %(dns)s') %
                                     {'dns': self.hostname})
                    print 'Postmortem console closed.'
            finally:
                if shutdown:
                    self.shutdown()

    def _copy_single_file(self, sftp, local_path, remote_dir):
        """Copy `local_path` to `remote_dir` on this instance.

        The name in the remote directory will be that of the local file.

        :param sftp: A paramiko SFTP object.
        :param local_path: The local path.
        :param remote_dir: The directory on the instance to copy into.
        """
        name = os.path.basename(local_path)
        remote_path = os.path.join(remote_dir, name)
        remote_file = sftp.open(remote_path, 'w')
        remote_file.write(open(local_path).read())
        remote_file.close()
        return remote_path

    def copy_key_and_certificate_to_image(self, sftp):
        """Copy the AWS private key and certificate to the image.

        :param sftp: A paramiko SFTP object.
        """
        remote_ec2_dir = '/mnt/ec2'
        remote_pk = self._copy_single_file(
            sftp, self.local_pk, remote_ec2_dir)
        remote_cert = self._copy_single_file(
            sftp, self.local_cert, remote_ec2_dir)
        return (remote_pk, remote_cert)

    def _check_single_glob_match(self, local_dir, pattern, file_kind):
        """Check that `pattern` matches one file in `local_dir` and return it.

        :param local_dir: The local directory to look in.
        :param pattern: The glob patten to match.
        :param file_kind: The sort of file we're looking for, to be used in
            error messages.
        """
        pattern = os.path.join(local_dir, pattern)
        matches = glob.glob(pattern)
        if len(matches) != 1:
            raise BzrCommandError(
                '%r must match a single %s file' % (pattern, file_kind))
        return matches[0]

    def check_bundling_prerequisites(self):
        """Check, as best we can, that all the files we need to bundle exist.
        """
        local_ec2_dir = os.path.expanduser('~/.ec2')
        if not os.path.exists(local_ec2_dir):
            raise BzrCommandError(
                "~/.ec2 must exist and contain aws_user, aws_id, a private "
                "key file and a certificate.")
        aws_user_file = os.path.expanduser('~/.ec2/aws_user')
        if not os.path.exists(aws_user_file):
            raise BzrCommandError(
                "~/.ec2/aws_user must exist and contain your numeric AWS id.")
        self.aws_user = open(aws_user_file).read().strip()
        self.local_cert = self._check_single_glob_match(
            local_ec2_dir, 'cert-*.pem', 'certificate')
        self.local_pk = self._check_single_glob_match(
            local_ec2_dir, 'pk-*.pem', 'private key')

    def bundle(self, name, credentials):
        """Bundle, upload and register the instance as a new AMI.

        :param name: The name-to-be of the new AMI.
        :param credentials: An `EC2Credentials` object.
        """
        ubuntu_connection = self.connect()
        ubuntu_connection.perform('sudo mkdir /mnt/ec2')
        ubuntu_connection.perform('sudo chown ubuntu:ubuntu /mnt/ec2')
        sftp = ubuntu_connection.ssh.open_sftp()

        remote_pk, remote_cert =  self.copy_key_and_certificate_to_image(sftp)

        sftp.close()

        bundle_dir = os.path.join('/mnt', name)

        ubuntu_connection.perform('sudo mkdir ' + bundle_dir)
        ubuntu_connection.perform(' '.join([
            'sudo ec2-bundle-vol',
            '-d %s' % bundle_dir,
            '-b',   # Set batch-mode, which doesn't use prompts.
            '-k %s' % remote_pk,
            '-c %s' % remote_cert,
            '-u %s' % self.aws_user,
            ]))

        # Assume that the manifest is 'image.manifest.xml', since "image" is
        # the default prefix.
        manifest = os.path.join(bundle_dir, 'image.manifest.xml')

        # Best check that the manifest actually exists though.
        test = 'test -f %s' % manifest
        ubuntu_connection.perform(test)

        ubuntu_connection.perform(' '.join([
            'sudo ec2-upload-bundle',
            '-b %s' % name,
            '-m %s' % manifest,
            '-a %s' % credentials.identifier,
            '-s %s' % credentials.secret,
            ]))

        sftp.close()
        ubuntu_connection.close()

        # This is invoked locally.
        mfilename = os.path.basename(manifest)
        manifest_path = os.path.join(name, mfilename)

        env = os.environ.copy()
        if 'JAVA_HOME' not in os.environ:
            env['JAVA_HOME'] = '/usr/lib/jvm/default-java'
        cmd = [
            'ec2-register',
            '--private-key=%s' % self.local_pk,
            '--cert=%s' % self.local_cert,
            manifest_path
            ]
        self.log("Executing command: %s" % ' '.join(cmd))
        subprocess.check_call(cmd, env=env)


class EC2InstanceConnection:
    """An ssh connection to an `EC2Instance`."""

    def __init__(self, instance, username, ssh):
        self.instance = instance
        self.username = username
        self.ssh = ssh

    def perform(self, cmd, ignore_failure=False, out=None):
        """Perform 'cmd' on server.

        :param ignore_failure: If False, raise an error on non-zero exit
            statuses.
        :param out: A stream to write the output of the remote command to.
        """
        cmd = cmd % self.instance._vals
        self.instance.log(
            '%s@%s$ %s\n' % (self.username, self.instance._boto_instance.id, cmd))
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
        cmd = cmd % self.instance._vals
        self.instance.log('%s@%s$ %s\n' % (self.username, self.instance._boto_instance.id, cmd))
        call = ['ssh', '-A', 'ubuntu@' + self.instance.hostname,
               '-o', 'CheckHostIP no',
               '-o', 'StrictHostKeyChecking no',
               '-o', 'UserKnownHostsFile ~/.ec2/known_hosts',
               cmd]
        res = subprocess.call(call)
        if res and not ignore_failure:
            raise RuntimeError('Command failed: %s' % (cmd,))
        return res

    def close(self):
        self.ssh.close()
        self.ssh = None
