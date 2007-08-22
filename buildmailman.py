#! /usr/bin/python2.4
#
# Copyright 2007 Canonical Ltd.  All rights reserved.

import os
import grp
import pwd
import sys
import errno
import subprocess

from canonical.config import config
from canonical.launchpad.mailman.monkeypatches import monkey_patch
from configs import generate_overrides

basepath = filter(None, sys.path)


def build_mailman():
    # Build and install Mailman if it is enabled and not yet built.
    mailman_path = config.mailman.build.prefix
    mailman_bin = os.path.join(mailman_path, 'bin')
    var_dir = os.path.abspath(config.mailman.build.var_dir)

    # If we can import the package, we assume Mailman is properly built and
    # installed.  This does not catch re-installs that might be necessary
    # should our copy in sourcecode be updated.  Do that manually.
    sys.path.append(mailman_path)
    try:
        import Mailman
    except ImportError:
        pass
    else:
        return 0

    if not config.mailman.build.build:
        # There's nothing to do.
        return 0

    # Make sure the target directories exist and have the correct
    # permissions, otherwise configure will complain.
    user, group = config.mailman.build.user_group
    # Now work backwards to get the uid and gid
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid

    # Ensure that the var_dir exists, is owned by the user:group, and has
    # the necessary permissions.  Set the mode separately after the
    # makedirs() call because some platforms ignore mkdir()'s mode (though
    # I think Linux does not ignore it -- better safe than sorry).
    try:
        os.makedirs(var_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    os.chown(var_dir, uid, gid)
    os.chmod(var_dir, 02775)

    mailman_source = os.path.join('sourcecode', 'mailman')

    # Build and install the Mailman software.  Note that we don't care
    # about --with-mail-gid or --with-cgi-gid because we're not going to
    # use those Mailman subsystems.
    configure_args = (
        './configure',
        '--prefix', mailman_path,
        '--with-var-prefix=' + var_dir,
        '--with-python=' + sys.executable,
        '--with-username=' + user,
        '--with-groupname=' + group,
        '--with-mailhost=' + config.mailman.build.host_name,
        )
    retcode = subprocess.call(configure_args, cwd=mailman_source)
    if retcode:
        print >> sys.stderr, 'Could not configure Mailman:'
        sys.exit(retcode)
    retcode = subprocess.call(('make',), cwd=mailman_source)
    if retcode:
        print >> sys.stderr, 'Could not make Mailman.'
        sys.exit(retcode)
    retcode = subprocess.call(('make', 'install'), cwd=mailman_source)
    if retcode:
        print >> sys.stderr, 'Could not install Mailman.'
        sys.exit(retcode)
    # Try again to import the package.
    try:
        import Mailman
    except ImportError:
        print >> sys.stderr, 'Could not import the Mailman package'
        return 1

    # Check to see if the site list exists.  The output can go to /dev/null
    # because we don't really care about it.  The site list exists if
    # config_list returns a zero exit status, otherwise it doesn't
    # (probably).  Before we can do this however, we must monkey patch
    # Mailman, otherwise mm_cfg.py won't be set up correctly.
    monkey_patch(mailman_path, config)

    import Mailman.mm_cfg
    retcode = subprocess.call(
        ('./config_list', '-o', '/dev/null',
         Mailman.mm_cfg.MAILMAN_SITE_LIST),
        cwd=mailman_bin,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if retcode:
        addr, password = config.mailman.build.site_list_owner

        # The site list does not yet exist, so create it now.
        retcode = subprocess.call(
            ('./newlist', '--quiet',
             '--emailhost=' + config.mailman.build.host_name,
             Mailman.mm_cfg.MAILMAN_SITE_LIST,
             addr, password),
            cwd=mailman_bin)
        if retcode:
            print >> sys.stderr, 'Could not create site list'
            return retcode

    # Create a directory to hold the gzip'd tarballs for the directories of
    # deactivated lists.
    try:
        os.mkdir(os.path.join(Mailman.mm_cfg.VAR_PREFIX, 'backups'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

    return 0


def main():
    # Sort ZCML overrides for our current config
    generate_overrides()

    # setting python paths
    program = sys.argv[0]

    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.join(here, src)
    sys.path = [srcdir, here] + basepath
    return build_mailman()



if __name__ == '__main__':
    return_code = main()
    sys.exit(return_code)
