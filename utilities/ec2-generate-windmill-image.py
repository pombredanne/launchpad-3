#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Generate an EC2 image that is capable of running the Windmill browser UI
testing tool.

You must provide a base image that will be augmented with the necessary
packages and configuration.

The script requires certain options to be specified in order to function
properly.  These options may be supplied using command-line switches, or
via a config file, with the --config command-line switch.  The default
config file location is ~/.ec2/ec2bundle.cfg

The config file format simply replicates the required command-line options
as configuration keys.

---- ec2bundle.cfg ---

[DEFAULT]
key = gsg-keypair
identity-file = ~/.ec2/foo-keypair-id_rsa
private-key = ~/.ec2/pk-HKZYKTAIG2ECMXYIBH3HXV4ZBZQ55CLO.pem
cert =~/.ec2/cert-HKZYKTAIG2ECMXYIBH3HXV4ZBZQ55CLO.pem
user-id = AIDADH4IGTRXXKCD
access-key = SOMEBIGSTRINGOFDIGITS
secret-key = s0m3funKyStr1Ng0fD1gitZ
#bucket = foo  # Required, but you probably want to customize it each time.

---- fin ---

"""

__metatype__ = type


# Reuse a whole bunch of code from ec2test.py.
import ConfigParser
import ec2test
import logging
import optparse
import os
import paramiko
import select
import socket
import subprocess
import sys
import time


log   = logging.getLogger(__name__)
info  = log.info
debug = log.debug


usage = """
Generate an EC2 image for Windmill testing in Firefox.

