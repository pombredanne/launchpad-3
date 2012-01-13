#!/usr/bin/env python
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Set up this box to act as an lxc test machine"""

__metaclass__ = type
__all__ = []

# This script is run as root.

import argparse
import os
import pwd
import shutil
import subprocess

# setup-lxc -u frankban -p XXX ~/buildbot/launchpad/

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

def main(user, fullname, email, lpuser, private_key, public_key, directory):
    def usercall(cmd):
        return subprocess.call(
            ['su', '-c', "'" + cmd + "'", user])
    # Install necessary deb packages.  This requires Oneiric or later.
    subprocess.call(
        ['apt-get', '-y', 'install', 'ssh', 'lxc', 'libvirt-bin', 'bzr'])
    # Make the user.
    subprocess.call(['useradd', '-m', '-s', '/bin/bash', '-U', user])
    # Get the user's uid and gid.
    _userdata = pwd.getpwnam(user)
    uid = _userdata.pw_uid
    gid = _userdata.pw_gid
    # Set up the user's ssh directory.  The ssh key must be associated
    # with the lpuser's Launchpad account.
    home = os.path.join(['', 'home', user])
    usercall('mkdir -p ~/.ssh')
    ssh_dir = os.path.join([home, '.ssh'])
    priv_file = os.path.join([ssh_dir, 'id_rsa'])
    pub_file = os.path.join([ssh_dir, 'id_rsa.pub'])
    auth_file = os.path.join([ssh_dir, 'authorized_keys'])
    for filename, contents in [(priv_file, private_key),
         (pub_file, public_key),
         (auth_file, public_key)]:
        with f as open(filename, 'w'):
            f.write(contents)
        os.chown(filename, uid, gid)
        os.chmod(filename, 0644)
    os.chmod(priv_file, 0600)
    # Set up bzr and Launchpad authentication.
    usercall('bzr whoami "%s <%s>"' % (fullname, email))
    usercall('bzr lp-login %s' % lpuser)
    # Set up the repository.
    usercall('mkdir -p %s' % directory)
    usercall('bzr init-repo %s' % directory)
    checkout_dir = os.path.join(directory, 'lp')
    usercall('bzr branch lp:launchpad %s' % checkout_dir)
    resolv_file = '/etc/resolv.conf'
    with open(resolv_file) as f:
        lines = f.readlines()
    lines.insert(0, 'nameserver 192.168.122.1\n')
    with open(resolv_file, 'w') as f:
        f.writelines(lines)
    

if __name__ == '__main__':
    args = parser.parse_args()
    main(args.user,
         args.fullname,
         args.email,
         args.lpuser or args.user,
         args.private_key,
         args.public_key,
         args.directory)
