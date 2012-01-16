#!/usr/bin/env python
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Set up this box to act as an lxc test machine"""

__metaclass__ = type
__all__ = []

# This script is run as root.
# To run doctests: python -m doctest -v setuplxc.py

from contextlib import contextmanager
import argparse
import os
import pwd
import shutil
import subprocess
import sys
import time


LXC_NAME = 'lptests'
LXC_OPTIONS = {
    'lxc.network.type': 'veth',
    'lxc.network.link': 'virbr0',
    'lxc.network.flags': 'up',
    }
LXC_PATH = '/var/lib/lxc/'
LXC_REPOS = (
    'deb http://archive.ubuntu.com/ubuntu '
    'lucid main universe multiverse',
    'deb http://archive.ubuntu.com/ubuntu '
    'lucid-updates main universe multiverse',
    'deb http://archive.ubuntu.com/ubuntu '
    'lucid-security main universe multiverse',
    'deb http://ppa.launchpad.net/launchpad/ppa/ubuntu lucid main',
    'deb http://ppa.launchpad.net/bzr/ppa/ubuntu lucid main',
    )
DEPENDENCIES_DIR = '~/dependencies'
HOST_PACKAGES = ['ssh', 'lxc', 'libvirt-bin', 'bzr']
RESOLV_FILE = '/etc/resolv.conf'
LP_SOURCE_DEPS = (
    'http://bazaar.launchpad.net/~launchpad/lp-source-dependencies/trunk')


@contextmanager
def ssh(location, user=None):
    """Return a callable that can be used to run shell commands into another
    host using ssh.

    The ssh `location` and, optionally, `user` must be given.
    If the user is None then the current user is used for the connection.
    """
    sshcmd = 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    if user is not None:
        location = '%s@%s' % (user, location)
    yield lambda cmd: subprocess.call([sshcmd, location, '--', "'%s'" % cmd])


def get_user_ids(user):
    """Return the uid and gid of given `user`, e.g.::

        >>> get_user_ids('root')
        (0, 0)
    """
    userdata = pwd.getpwnam(user)
    return userdata.pw_uid, userdata.pw_gid


@contextmanager
def su(user):
    """A context manager to temporary run the Python interpreter as a
    different user.
    """
    uid, gid = get_user_ids(user)
    os.setegid(gid)
    os.seteuid(uid)
    yield uid, gid
    os.setegid(os.getgid())
    os.seteuid(os.getuid())


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


def get_container_path(lxcname, path=''):
    """Return the path of LXC container called `lxcname`.
    If a `path` is given, return that path inside the container, e.g.::

        >>> get_container_path('mycontainer')
        '/var/lib/lxc/mycontainer/rootfs/'
        >>> get_container_path('mycontainer', '/etc/apt/')
        '/var/lib/lxc/mycontainer/rootfs/etc/apt/'
        >>> get_container_path('mycontainer', 'home')
        '/var/lib/lxc/mycontainer/rootfs/home'
    """
    return os.path.join(LXC_PATH, lxcname, 'rootfs', path.lstrip('/'))


def error(msg):
    """Print out the error message and quit the script."""
    print msg
    sys.exit(1)


parser = argparse.ArgumentParser(
    description='Create an LXC test environment for Launchpad testing.')
parser.add_argument(
    '-u', '--user', required=True,
    help=('The name of the system user to be created.'))
parser.add_argument(
    '-e', '--email', required=True,
    help=('The email of the user, used for bzr whoami.'))
parser.add_argument(
    '-m', '--name', required=True,
    help=('The full name of the user, used fo bzr whoami.'))
parser.add_argument(
    '-l', '--lpuser',
    help=('The name of the Launchpad user that will be used to check out '
          'dependencies.  If not provided, the system user name is used.'))
parser.add_argument(
    '-v', '--private-key', required=True,
    help='The SSH private key for the Launchpad user.')
parser.add_argument(
    '-b', '--public-key', required=True,
    help='The SSH public key for the Launchpad user.')
parser.add_argument(
    'directory',
    help='The directory of the Launchpad repository to be created.')


def initialize_host(
    user, fullname, email, lpuser, private_key, public_key, directory):
    """Initialize host machine."""
    # Install necessary deb packages.  This requires Oneiric or later.
    subprocess.call(['apt-get', '-y', 'install'] + HOST_PACKAGES)
    # Make the user.
    subprocess.call(['useradd', '-m', '-s', '/bin/bash', '-U', user])
    # Get the user's uid and gid, and run as user.
    with su(user) as (uid, gid):
        # Set up the user's ssh directory.  The ssh key must be associated
        # with the lpuser's Launchpad account.
        home_dir = os.path.join(os.path.sep, 'home', user)
        ssh_dir = os.path.join(home_dir, '.ssh')
        os.makedirs(ssh_dir)
        priv_file = os.path.join(ssh_dir, 'id_rsa')
        pub_file = os.path.join(ssh_dir, 'id_rsa.pub')
        auth_file = os.path.join(ssh_dir, 'authorized_keys')
        for filename, contents in [
            (priv_file, private_key),
            (pub_file, public_key),
            (auth_file, public_key),
            ]:
            with open(filename, 'w') as f:
                f.write(contents)
            os.chmod(filename, 0644)
        os.chmod(priv_file, 0600)
        # Set up bzr and Launchpad authentication.
        subprocess.call(['bzr', 'whoami', '"%s <%s>"' % (fullname, email)])
        subprocess.call(['bzr', 'lp-login', lpuser])
        # Set up the repository.
        os.makedirs(directory)
        subprocess.call(['bzr', 'init-repo', directory])
        checkout_dir = os.path.join(directory, 'lp')
        subprocess.call(['bzr', 'branch', 'lp:launchpad', checkout_dir])
        # Set up source dependencies.
        os.makedirs('%s/eggs' % DEPENDENCIES_DIR)
        os.makedirs('%s/yui' % DEPENDENCIES_DIR)
        with cd(checkout_dir):
            subprocess.call(['utilities/update-sourcecode', DEPENDENCIES_DIR])
        with cd(DEPENDENCIES_DIR):
            subprocess.call([
                'bzr co --lightweight', LP_SOURCE_DEPS, 'download-cache'])
    # Update resolv file in order to get the ability to ssh into the LXC
    # container using its name.
    with open(RESOLV_FILE, 'r+') as f:
        lines = f.readlines()
        line = 'nameserver 192.168.122.1\n'
        if lines[0] != line:
            lines.insert(0, line)
            f.seek(0)
            f.writelines(lines)


def create_lxc(user, lxcname):
    """Create the LXC container that will be used for ephemeral instances."""
    config_template = '/etc/lxc/local.conf'
    # Container configuration template.
    content = '\n'.join('%s=%s' % i for i in LXC_OPTIONS.items())
    with open(config_template, 'w') as f:
        f.write(content)
    # Creating container.
    subprocess.call(
        'lxc-create -t ubuntu -n %s -f %s -- '
        '-r lucid -a i386 -b %s' % (lxcname, config_template, user))
    subprocess.call('lxc-start -n %s -d' % lxcname)
    # SSH the container
    timeout = 30
    with ssh(user, lxcname) as sshcall:
        while timeout:
            if not sshcall('true'):
                break
            timeout -= 1
            time.sleep(1)
        else:
            error('Impossible to SSH into LXC.')
    # Set up root ssh key.
    src = '/home/%s/.ssh/authorized_keys' % user
    dst = get_container_path(lxcname, '/root/.ssh/')
    os.makedirs(dst)
    shutil.copy(src, dst)


def initialize_lxc(user, directory, lxcname):
    """Set up the Launchpad development environment inside the LXC container.
    """
    with ssh(lxcname) as sshcall:
        # APT repository update.
        sources = get_container_path(lxcname, '/etc/apt/sources.list')
        with open(sources, 'w') as f:
            f.write('\n'.join(LXC_REPOS))
        # XXX frankban 2012-01-13 - Bug 892892: upgrading mountall in LXC
        # containers currently does not work
        sshcall("echo 'mountall hold' | dpkg --set-selections")
        # Upgrading packages.
        sshcall(
            'apt-get update && '
            'apt-get -y install bzr launchpad-developer-dependencies')
        # User configuration.
        sshcall('adduser %s sudo' % user)
        pygetgid = 'import pwd; print pwd.getpwnam("%s").pw_gid' % user
        gid = "`python -c '%s'`" % pygetgid
        sshcall('addgroup --gid %s %s' % (gid, user))
    with ssh(lxcname, user) as sshcall:
        # Launchpad database setup.
        sshcall(
            'cd %s && utilities/launchpad-database-setup %s' % (
            directory, user))
        sshcall(
            'cd %s && utilities/link-external-sourcecode %s' % (
            directory, DEPENDENCIES_DIR))
        # Probably unnecessary (just a test).
        sshcall('cd %s && make schema' % directory)
        sshcall('cd %s && make install' % directory)


def stop_lxc(lxcname):
    """Stop the lxc instance named `lxcname`."""
    pass


def main(user, fullname, email, lpuser, private_key, public_key, directory):
    initialize_host(
        user, fullname, email, lpuser, private_key, public_key, directory)
    create_lxc(user, LXC_NAME)
    initialize_lxc(user, directory, LXC_NAME)


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.user,
         args.fullname,
         args.email,
         args.lpuser or args.user,
         args.private_key,
         args.public_key,
         args.directory)