usage: %prog [options] AMI-ID
"""

class Instance:
    """An EC2 instance controller."""

    def __init__(self, instance):
        self._instance = instance

    @property
    def id(self):
        return self._instance.id

    @property
    def hostname(self):
        return self._instance.public_dns_name

    def stop(self):
        instance = self._instance

        instance.update()
        if instance.state not in ('shutting-down', 'terminated'):
            # terminate instance
            instance.stop()
            instance.update()

        info('instance %s\n' % (instance.state,))

    def wait_for_instance_to_start(self):
        """Wait for the instance to transition to the "running" state."""
        instance = self._instance
        info('Instance %s starting..' % instance.id)

        start = time.time()
        while instance.state == 'pending':
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(5)
            instance.update()
        if instance.state == 'running':
            info('\ninstance now running at %s\n' % instance.public_dns_name)
            elapsed = time.time() - start
            info('Started in %d minutes %d seconds\n' %
                     (elapsed // 60, elapsed % 60))
            cout = instance.get_console_output()
            info(cout.output)
        else:
            raise RuntimeError('failed to start: %s\n' % instance.state)

    @classmethod
    def from_image(cls, account, ami_id, instance_type):
        """Return a new instance using the given startup parameters."""
        info("Starting instance")

        # Set up a security group that opens up ports 22, 80, and 443.  Also
        # opens up access for our IP.
        account.acquire_security_group()

        image = account.acquire_image(ami_id)
        key = account.name
        debug("Image: %s, Type: %s, Key: %s" % (
              ami_id, instance_type, key))

        reservation = image.run(
            key_name=key,
            security_groups=[key],
            instance_type=instance_type)

        instance = cls(reservation.instances[0])
        instance.wait_for_instance_to_start()
        return instance

    @classmethod
    def from_running_instance(cls, account, instance_id):
        """Create an object from an already running EC2 instance."""
        instance = account.get_instance(instance_id)
        if not instance:
            raise RuntimeError(
                "Unable to connect to instance %s" % instance_id)

        info("Connected to instance %s" % instance_id)
        proxy = cls(instance)
        # Just to be extra safe.
        proxy.wait_for_instance_to_start()
        return proxy


class SSHConnector:
    """Handle the various aspects of using an SSH connection."""

    def __init__(self, hostname, user, identity_file):
        self.hostname = hostname
        self.user = user
        self.identity_file = os.path.expanduser(identity_file)
        self._client = None

    def get_private_key(self):
        """Generate a private key object for our keyfile"""
        fp = os.path.expanduser(self.identity_file)
        return paramiko.RSAKey.from_private_key(open(fp))

    def connect(self):
        info('Waiting for SSH to come available: %s@%s\n' % (
             self.user, self.hostname))
        debug("Using private key file: %s" % self.identity_file)

        private_key = self.get_private_key()

        for count in range(10):
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(ec2test.AcceptAllPolicy())

            try:

                self._client.connect(
                    self.hostname,
                    username=self.user,
                    pkey=private_key,
                    allow_agent=False,
                    look_for_keys=False)

            except (socket.error, paramiko.AuthenticationException), e:
                log.warning('wait_for_connection: %r' % (e,))
                if count < 9:
                    time.sleep(5)
                    info('retrying...')
                else:
                    raise
            else:
                break

    def exec_command(self, remote_command, check_return=True):
        """Execute a command on the remote server.

        Raises an error if the command returns an exit status that is not
        zero, unless the option `check_return=False' has been given.
        """
        info('Executing command: %s@%s %s\n' % (self.user, self.hostname, remote_command))

        session = self._client.get_transport().open_session()
        session.exec_command(remote_command)
        session.shutdown_write()

        # TODO: change this to use the logging module
        while True:
            select.select([session], [], [], 0.5)
            if session.recv_ready():
                data = session.recv(4096)
                if data:
                    sys.stdout.write(data)
                    sys.stdout.flush()
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
        exit_status = session.recv_exit_status()
        if exit_status and check_return:
            raise RuntimeError('Command failed: %s' % (remote_command,))
        return exit_status

    def copy_to_remote(self, local_filename, remote_filename):
        cmd = [
            'scp',
            '-i', self.identity_file,
            local_filename,
            '%s@%s:%s' % (self.user, self.hostname, remote_filename)
            ]
        info("Executing command: %s" % ' '.join(cmd))
        subprocess.check_call(cmd)

    def user_command(self):
        """Return a user-friendly ssh command-line string."""
        return "ssh -i %s %s@%s" % (
            self.identity_file,
            self.user,
            self.hostname)


class ImageBundler:
    """Bundle an EC2 image on a remote system."""

    def __init__(self, private_key, cert, account_id, target_bucket,
                 access_key, secret_key, ssh):
        self.private_key = os.path.expanduser(private_key)
        self.cert = os.path.expanduser(cert)
        self.account_id = account_id
        self.target_bucket = target_bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.ssh = ssh

        # Use the instance /mnt directory by default, because it has a few
        # hundred GB of free space to work with.
        self._bundle_dir = os.path.join('/mnt', target_bucket)

    def bundle_image(self):
        self.configure_bundling_environment()
        manifest = self._bundle_image()
        self._upload_bundle(manifest)
        self._register_image(manifest)

    def remote_private_keypath(self):
        # ALWAYS have these files in /mnt on the remote system.  Otherwise
        # they will get bundled along with the image.
        return os.path.join('/mnt', os.path.basename(self.private_key))

    def remote_certpath(self):
        # ALWAYS have these files in /mnt on the remote system.  Otherwise
        # they will get bundled along with the image.
        return os.path.join('/mnt', os.path.basename(self.cert))

    def configure_bundling_environment(self):
        """Configure what we need on the instance for bundling the image."""
        # Send our keypair to the remote environment so that it can be used
        # to bundle the image.
        local_cert = os.path.abspath(self.cert)
        local_pkey = os.path.abspath(self.private_key)

        # ALWAYS copy these files into /mnt on the remote system.  Otherwise
        # they will get bundled along with the image.
        remote_cert = self.remote_certpath()
        remote_pkey = self.remote_private_keypath()

        # See if the files are present, and copy them over if they are not.
        self._ensure_remote_file(remote_cert, local_cert)
        self._ensure_remote_file(remote_pkey, local_pkey)

    def _ensure_remote_file(self, remote_file, desired_file):
        info("Checking for '%s' on the remote system" % remote_file)
        test = 'test -f %s' % remote_file
        exit_status = self.ssh.exec_command(test, check_return=False)
        if bool(exit_status):
            self.ssh.copy_to_remote(desired_file, remote_file)

    def _bundle_image(self):
        # Create the bundle in a subdirectory, to avoid spamming up /mnt.
        self.ssh.exec_command(
            'mkdir %s' % self._bundle_dir, check_return=False)

        cmd = [
            'ec2-bundle-vol',
            '-d %s' % self._bundle_dir,
            '-b',   # Set batch-mode, which doesn't use prompts.
            '-k %s' % self.remote_private_keypath(),
            '-c %s' % self.remote_certpath(),
            '-u %s'  % self.account_id
            ]

        self.ssh.exec_command(' '.join(cmd))
        # Assume that the manifest is 'image.manifest.xml', since "image" is
        # the default prefix.
        manifest = os.path.join(self._bundle_dir, 'image.manifest.xml')

        # Best check that the manifest actually exists though.
        test = 'test -f %s' % manifest
        exit_status = self.ssh.exec_command(test, check_return=False)

        if bool(exit_status):
            raise RuntimeError(
                "Failed to write the image manifest file: %s" % manifest)

        return manifest

    def _upload_bundle(self, manifest):
        cmd = [
            'ec2-upload-bundle',
            '-b %s' % self.target_bucket,
            '-m %s' % manifest,
            '-a %s' % self.access_key,
            '-s %s' % self.secret_key
            ]
        self.ssh.exec_command(' '.join(cmd))

    def _register_image(self, manifest):
        # This is invoked locally.
        mfilename = os.path.basename(manifest)
        manifest_path = os.path.join(self.target_bucket, mfilename)

        env = os.environ.copy()
        env['JAVA_HOME'] = '/usr/lib/jvm/default-java'
        cmd = [
            'ec2-register',
            '--private-key=%s' % self.private_key,
            '--cert=%s' % self.cert,
            manifest_path
            ]
        info("Executing command: %s" % ' '.join(cmd))
        subprocess.check_call(cmd, env=env)


class XvfbSystemConfigurator:
    """Configure a remote operating system over SSH to use the xvfb server."""

    def __init__(self, ssh):
        self.ssh = ssh

    def configure_system(self):
        """Configure the operating system with the needed packages, etc."""
        do = self.ssh.exec_command

        # Make sure we know about all the packages, and where they may be
        # found.
        do("apt-get -y update")
        # Install the necessary packages
        do("apt-get -y install xvfb firefox xfonts-base")


class CombinedConfigParser:
    """Store and reconcile options for both optparse and ConfigParser."""

    def __init__(self, optparser, cfgparser):
        self._optparser = optparser
        self._cfgparser = cfgparser

        # A list of required optparse options.
        self.required_options = []
        self.known_options = []

        # Our parsed positional command-line arguments, as returned by
        # optparse.OptionParser.parse_args()
        self.args = None

        # An optparse option.dest to 'cfg-key' mapping.
        self._option_to_cfgkey = {}

        self._parsed_cli_options = None
        self._parsed_cfg_options = None

    def __getattr__(self, name):
        return self.get(name)

    def add_option(self, *args, **kwds):
        """Wrap the OptionParser.add_option() method, and add our options."""
        try:
            # We can't pass unknown kwds to make_option, or it will barf.
            is_required = kwds.pop('required')
        except KeyError:
            is_required = False

        option = optparse.make_option(*args, **kwds)
        self._optparser.add_option(option)

        if is_required:
            self.add_required_option(option)

        self._add_option_to_cfg_mapping(option, args)

    def add_required_option(self, option):
        """Add a required option.

        Takes an optparse.Option object.
        """
        self.required_options.append(option)

    def _add_option_to_cfg_mapping(self, option, option_constructor_args):
        # Convert the long options into .ini keys.  Use the last long option
        # given.
        for switch in reversed(option_constructor_args):
            if switch.startswith('--'):
                # We found a '--foo' switch, so use it.  Drop the '--',
                # because the config file doesn't use the prefixes.
                self._option_to_cfgkey[option.dest] = switch[2:]

    def error(self, message):
        """Wrap optparse.OptionParser.error()."""
        self._optparser.error(message)

    def parse_config_file(self, filepath):
        fp = os.path.expanduser(filepath)

        if not os.path.exists(fp):
            self.error("The config file '%s' does not exist!" % fp)

        self._cfgparser.read(fp)
        self._parsed_cfg_options = self._cfgparser.defaults()

        num_opts = len(self._parsed_cfg_options)
        debug("Loaded %d options from %s" % (num_opts, fp))

    def parse_cli_args(self, argv):
        """Wrap optparse.OptionParser.parse_args()."""
        options, args = self._optparser.parse_args(argv)
        self._parsed_cli_options = options
        self.args = args
        return (options, args)

    def verify_options(self):
        """Verify that all required options are there.

        Raise an optparse.OptionParser.error() if something is missing.

        Make sure you parsed the config file with parse_config_file() before
        doing this.
        """
        debug("Verifying options")
        if not self._parsed_cfg_options:
            debug("No config file options found")

        for option in self.required_options:
            # Check for a command-line option.

            option_name = option.dest

            if self.get(option_name) is None:
                self._required_option_error(option)
            else:
                debug("Found required option: %s" % option_name)

    def _required_option_error(self, option):
        msg = "Required option '%s' was not given (-h for help)" % str(option)
        self.error(msg)

    def get(self, name, default=None):
        """Return the appropriate option, CLI first, CFG second."""
        cli_name = name
        cfg_name = self._option_to_cfgkey.get(name)

        value = self._getoption(cli_name)

        if value is None and cfg_name is not None:
            # No command-line option was supplied, but we do have a config
            # file entry with that name.
            value = self._getcfg(cfg_name)

            if value is None:
                # No config file option was supplied either, so return the
                # default.
                return default

        return value

    def _getoption(self, key, default=None):
        return getattr(self._parsed_cli_options, key, default)

    def _getcfg(self, key, default=None):
        return self._parsed_cfg_options.get(key, default)


def get_credentials():
    """Return an EC2Credentials object for accessing the webservice."""
    # Get the AWS identifier and secret identifier.
    return ec2test.EC2Credentials.load_from_file()


def parse_config_file(filepath):
    config = ConfigParser.ConfigParser()
    config.read(filepath)
    return config


def parse_options(argv):
    oparser = optparse.OptionParser(usage)
    cparser = ConfigParser.SafeConfigParser()
    parser = CombinedConfigParser(oparser, cparser)

    # What follows are "Required options" - these must be supplied from either
    # the command-line, or from a config file.
    parser.add_option(
        '-k', '--key',
        dest="keypair_name",
        required=True,
        help="The name of the AWS key pair to use for launching instances.")

    parser.add_option(
        '-K', '--private-key',
        dest="private_key",
        required=True,
        help="The X.509 private keyfile that will be used to sign the new "
             "image.")

    parser.add_option(
        '-C', '--cert',
        dest="cert",
        required=True,
        help="The X.509 certificate that will be used to bundle the new "
             "image.")

    parser.add_option(
        '-i', '--identity-file',
        dest='identity_file',
        required=True,
        help="The location of the RSA private key that SSH will use to "
             "connect to the instance.")

    parser.add_option(
        '-b', '--bucket',
        dest="bucket",
        required=True,
        help="The bucket that the image will be placed into.")

    parser.add_option(
        '-u', '--user-id',
        dest="account_id",
        required=True,
        help="Your 12 digit AWS account ID")

    parser.add_option(
        '-a', '--access-key',
        dest="access_key",
        required=True,
        help="Your AWS access key.")

    parser.add_option(
        '-s', '--secret-key',
        dest="secret_key",
        required=True,
        help="Your AWS secret key.")


    # Start our "Optional options."
    parser.add_option(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help="Turn on debug output.")

    parser.add_option(
        '-t', '--instance-type',
        dest="instance_type",
        default="m1.large",
        help="The type of instance to be launched.  Should be the same as "
             "the base image's required type. [default: %default]")

    parser.add_option(
        '-c', '--config',
        dest='config',
        default="~/.ec2/ec2bundle.cfg",
        help="Load script options from the supplied config file. (.ini "
             "format, see the module docstring for details.) "
             "[default: %default]")

    parser.add_option(
        '--keepalive',
        action='store_true',
        dest="keepalive",
        default=False,
        help="Don't shut down the instance when we are done building (or "
             "erroring out).")

    parser.add_option(
        '--no-bundle',
        action='store_true',
        dest='no_bundle',
        default=False,
        help="Don't create a bundle, just start the server and configure the "
             "environment.")

    parser.add_option(
        '--use-instance',
        dest='running_instance',
        help="Use the supplied EC2 instance ID, instead of starting our own "
             "server.  The instance will be left running.")


    options, args = parser.parse_cli_args(argv)

    # Do this ASAP
    if options.verbose:
        log.setLevel(logging.DEBUG)

    if options.config:
        parser.parse_config_file(options.config)

    # Make sure all the required args are present.  Will error-out if
    # something is missing.
    parser.verify_options()

    if len(args) != 2:
        parser.error("You must provide an AMI ID that can serve as the new "
                     "image's base.")

    return parser


def main(argv):
    config = parse_options(argv)

    credentials = get_credentials()
    account = credentials.connect(config.keypair_name)

    # Save the flag so we can change it.  This is how we enforce shutdown
    # policies.
    keepalive = config.keepalive

    if config.running_instance:
        # We want to keep the server alive if the user supplied their own
        # instance.  Killing it without their consent would be cruel.
        keepalive = True

    ssh_user_command = None
    try:
        try:
            instance = None
            if config.running_instance:
                # Connect to an already running instance.
                instance = Instance.from_running_instance(
                    account, config.running_instance)
            else:
                # Run an instance for our base image.
                instance = Instance.from_image(
                    account, config.args[1], config.instance_type)

            ssh = SSHConnector(
                instance.hostname, 'root', config.identity_file)
            ssh.connect()
            ssh_user_command = ssh.user_command()

            system_configurator = XvfbSystemConfigurator(ssh)
            system_configurator.configure_system()

            if not config.no_bundle:
                bundler = ImageBundler(
                    config.private_key,
                    config.cert,
                    config.account_id,
                    config.bucket,
                    config.access_key,
                    config.secret_key,
                    ssh)
                bundler.bundle_image()

        except:
            # Log the exception now so it doesn't interfere with or get eaten
            # by the instance shutdown.
            log.exception("Oops!")
    finally:
        if keepalive:
            log.warning("instance %s is now running on its own" % instance.id)
            if ssh_user_command:
                info("You may now ssh into the instance using the following command:")
                info("  $ %s" % ssh_user_command)

            log.warning("Remember to shut the instance down when you are done!")
        else:
            instance.stop()


if __name__ == '__main__':
    logging.basicConfig()
    main(sys.argv)
