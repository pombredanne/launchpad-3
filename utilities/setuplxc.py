#!/usr/bin/env python
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create an LXC test environment for Launchpad testing."""

__metaclass__ = type
__all__ = [
    'ArgumentParser',
    'cd',
    'create_lxc',
    'create_scripts',
    'file_append',
    'file_prepend',
    'get_container_path',
    'get_user_home',
    'get_user_ids',
    'initialize_host',
    'initialize_lxc',
    'SetupLXCError',
    'ssh',
    'SSHError',
    'stop_lxc',
    'su',
    'user_exists',
    'ValidationError',
    ]

# To run doctests: python -m doctest -v setuplxc.py

from collections import namedtuple, OrderedDict
from contextlib import contextmanager
from email.Utils import parseaddr, formataddr
import argparse
import os
import platform
import pwd
import re
import shutil
import subprocess
import sys
import textwrap
import time

APT_REPOSITORIES = (
    'deb http://archive.ubuntu.com/ubuntu {distro} multiverse',
    'deb http://archive.ubuntu.com/ubuntu {distro}-updates multiverse',
    'deb http://archive.ubuntu.com/ubuntu {distro}-security multiverse',
    'ppa:launchpad/ppa',
    'ppa:bzr/ppa',
    # XXX 2012-03-19 frankban bug=955006:
    #     The yellow PPA contains an updated version of testrepository
    #     that fixes the encoding issue.
    'ppa:yellow/ppa',
    )
DEPENDENCIES_DIR = '~/dependencies'
DHCP_FILE = '/etc/dhcp/dhclient.conf'
HOST_PACKAGES = ['ssh', 'lxc', 'libvirt-bin', 'bzr', 'testrepository',
    'python-shell-toolbox']
HOSTS_FILE = '/etc/hosts'
MAILNAME_FILE = '/etc/mailname'
LP_APACHE_MODULES = 'proxy proxy_http rewrite ssl deflate headers'
LP_APACHE_ROOTS = (
    '/var/tmp/bazaar.launchpad.dev/static',
    '/var/tmp/archive',
    '/var/tmp/ppa',
    )
LP_CHECKOUT = 'devel'
LP_DEB_DEPENDENCIES = (
    'bzr launchpad-developer-dependencies apache2 '
    'apache2-mpm-worker libapache2-mod-wsgi')
LP_REPOSITORIES = (
    'http://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel',
    'lp:launchpad',
    )
LP_SOURCE_DEPS = (
    'http://bazaar.launchpad.net/~launchpad/lp-source-dependencies/trunk')
LXC_CONFIG_TEMPLATE = '/etc/lxc/local.conf'
LXC_GUEST_OS = 'lucid'
LXC_HOSTS_CONTENT = (
    ('127.0.0.88',
        'launchpad.dev answers.launchpad.dev archive.launchpad.dev '
        'api.launchpad.dev bazaar-internal.launchpad.dev beta.launchpad.dev '
        'blueprints.launchpad.dev bugs.launchpad.dev code.launchpad.dev '
        'feeds.launchpad.dev id.launchpad.dev keyserver.launchpad.dev '
        'lists.launchpad.dev openid.launchpad.dev '
        'ubuntu-openid.launchpad.dev ppa.launchpad.dev '
        'private-ppa.launchpad.dev testopenid.dev translations.launchpad.dev '
        'xmlrpc-private.launchpad.dev xmlrpc.launchpad.dev'),
    ('127.0.0.99', 'bazaar.launchpad.dev'),
    )
LXC_NAME = 'lptests'
LXC_OPTIONS = """
lxc.network.type = veth
lxc.network.link = {interface}
lxc.network.flags = up
"""
LXC_PATH = '/var/lib/lxc/'
RESOLV_FILE = '/etc/resolv.conf'
SSH_KEY_NAME = 'id_rsa'


Env = namedtuple('Env', 'uid gid home')


class SetupLXCError(Exception):
    """Base exception for setuplxc."""


class SSHError(SetupLXCError):
    """Errors occurred during SSH connection."""


class ValidationError(SetupLXCError):
    """Argparse invalid arguments."""


def bzr_whois(user):
    """Return fullname and email of bzr `user`.

    Return None if the given `user` does not have a bzr user id.
    """
    with su(user):
        try:
            whoami = subprocess.check_output(['bzr', 'whoami'])
        except (subprocess.CalledProcessError, OSError):
            return None
    return parseaddr(whoami)


@contextmanager
def cd(directory):
    """A context manager to temporary change current working dir, e.g.::

        >>> import os
        >>> os.chdir('/tmp')
        >>> with cd('/bin'): print os.getcwd()
        /bin
        >>> os.getcwd()
        '/tmp'
    """
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


def file_append(filename, line):
    r"""Append given `line`, if not present, at the end of `filename`.

    Usage example::

        >>> import tempfile
        >>> f = tempfile.NamedTemporaryFile('w', delete=False)
        >>> f.write('line1\n')
        >>> f.close()
        >>> file_append(f.name, 'new line\n')
        >>> open(f.name).read()
        'line1\nnew line\n'

    Nothing happens if the file already contains the given `line`::

        >>> file_append(f.name, 'new line\n')
        >>> open(f.name).read()
        'line1\nnew line\n'

    A new line is automatically added before the given `line` if it is not
    present at the end of current file content::

        >>> import tempfile
        >>> f = tempfile.NamedTemporaryFile('w', delete=False)
        >>> f.write('line1')
        >>> f.close()
        >>> file_append(f.name, 'new line\n')
        >>> open(f.name).read()
        'line1\nnew line\n'
    """
    with open(filename, 'a+') as f:
        content = f.read()
        if line not in content:
            if content.endswith('\n'):
                f.write(line)
            else:
                f.write('\n' + line)


def file_prepend(filename, line):
    r"""Insert given `line`, if not present, at the beginning of `filename`.

    Usage example::

        >>> import tempfile
        >>> f = tempfile.NamedTemporaryFile('w', delete=False)
        >>> f.write('line1\n')
        >>> f.close()
        >>> file_prepend(f.name, 'line0\n')
        >>> open(f.name).read()
        'line0\nline1\n'

    If the file starts with the given `line`, nothing happens::

        >>> file_prepend(f.name, 'line0\n')
        >>> open(f.name).read()
        'line0\nline1\n'

    If the file contains the given `line`, but not at the beginning,
    the line is moved on top::

        >>> file_prepend(f.name, 'line1\n')
        >>> open(f.name).read()
        'line1\nline0\n'
    """
    with open(filename, 'r+') as f:
        lines = f.readlines()
        if lines[0] != line:
            if line in lines:
                lines.remove(line)
            lines.insert(0, line)
            f.seek(0)
            f.writelines(lines)


def generate_ssh_keys(path):
    """Generate ssh key pair, saving them inside the given `directory`.

        >>> generate_ssh_keys('/tmp/id_rsa')
        0
        >>> open('/tmp/id_rsa').readlines()[0].strip()
        '-----BEGIN RSA PRIVATE KEY-----'
        >>> open('/tmp/id_rsa.pub').read().startswith('ssh-rsa')
        True
        >>> os.remove('/tmp/id_rsa')
        >>> os.remove('/tmp/id_rsa.pub')
    """
    return subprocess.call([
        'ssh-keygen', '-q', '-t', 'rsa', '-N', '', '-f', path])


def get_container_path(lxcname, path='', base_path=LXC_PATH):
    """Return the path of LXC container called `lxcname`.

    If a `path` is given, return that path inside the container, e.g.::

        >>> get_container_path('mycontainer')
        '/var/lib/lxc/mycontainer/rootfs/'
        >>> get_container_path('mycontainer', '/etc/apt/')
        '/var/lib/lxc/mycontainer/rootfs/etc/apt/'
        >>> get_container_path('mycontainer', 'home')
        '/var/lib/lxc/mycontainer/rootfs/home'
    """
    return os.path.join(base_path, lxcname, 'rootfs', path.lstrip('/'))


def get_lxc_gateway():
    """Return a tuple of gateway name and address.

    The gateway name and address will change depending on which version
    of Ubuntu the script is running on.
    """
    release_name = platform.linux_distribution()[2]
    if release_name == 'oneiric':
        return 'virbr0', '192.168.122.1'
    else:
        return 'lxcbr0', '10.0.3.1'


def get_user_ids(user):
    """Return the uid and gid of given `user`, e.g.::

        >>> get_user_ids('root')
        (0, 0)
    """
    userdata = pwd.getpwnam(user)
    return userdata.pw_uid, userdata.pw_gid


def get_user_home(user):
    """Return the home directory of the given `user`.

        >>> get_user_home('root')
        '/root'
    """
    return pwd.getpwnam(user).pw_dir


def ssh(location, user=None, key=None, caller=subprocess.call):
    """Return a callable that can be used to run ssh shell commands.

    The ssh `location` and, optionally, `user` must be given.
    If the user is None then the current user is used for the connection.

    The callable internally uses the given `caller`::

        >>> def caller(cmd):
        ...     print tuple(cmd)
        >>> sshcall = ssh('example.com', 'myuser', caller=caller)
        >>> root_sshcall = ssh('example.com', caller=caller)
        >>> sshcall('ls -l') # doctest: +ELLIPSIS
        ('ssh', '-t', ..., 'myuser@example.com', '--', 'ls -l')
        >>> root_sshcall('ls -l') # doctest: +ELLIPSIS
        ('ssh', '-t', ..., 'example.com', '--', 'ls -l')

    The ssh key path can be optionally provided::

        >>> root_sshcall = ssh('example.com', key='/tmp/foo', caller=caller)
        >>> root_sshcall('ls -l') # doctest: +ELLIPSIS
        ('ssh', '-t', ..., '-i', '/tmp/foo', 'example.com', '--', 'ls -l')


    If the ssh command exits with an error code, an `SSHError` is raised::

        >>> ssh('loc', caller=lambda cmd: 1)('ls -l') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        SSHError: ...

    If ignore_errors is set to True when executing the command, no error
    will be raised, even if the command itself returns an error code.

        >>> sshcall = ssh('loc', caller=lambda cmd: 1)
        >>> sshcall('ls -l', ignore_errors=True)
    """
    sshcmd = [
        'ssh',
        '-t',
        '-t',  # Yes, this second -t is deliberate. See `man ssh`.
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        ]
    if key is not None:
        sshcmd.extend(['-i', key])
    if user is not None:
        location = '{}@{}'.format(user, location)
    sshcmd.extend([location, '--'])

    def _sshcall(cmd, ignore_errors=False):
        command = sshcmd + [cmd]
        if caller(command) and not ignore_errors:
            raise SSHError('Error running command: ' + ' '.join(command))

    return _sshcall


@contextmanager
def su(user):
    """A context manager to temporary run the script as a different user."""
    uid, gid = get_user_ids(user)
    os.setegid(gid)
    os.seteuid(uid)
    current_home = os.getenv('HOME')
    home = get_user_home(user)
    os.environ['HOME'] = home
    try:
        yield Env(uid, gid, home)
    finally:
        os.setegid(os.getgid())
        os.seteuid(os.getuid())
        if current_home is not None:
            os.environ['HOME'] = current_home


def user_exists(username):
    """Return True if given `username` exists, e.g.::

        >>> user_exists('root')
        True
        >>> user_exists('_this_user_does_not_exist_')
        False
    """
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    return True


class ArgumentParser(argparse.ArgumentParser):
    """A customized parser for argparse."""

    validators = ()

    def get_args_from_namespace(self, namespace):
        """Return a list of arguments taking values from `namespace`.

        Having a parser defined as usual::

            >>> parser = ArgumentParser()
            >>> _ = parser.add_argument('--foo')
            >>> _ = parser.add_argument('bar')
            >>> namespace = parser.parse_args('--foo eggs spam'.split())

        It is possible to recreate the argument list taking values from
        a different namespace::

            >>> namespace.foo = 'changed'
            >>> parser.get_args_from_namespace(namespace)
            ['--foo', 'changed', 'spam']
        """
        args = []
        for action in self._actions:
            dest = action.dest
            option_strings = action.option_strings
            value = getattr(namespace, dest, None)
            if value:
                if option_strings:
                    args.append(option_strings[0])
                if isinstance(value, list):
                    args.extend(value)
                elif not isinstance(value, bool):
                    args.append(value)
        return args

    def _validate(self, namespace):
        for validator in self.validators:
            try:
                validator(namespace)
            except ValidationError as err:
                self.error(err.message)

    def parse_args(self, *args, **kwargs):
        """Override to add further arguments cleaning and validation.

        `self.validators` can contain an iterable of objects that are called
        once the arguments namespace is fully populated.
        This allows cleaning and validating arguments that depend on
        each other, or on the current environment.

        Each validator is a callable object, takes the current namespace
        and can raise ValidationError if the arguments are not valid::

            >>> import sys
            >>> stderr, sys.stderr = sys.stderr, sys.stdout
            >>> def validator(namespace):
            ...     raise ValidationError('nothing is going on')
            >>> parser = ArgumentParser()
            >>> parser.validators = [validator]
            >>> parser.parse_args([])
            Traceback (most recent call last):
            SystemExit: 2
            >>> sys.stderr = stderr
        """
        namespace = super(ArgumentParser, self).parse_args(*args, **kwargs)
        self._validate(namespace)
        return namespace


def handle_users(namespace, euid=None):
    """Handle user and lpuser arguments.

    If lpuser is not provided by namespace, the user name is used::

        >>> import getpass
        >>> username = getpass.getuser()

        >>> namespace = argparse.Namespace(user=username, lpuser=None)
        >>> handle_users(namespace)
        >>> namespace.lpuser == username
        True

    This validator populates namespace with `home_dir` and `run_as_root`
    names::

        >>> handle_users(namespace, euid=0)
        >>> namespace.home_dir == '/home/' + username
        True
        >>> namespace.run_as_root
        True

    The validation fails if the current user is root and no user is provided::

        >>> namespace = argparse.Namespace(user=None)
        >>> handle_users(namespace, euid=0) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: argument user ...
    """
    if euid is None:
        euid = os.geteuid()
    if namespace.user is None:
        if not euid:
            raise ValidationError('argument user can not be omitted if '
                                  'the script is run as root.')
        namespace.user = pwd.getpwuid(euid).pw_name
    if namespace.lpuser is None:
        namespace.lpuser = namespace.user
    namespace.home_dir = get_user_home(namespace.user)
    namespace.run_as_root = not euid


def handle_userdata(namespace, whois=bzr_whois):
    """Handle full_name and email arguments.

    If they are not provided, this function tries to obtain them using
    the given `whois` callable::

        >>> namespace = argparse.Namespace(
        ...     full_name=None, email=None, user='foo')
        >>> email = 'email@example.com'
        >>> handle_userdata(namespace, lambda user: (user, email))
        >>> namespace.full_name == namespace.user
        True
        >>> namespace.email == email
        True

    The validation fails if full_name or email are not provided and
    they can not be obtained using the `whois` callable::

        >>> namespace = argparse.Namespace(
        ...     full_name=None, email=None, user='foo')
        >>> handle_userdata(namespace, lambda user: None) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: arguments full-name ...

    It does not make sense to provide only one argument::

        >>> namespace = argparse.Namespace(full_name='Foo Bar', email=None)
        >>> handle_userdata(namespace) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: arguments full-name ...
    """
    args = (namespace.full_name, namespace.email)
    if not all(args):
        if any(args):
            raise ValidationError(
                'arguments full-name and email: '
                'either none or both must be provided.')
        userdata = whois(namespace.user)
        if userdata is None:
            raise ValidationError(
                'arguments full-name and email are required: '
                'bzr user id not found.')
        namespace.full_name, namespace.email = userdata


def handle_ssh_keys(namespace):
    r"""Handle private and public ssh keys.

    Keys contained in the namespace are escaped::

        >>> private = r'PRIVATE\nKEY'
        >>> public = r'PUBLIC\nKEY'
        >>> namespace = argparse.Namespace(
        ...     private_key=private, public_key=public,
        ...     ssh_key_name='id_rsa', home_dir='/tmp/')
        >>> handle_ssh_keys(namespace)
        >>> namespace.private_key == private.decode('string-escape')
        True
        >>> namespace.public_key == public.decode('string-escape')
        True

    After this handler is called, the ssh key path is present as an attribute
    of the namespace::

        >>> namespace.ssh_key_path
        '/tmp/.ssh/id_rsa'

    Keys are None if they are not provided and can not be found in the
    current home directory::

        >>> namespace = argparse.Namespace(
        ...     private_key=None, public_key=None, ssh_key_name='id_rsa',
        ...     home_dir='/tmp/__does_not_exists__')
        >>> handle_ssh_keys(namespace) # doctest: +ELLIPSIS
        >>> print namespace.private_key
        None
        >>> print namespace.public_key
        None

    If only one of private_key and public_key is provided, a
    ValidationError will be raised.

        >>> namespace = argparse.Namespace(
        ...     private_key=private, public_key=None, ssh_key_name='id_rsa',
        ...     home_dir='/tmp/__does_not_exists__')
        >>> handle_ssh_keys(namespace) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: arguments private-key...
    """
    namespace.ssh_key_path = os.path.join(
        namespace.home_dir, '.ssh', namespace.ssh_key_name)
    for attr, path in (
        ('private_key', namespace.ssh_key_path),
        ('public_key', namespace.ssh_key_path + '.pub')):
        value = getattr(namespace, attr)
        if value:
            setattr(namespace, attr, value.decode('string-escape'))
        else:
            try:
                value = open(path).read()
            except IOError:
                value = None
            setattr(namespace, attr, value)
    if bool(namespace.private_key) != bool(namespace.public_key):
        raise ValidationError(
            "arguments private-key and public-key: "
            "both must be provided or neither must be provided.")


def handle_directories(namespace):
    """Handle checkout and dependencies directories.

    The ~ construction is automatically expanded::

        >>> namespace = argparse.Namespace(
        ...     directory='~/launchpad', dependencies_dir='~/launchpad/deps',
        ...     home_dir='/home/foo')
        >>> handle_directories(namespace)
        >>> namespace.directory
        '/home/foo/launchpad'
        >>> namespace.dependencies_dir
        '/home/foo/launchpad/deps'

    The validation fails for directories not residing inside the home::

        >>> namespace = argparse.Namespace(
        ...     directory='/tmp/launchpad',
        ...     dependencies_dir='~/launchpad/deps',
        ...     home_dir='/home/foo')
        >>> handle_directories(namespace) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: argument directory ...

    The validation fails if the directory contains spaces::

        >>> namespace = argparse.Namespace(directory='my directory')
        >>> handle_directories(namespace) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ValidationError: argument directory ...
    """
    if ' ' in namespace.directory:
        raise ValidationError('argument directory can not contain spaces.')
    for attr in ('directory', 'dependencies_dir'):
        directory = getattr(
            namespace, attr).replace('~', namespace.home_dir)
        if not directory.startswith(namespace.home_dir + os.path.sep):
            raise ValidationError(
                'argument {} does not reside under the home '
                'directory of the system user.'.format(attr))
        setattr(namespace, attr, directory)


parser = ArgumentParser(description=__doc__)
parser.add_argument(
    '-u', '--user',
    help='The name of the system user to be created or updated. '
         'The current user is used if this script is not run as root '
         'and this argument is omitted.')
parser.add_argument(
    '-e', '--email',
    help='The email of the user, used for bzr whoami. This argument can '
         'be omitted if a bzr id exists for current user.')
parser.add_argument(
    '-f', '--full-name',
    help='The full name of the user, used for bzr whoami. This argument can '
         'be omitted if a bzr id exists for current user.')
parser.add_argument(
    '-l', '--lpuser',
    help='The name of the Launchpad user that will be used to check out '
         'dependencies.  If not provided, the system user name is used.')
parser.add_argument(
    '-v', '--private-key',
    help='The SSH private key for the Launchpad user (without passphrase). '
         'If this argument is omitted and a keypair is not found in the '
         'home directory of the system user a new SSH keypair will be '
         'generated and the checkout of the Launchpad code will use HTTP '
         'rather than bzr+ssh.')
parser.add_argument(
    '-b', '--public-key',
    help='The SSH public key for the Launchpad user. '
         'If this argument is omitted and a keypair is not found in the '
         'home directory of the system user a new SSH keypair will be '
         'generated and the checkout of the Launchpad code will use HTTP '
         'rather than bzr+ssh.')
parser.add_argument(
    '-a', '--actions', nargs='+',
    choices=('initialize_host', 'create_scripts', 'create_lxc',
             'initialize_lxc', 'stop_lxc'),
    help='Only for debugging. Call one or more internal functions.')
parser.add_argument(
    '-n', '--lxc-name', default=LXC_NAME,
    metavar='LXC_NAME (default={})'.format(LXC_NAME),
    help='The LXC container name.')
parser.add_argument(
    '-s', '--ssh-key-name', default=SSH_KEY_NAME,
    metavar='SSH_KEY_NAME (default={})'.format(SSH_KEY_NAME),
    help='The ssh key name used to connect to the LXC container.')
parser.add_argument(
    '-d', '--dependencies-dir', default=DEPENDENCIES_DIR,
    metavar='DEPENDENCIES_DIR (default={})'.format(DEPENDENCIES_DIR),
    help='The directory of the Launchpad dependencies to be created. '
         'The directory must reside under the home directory of the '
         'given user (see -u argument).')
parser.add_argument(
    '-U', '--use-urandom', action='store_true',
    help='Use /dev/urandom to feed /dev/random and avoid entropy exhaustion.')
parser.add_argument(
    'directory',
    help='The directory of the Launchpad repository to be created. '
         'The directory must reside under the home directory of the '
         'given user (see -u argument).')
parser.validators = (
    handle_users,
    handle_userdata,
    handle_ssh_keys,
    handle_directories,
    )


def initialize_host(
    user, fullname, email, lpuser, private_key, public_key, ssh_key_path,
    use_urandom, dependencies_dir, directory):
    """Initialize host machine."""
    # Install necessary deb packages.  This requires Oneiric or later.
    subprocess.call(['apt-get', 'update'])
    subprocess.call(['apt-get', '-y', 'install'] + HOST_PACKAGES)
    # Create the user (if he does not exist).
    if not user_exists(user):
        subprocess.call(['useradd', '-m', '-s', '/bin/bash', '-U', user])
    with su(user) as env:
        # Set up the user's ssh directory.  The ssh key must be associated
        # with the lpuser's Launchpad account.
        ssh_dir = os.path.join(env.home, '.ssh')
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir)
        # Generate user ssh keys if none are supplied.
        valid_ssh_keys = True
        pub_key_path = ssh_key_path + '.pub'
        if private_key is None:
            generate_ssh_keys(ssh_key_path)
            private_key = open(ssh_key_path).read()
            public_key = open(pub_key_path).read()
            valid_ssh_keys = False
        auth_file = os.path.join(ssh_dir, 'authorized_keys')
        known_hosts = os.path.join(ssh_dir, 'known_hosts')
        known_host_content = subprocess.check_output([
            'ssh-keyscan', '-t', 'rsa', 'bazaar.launchpad.net'])
        for filename, contents, mode in [
            (ssh_key_path, private_key, 'w'),
            (pub_key_path, public_key, 'w'),
            (auth_file, public_key, 'a'),
            (known_hosts, known_host_content, 'a'),
            ]:
            with open(filename, mode) as f:
                f.write('{}\n'.format(contents))
            os.chmod(filename, 0644)
        os.chmod(ssh_key_path, 0600)
        # Set up bzr and Launchpad authentication.
        subprocess.call(['bzr', 'whoami', formataddr((fullname, email))])
        if valid_ssh_keys:
            subprocess.call(['bzr', 'lp-login', lpuser])
        # Set up the repository.
        if not os.path.exists(directory):
            os.makedirs(directory)
        subprocess.call(['bzr', 'init-repo', directory])
        checkout_dir = os.path.join(directory, LP_CHECKOUT)
    # bzr branch does not work well with seteuid.
    repository = LP_REPOSITORIES[1] if valid_ssh_keys else LP_REPOSITORIES[0]
    subprocess.call([
        'su', '-', user, '-c',
        'bzr branch {} "{}"'.format(repository, checkout_dir)])
    with su(user) as env:
        # Set up source dependencies.
        for subdir in ('eggs', 'yui', 'sourcecode'):
            path = os.path.join(dependencies_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
    with cd(dependencies_dir):
        with su(user) as env:
            subprocess.call([
                'bzr', 'co', '--lightweight',
                LP_SOURCE_DEPS, 'download-cache'])
    # rng-tools is used to set /dev/urandom as random data source, avoiding
    # entropy exhaustion during automated parallel tests.
    if use_urandom:
        subprocess.call(['apt-get', '-y', 'install', 'rng-tools'])
        file_append('/etc/default/rng-tools', 'HRNGDEVICE=/dev/urandom')
        subprocess.call(['/etc/init.d/rng-tools', 'start'])


def create_scripts(user, lxcname, ssh_key_path):
    """Create scripts to update the Launchpad environment and run tests."""
    # Leases path in lucid differs from the one in oneiric/precise.
    mapping = {
        'leases1': get_container_path(
            lxcname, '/var/lib/dhcp3/dhclient.eth0.leases'),
        'leases2': get_container_path(
            lxcname, '/var/lib/dhcp/dhclient.eth0.leases'),
        'lxcname': lxcname,
        'pattern':
            r's/.* ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}).*/\1/',
        'ssh_key_path': ssh_key_path,
        'user': user,
        }
    # We need a script that will run the LP build inside LXC.  It is run as
    # root (see below) but drops root once inside the LXC container.
    build_script_file = '/usr/local/bin/launchpad-lxc-build'
    with open(build_script_file, 'w') as script:
        script.write(textwrap.dedent("""\
            #!/bin/sh
            set -ux
            truncate -c -s0 {leases1}
            truncate -c -s0 {leases2}

            lxc-start -n {lxcname} -d
            lxc-wait -n {lxcname} -s RUNNING

            delay=30
            while [ "$delay" -gt 0 -a ! -s {leases1} -a ! -s {leases2} ]
            do
                delay=$(( $delay - 1 ))
                sleep 1
            done

            [ -s {leases1} ] && LEASES={leases1} || LEASES={leases2}
            IP_ADDRESS=`grep fixed-address $LEASES | \\
                tail -n 1 | sed -r '{pattern}'`

            if [ 0 -eq $? -a -n "$IP_ADDRESS" ]; then
                for i in $(seq 1 30); do
                    su {user} -c "/usr/bin/ssh -o StrictHostKeyChecking=no \\
                        -i '{ssh_key_path}' $IP_ADDRESS make -C $PWD schema"
                    if [ ! 255 -eq $? ]; then
                        # If ssh returns 255 then its connection failed.
                        # Anything else is either success (status 0) or a
                        # failure from whatever we ran over the SSH connection.
                        # In those cases we want to stop looping, so we break
                        # here.
                        break;
                    fi
                    sleep 1
                done
            else
                echo "could not get IP address - aborting." >&2
                echo "content of $LEASES:" >&2
                cat $LEASES >&2
            fi

            lxc-stop -n {lxcname}
            lxc-wait -n {lxcname} -s STOPPED
            """.format(**mapping)))
        os.chmod(build_script_file, 0555)
    # We need a script to test launchpad using LXC ephemeral instances.
    test_script_file = '/usr/local/bin/launchpad-lxc-test'
    with open(test_script_file, 'w') as script:
        # We intentionally generate a very long line for the
        # lxc-start-ephemeral command below because ssh does not propagate
        # quotes the way we want.  E.g.,
        #     touch a; touch b; ssh localhost -- ls "a b"
        # succeeds, when it should say that the file "a b" does not exist.
        script.write(textwrap.dedent(re.sub(' {2,}', ' ', """\
            #!/bin/sh
            set -uex
            lxc-start-ephemeral -u {user} -S '{ssh_key_path}' -o {lxcname} -- \
                "xvfb-run --error-file=/var/tmp/xvfb-errors.log \
                --server-args='-screen 0 1024x768x24' \
                -a $PWD/bin/test --shuffle --subunit $@"
            """).format(**mapping)))
    os.chmod(test_script_file, 0555)
    # Create a script for cleaning up cruft possibly left by previous lxc
    # ephemeral containers that were not properly shut down.
    cleanup_script_file = '/usr/local/bin/launchpad-lxc-cleanup'
    with open(cleanup_script_file, 'w') as script:
        script.write(textwrap.dedent('''\
            #!/usr/bin/python
            # Cleanup remnants of LXC containers from previous runs.

            # Runs of LXC may leave cruft laying around that interferes with
            # the next run.  These items need to be cleaned up.

            # 1) Shut down all running containers

            # 2) for every /var/lib/lxc/lptests-tmp-* directory:
            #      umount [directory]/ephemeralbind
            #      umount [directory]
            #      rm -rf [directory]

            # 3) for every /tmp/lxc-lp-* (or something like that?) directory:
            #      umount [directory]
            #      rm -rf [directory]

            # Assumptions:
            #  * This script is run as root.

            import glob
            import os.path
            import re
            from shelltoolbox import run
            import shutil
            import time


            LP_TEST_DIR_PATTERN = "/var/lib/lxc/lptests-tmp-*"
            LXC_LP_DIR_PATTERN = "/tmp/lxc-lp-*"
            PID_RE = re.compile("pid:\s+(\d+)")


            class Scrubber(object):
                """Scrubber will cleanup after lxc ephemeral uncleanliness.

                All running containers will be killed.

                Those directories corresponding the lp_test_dir_pattern will
                be unmounted and removed.  The 'ephemeralbind' subdirectories
                will be unmounted.

                The directories corresponding to the lxc_lp_dir_pattern will
                be unmounted and removed.  No subdirectories will need
                unmounting.
                """
                def __init__(self, user='buildbot',
                             lp_test_dir_pattern=LP_TEST_DIR_PATTERN,
                             lxc_lp_dir_pattern=LXC_LP_DIR_PATTERN):
                    self.lp_test_dir_pattern = lp_test_dir_pattern
                    self.lxc_lp_dir_pattern = lxc_lp_dir_pattern
                    self.user = user

                def umount(self, dir_):
                    if os.path.ismount(dir_):
                        run("umount", dir_)

                def scrubdir(self, dir_, extra):
                    dirs = [dir_]
                    if extra is not None:
                        dirs.insert(0, os.path.join(dir_, extra))
                    for d in dirs:
                        self.umount(d)
                    shutil.rmtree(dir_)

                def scrub(self, pattern, extra=None):
                    for dir_ in glob.glob(pattern):
                        if os.path.isdir(dir_):
                            self.scrubdir(dir_, extra)

                def getPid(self, container):
                    info = run("lxc-info", "-n", container)
                    # lxc-info returns a string containing 'RUNNING' for those
                    # containers that are running followed by 'pid: <pid>', so
                    # that must be parsed.
                    if 'RUNNING' in info:
                        match = PID_RE.search(info)
                        if match:
                            return match.group(1)
                    return None

                def getRunningContainers(self):
                    """Get the running containers.

                    Returns a list of (name, pid) tuples.
                    """
                    output = run("lxc-ls")
                    containers = set(output.split())
                    pidlist = [(c, self.getPid(c)) for c in containers]
                    return [(c,p) for c,p in pidlist if p is not None]

                def killer(self):
                    """Kill all running ephemeral containers."""
                    pids = self.getRunningContainers()
                    if len(pids) > 0:
                        # We can do this the easy way...
                        for name, pid in pids:
                            run("/usr/bin/lxc-stop", "-n", name)
                        time.sleep(2)
                        pids = self.getRunningContainers()
                        # ...or, the hard way.
                        for name, pid in pids:
                            run("kill", "-9", pid)

                def run(self):
                    self.killer()
                    self.scrub(self.lp_test_dir_pattern, "ephemeralbind")
                    self.scrub(self.lxc_lp_dir_pattern)


            if __name__ == '__main__':
                scrubber = Scrubber()
                scrubber.run()
            '''))
    os.chmod(cleanup_script_file, 0555)

    # Add a file to sudoers.d that will let the buildbot user run the above.
    sudoers_file = '/etc/sudoers.d/launchpad-' + user
    with open(sudoers_file, 'w') as sudoers:
        sudoers.write('{} ALL = (ALL) NOPASSWD:'.format(user))
        sudoers.write(' {},'.format(build_script_file))
        sudoers.write(' {},'.format(cleanup_script_file))
        sudoers.write(' {}\n'.format(test_script_file))
        # The sudoers must have this mode or it will be ignored.
    os.chmod(sudoers_file, 0440)
    # XXX 2012-03-13 frankban bug=944386:
    #     Disable hardlink restriction. This workaround needs
    #     to be removed once the kernel bug is resolved.
    procfile = '/proc/sys/kernel/yama/protected_nonaccess_hardlinks'
    with open(procfile, 'w') as f:
        f.write('0\n')


def create_lxc(user, lxcname, ssh_key_path):
    """Create the LXC container that will be used for ephemeral instances."""
    # XXX 2012-02-02 gmb bug=925024:
    #     These calls need to be removed once the lxc vs. apparmor bug
    #     is resolved, since having apparmor enabled for lxc is very
    #     much a Good Thing.
    # Disable the apparmor profiles for lxc so that we don't have
    # problems installing postgres.
    if not os.path.exists('/etc/apparmor.d/disable/usr.bin.lxc-start'):
        subprocess.call([
            'ln', '-s',
            '/etc/apparmor.d/usr.bin.lxc-start',
            '/etc/apparmor.d/disable/'])
    subprocess.call([
        'apparmor_parser', '-R', '/etc/apparmor.d/usr.bin.lxc-start'])
    # Update resolv file in order to get the ability to ssh into the LXC
    # container using its name.
    lxc_gateway_name, lxc_gateway_address = get_lxc_gateway()
    file_prepend(RESOLV_FILE, 'nameserver {}\n'.format(lxc_gateway_address))
    file_append(
        DHCP_FILE,
        'prepend domain-name-servers {};\n'.format(lxc_gateway_address))
    # Container configuration template.
    content = LXC_OPTIONS.format(interface=lxc_gateway_name)
    with open(LXC_CONFIG_TEMPLATE, 'w') as f:
        f.write(content)
    # Creating container.
    exit_code = subprocess.call([
        'lxc-create',
        '-t', 'ubuntu',
        '-n', lxcname,
        '-f', LXC_CONFIG_TEMPLATE,
        '--',
        '-r {} -a i386 -b {}'.format(LXC_GUEST_OS, user),
        ])
    if exit_code:
        raise SetupLXCError('Unable to create the LXC container.')
    # XXX 2012-04-18 frankban bug=974584:
    #     Add a line to the container's fstab to be able to create semaphores
    #     in lxc. This workaround needs to be removed once the lxc bug is
    #     resolved for lucid containers too.
    file_append(
        '/var/lib/lxc/{}/fstab'.format(lxcname),
        'none dev/shm tmpfs defaults 0 0\n')
    subprocess.call(['lxc-start', '-n', lxcname, '-d'])
    # Set up root ssh key.
    user_authorized_keys = os.path.expanduser(
        '~' + user + '/.ssh/authorized_keys')
    dst = get_container_path(lxcname, '/root/.ssh/')
    if not os.path.exists(dst):
        os.makedirs(dst)
    shutil.copy(user_authorized_keys, dst)
    # SSH into the container.
    sshcall = ssh(lxcname, user, key=ssh_key_path)
    trials = 60
    while True:
        trials -= 1
        try:
            sshcall('true')
        except SSHError:
            if not trials:
                raise
            time.sleep(1)
        else:
            break


def initialize_lxc(user, dependencies_dir, directory, lxcname, ssh_key_path):
    """Set up the Launchpad development environment inside the LXC container.
    """
    root_sshcall = ssh(lxcname, key=ssh_key_path)
    sshcall = ssh(lxcname, user, key=ssh_key_path)
    # APT repository update.
    for apt_repository in APT_REPOSITORIES:
        repository = apt_repository.format(distro=LXC_GUEST_OS)
        assume_yes = '' if LXC_GUEST_OS == 'lucid' else '-y'
        root_sshcall('add-apt-repository {} "{}"'.format(
            assume_yes, repository))
    # XXX frankban 2012-01-13 - Bug 892892: upgrading mountall in LXC
    # containers currently does not work.
    root_sshcall("echo 'mountall hold' | dpkg --set-selections")
    # Upgrading packages.
    root_sshcall(
        'apt-get update && DEBIAN_FRONTEND=noninteractive LANG=C apt-get -y '
        'install {}'.format(LP_DEB_DEPENDENCIES))
    # We install lxc in the guest so that lxc-execute will work on the
    # container.  We use --no-install-recommends at the recommendation
    # of the Canonical lxc maintainers because all we need is a file
    # that the base lxc package installs, and so that packages we
    # don't need and that might even cause problems inside the
    # container are not around.
    root_sshcall(
        'DEBIAN_FRONTEND=noninteractive apt-get -y '
        '--no-install-recommends install lxc')
    # User configuration.
    root_sshcall('adduser {} sudo'.format(user))
    pygetgid = 'import pwd; print pwd.getpwnam("{}").pw_gid'.format(user)
    gid = "`python -c '{}'`".format(pygetgid)
    root_sshcall('addgroup --gid {} {}'.format(gid, user), ignore_errors=True)
    # Set up Launchpad dependencies.
    checkout_dir = os.path.join(directory, LP_CHECKOUT)
    sshcall(
        ('cd {} && utilities/update-sourcecode --use-http '
         '"{}/sourcecode"').format(checkout_dir, dependencies_dir))
    sshcall(
        'cd {} && utilities/link-external-sourcecode "{}"'.format(
        checkout_dir, dependencies_dir))
    # Create Apache document roots, to avoid warnings.
    sshcall(' && '.join('mkdir -p {}'.format(i) for i in LP_APACHE_ROOTS))
    # Set up Apache modules.
    for module in LP_APACHE_MODULES.split():
        root_sshcall('a2enmod {}'.format(module))
    # Launchpad database setup.
    root_sshcall(
        'cd {} && utilities/launchpad-database-setup {}'.format(
        checkout_dir, user))
    sshcall('cd {} && make'.format(checkout_dir))
    # Set up container hosts file.
    lines = ['{}\t{}'.format(ip, names) for ip, names in LXC_HOSTS_CONTENT]
    lxc_hosts_file = get_container_path(lxcname, HOSTS_FILE)
    file_append(lxc_hosts_file, '\n'.join(lines))
    # Make and install launchpad.
    root_sshcall('cd {} && make install'.format(checkout_dir))
    # XXX benji 2012-03-19 bug=959352: this is so graphviz will work in an
    # ephemeral container
    root_sshcall('mkdir -p /rootfs/usr/lib')
    root_sshcall('ln -s /usr/lib/graphviz /rootfs/usr/lib/graphviz')
    # XXX: BradCrittenden 2012-04-13 bug=981114: Manually create /etc/mailname
    # or bzrlib gets upset and returns None,None for whoami causing test
    # failures.
    mailname_file = get_container_path(lxcname, MAILNAME_FILE)
    if not os.path.exists(mailname_file):
        with open(mailname_file, 'w') as fd:
            fd.write('localhost')


def stop_lxc(lxcname, ssh_key_path):
    """Stop the lxc instance named `lxcname`."""
    ssh(lxcname, key=ssh_key_path)('poweroff')
    timeout = 30
    while timeout:
        try:
            output = subprocess.check_output([
                'lxc-info', '-n', lxcname], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            pass
        else:
            if 'STOPPED' in output:
                break
        timeout -= 1
        time.sleep(1)
    else:
        subprocess.call(['lxc-stop', '-n', lxcname])


def main(
    user, fullname, email, lpuser, private_key, public_key, actions,
    lxc_name, ssh_key_path, use_urandom, dependencies_dir, directory):
    function_args_map = OrderedDict((
        ('initialize_host', (
            user, fullname, email, lpuser, private_key, public_key,
            ssh_key_path, use_urandom, dependencies_dir, directory)),
        ('create_scripts', (user, lxc_name, ssh_key_path)),
        ('create_lxc', (user, lxc_name, ssh_key_path)),
        ('initialize_lxc', (
            user, dependencies_dir, directory, lxc_name, ssh_key_path)),
        ('stop_lxc', (lxc_name, ssh_key_path)),
        ))
    if actions is None:
        actions = function_args_map.keys()
    scope = globals()
    for action in actions:
        try:
            scope[action](*function_args_map[action])
        except SetupLXCError as err:
            return err


if __name__ == '__main__':
    args = parser.parse_args()
    if args.run_as_root:
        exit_code = main(
            args.user,
            args.full_name,
            args.email,
            args.lpuser,
            args.private_key,
            args.public_key,
            args.actions,
            args.lxc_name,
            args.ssh_key_path,
            args.use_urandom,
            args.dependencies_dir,
            args.directory,
            )
    else:
        # If the script is run as normal user, restart it as root using
        # all the collected arguments. Note that this step requires user
        # interaction: running this script as root is still required
        # for non-interactive setup of the Launchpad environment.
        exit_code = subprocess.call(
            ['sudo', sys.argv[0]] + parser.get_args_from_namespace(args))
    sys.exit(exit_code)
