# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to represent a single machine instance in EC2."""

__metaclass__ = type
__all__ = [
    'EC2Instance',
    ]

import glob
import os
import select
import socket
import subprocess
import sys
import time

import paramiko

from devscripts.ec2test.sshconfig import SSHConfig


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

    def __init__(self, name, image, instance_type, demo_networks, account,
                 vals):
        self._name = name
        self._image = image
        self._account = account
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
        self.private_key = self._account.acquire_private_key()
        self._account.acquire_security_group(
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

    def _connect(self, user, use_agent):
        """Connect to the instance as `user`. """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(AcceptAllPolicy())
        connect_args = {'username': user}
        if not use_agent:
            connect_args.update({
                'pkey': self.private_key,
                'allow_agent': False,
                'look_for_keys': False,
                })
        for count in range(10):
            try:
                ssh.connect(self.hostname, **connect_args)
            except (socket.error, paramiko.AuthenticationException), e:
                self.log('_connect: %r' % (e,))
                if count < 9:
                    time.sleep(5)
                    self.log('retrying...')
                else:
                    raise
            else:
                break
        return EC2InstanceConnection(self, user, ssh)

    def connect_as_root(self):
        return self._connect('root', False)

    def connect_as_user(self):
        return self._connect(self._vals['USER'], True)

    def setup_user(self):
        """Set up an account named after the local user."""
        root_connection = self.connect_as_root()
        root_p = root_connection.perform
        if self._vals['USER'] == 'gary':
            # This helps gary debug problems others are having by removing
            # much of the initial setup used to work on the original image.
            root_p('deluser --remove-home gary', ignore_failure=True)
        # Let root perform sudo without a password.
        root_p('echo "root\tALL=NOPASSWD: ALL" >> /etc/sudoers')
        # Add the user.
        root_p('adduser --gecos "" --disabled-password %(USER)s')
        # Give user sudo without password.
        root_p('echo "%(USER)s\tALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
            # Make /var/launchpad owned by user.
        root_p('chown -R %(USER)s:%(USER)s /var/launchpad')
        # Clean out left-overs from the instance image.
        root_p('rm -fr /var/tmp/*')
        # Update the system.
        root_p('aptitude update')
        root_p('aptitude -y full-upgrade')
        # Set up ssh for user
        # Make user's .ssh directory
        root_p('sudo -u %(USER)s mkdir /home/%(USER)s/.ssh')
        root_sftp = root_connection.ssh.open_sftp()
        remote_ssh_dir = '/home/%(USER)s/.ssh' % self._vals
        # Create config file
        self.log('Creating %s/config\n' % (remote_ssh_dir,))
        ssh_config_file_name = os.path.join(
            self._vals['HOME'], '.ssh', 'config')
        ssh_config_source = open(ssh_config_file_name)
        config = SSHConfig()
        config.parse(ssh_config_source)
        ssh_config_source.close()
        ssh_config_dest = root_sftp.open("%s/config" % remote_ssh_dir, 'w')
        ssh_config_dest.write('CheckHostIP no\n')
        ssh_config_dest.write('StrictHostKeyChecking no\n')
        for hostname in ('devpad.canonical.com', 'chinstrap.canonical.com'):
            ssh_config_dest.write('Host %s\n' % (hostname,))
            data = config.lookup(hostname)
            for key in ('hostname', 'gssapiauthentication', 'proxycommand',
                        'user', 'forwardagent'):
                value = data.get(key)
                if value is not None:
                    ssh_config_dest.write('    %s %s\n' % (key, value))
        ssh_config_dest.write('Host bazaar.launchpad.net\n')
        ssh_config_dest.write('    user %(launchpad-login)s\n' % self._vals)
        ssh_config_dest.close()
        # create authorized_keys
        self.log('Setting up %s/authorized_keys\n' % remote_ssh_dir)
        authorized_keys_file = root_sftp.open(
            "%s/authorized_keys" % remote_ssh_dir, 'w')
        authorized_keys_file.write("%(key_type)s %(key)s\n" % self._vals)
        authorized_keys_file.close()
        root_sftp.close()
        # Chown and chmod the .ssh directory and contents that we just
        # created.
        root_p('chown -R %(USER)s:%(USER)s /home/%(USER)s/')
        root_p('chmod 644 /home/%(USER)s/.ssh/*')
        self.log(
            'You can now use ssh -A %s to log in the instance.\n' %
            self.hostname)
        # give the user permission to do whatever in /var/www
        root_p('chown -R %(USER)s:%(USER)s /var/www')
        root_connection.close()

    def _copy_single_glob_match(self, sftp, pattern, local_dir, remote_dir):
        [local_path] = glob.glob(os.path.join(local_dir, pattern))
        name = os.path.basename(local_path)
        remote_path = os.path.join(remote_dir, name)
        remote_file = sftp.open(remote_path, 'w')
        remote_file.write(open(local_path).read())
        remote_file.close()
        return remote_path

    def copy_key_and_certificate_to_image(self, sftp):
        remote_ec2_dir = '/mnt/ec2'
        local_ec2_dir = os.path.expanduser('~/.ec2')
        remote_private_key_path = self._copy_single_glob_match(
            sftp, 'pk-*.pem', local_ec2_dir, remote_ec2_dir)
        remote_cert_path = self._copy_single_glob_match(
            sftp, 'cert-*.pem', local_ec2_dir, remote_ec2_dir)
        return (remote_private_key_path, remote_cert_path)

    def bundle(self, name):
        """Bundle, upload and register the instance as a new AMI."""
        root_connection = self.connect_as_root()
        sftp = root_connection.ssh.open_sftp()

        remote_private_key_path, remote_cert_path = \
            self.copy_key_and_certificate_to_image(sftp)

        sftp.close()

        bundle_dir = os.path.join('/mnt', name)

        root_connection.perform('mkdir ' + bundle_dir)
        root_connection.peform(' '.join([
            'ec2-bundle-vol',
            '-d %s' % bundle_dir,
            '-b',   # Set batch-mode, which doesn't use prompts.
            '-k %s' % remote_private_key_path,
            '-c %s' % remote_cert_path,
            '-u %s'  % self.account_id
            ]))

        # Assume that the manifest is 'image.manifest.xml', since "image" is
        # the default prefix.
        manifest = os.path.join(bundle_dir, 'image.manifest.xml')

        # Best check that the manifest actually exists though.
        test = 'test -f %s' % manifest
        root_connection.perform(test)

        root_connection.peform(' '.join([
            'ec2-upload-bundle',
            '-b %s' % self.target_bucket,
            '-m %s' % manifest,
            '-a %s' % self.access_key,
            '-s %s' % self.secret_key
            ]))

        sftp.close()
        root_connection.close()


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
        call = ['ssh', '-A', self.instance.hostname,
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

