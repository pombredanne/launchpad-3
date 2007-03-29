#! /usr/bin/python2.4
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Start script for Launchpad: loads configuration and starts the server.

$Id: z3.py 25266 2004-06-04 21:25:45Z jim $
"""
import sys

if sys.version_info < (2, 4, 0):
    print ("ERROR: Your python version is not supported by Launchpad."
            "Launchpad needs Python 2.4 or greater. You are running: " 
            + sys.version)
    sys.exit(1)

import os
import grp
import pwd
import time
import errno
import atexit
import random
import signal
import socket
import subprocess

from configs import generate_overrides
from string import ascii_letters, digits
from zope.app.server.main import main

basepath = filter(None, sys.path)

# Disgusting hack to use our extended config file schema rather than the
# Z3 one. TODO: Add command line options or other to Z3 to enable overriding
# this -- StuartBishop 20050406
from zdaemon.zdoptions import ZDOptions
ZDOptions.schemafile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'lib', 'canonical',
        'config', 'schema.xml'))

twistd_script = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'sourcecode', 'twisted', 'bin', 'twistd'))

def start_librarian():
    # Imported here as path is not set fully on module load
    from canonical.config import config
    from canonical.pidfile import make_pidfile, pidfile_path

    # Don't run the Librarian if it wasn't asked for. We only want it
    # started up developer boxes really, as the production Librarian
    # doesn't use this startup script.
    if not config.librarian.server.launch:
        return

    if not os.path.isdir(config.librarian.server.root):
        os.makedirs(config.librarian.server.root, 0700)

    pidfile = pidfile_path('librarian')
    logfile = config.librarian.server.logfile
    tacfile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'daemons', 'librarian.tac'
        ))

    args = [
        sys.executable,
        twistd_script,
        "--no_save",
        "--nodaemon",
        "--python", tacfile,
        "--pidfile", pidfile,
        "--prefix", "Librarian",
        "--logfile", logfile,
        ]

    if config.librarian.server.spew:
        args.append("--spew")

    # Note that startup tracebacks and evil programmers using 'print'
    # will cause output to our stdout. However, we don't want to have
    # twisted log to stdout and redirect it ourselves because we then
    # lose the ability to cycle the log files by sending a signal to the
    # twisted process.
    librarian_process = subprocess.Popen(args, stdin=subprocess.PIPE)
    librarian_process.stdin.close()
    # I've left this off - we still check at termination and we can
    # avoid the startup delay. -- StuartBishop 20050525
    #time.sleep(1)
    #if librarian_process.poll() != None:
    #    raise RuntimeError(
    #            "Librarian did not start: %d" % librarian_process.returncode
    #            )
    def stop_librarian():
        if librarian_process.poll() is None:
            os.kill(librarian_process.pid, signal.SIGTERM)
            librarian_process.wait()
    atexit.register(stop_librarian)


def start_mailman():
    # Build and install Mailman if it is enabled and not yet built.
    from canonical.config import config

    mailman_path = os.path.abspath(config.mailman.build.prefix)
    mailman_bin  = os.path.join(mailman_path, 'bin')
    var_dir      = os.path.abspath(config.mailman.build.var_dir)

    # If we can import the package, we assume Mailman is properly built and
    # installed.  This does not catch re-installs that might be necessary
    # should our copy in sourcecode be updated.  Do that manually.
    sys.path.append(mailman_path)
    try:
        import Mailman
    except ImportError:
        Mailman = None

    if Mailman is None and config.mailman.build.build:
        # Make sure the target directories exist and have the correct
        # permissions, otherwise configure will complain.
        user_group = config.mailman.build.user_group
        if not user_group:
            user  = pwd.getpwuid(os.getuid()).pw_name
            group = grp.getgrgid(os.getgid()).gr_name
        else:
            user, group = user_group.split(':', 1)

        # Now work backwards to get the uid and gid
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid

        # Ensure that the var_dir exists, is owned by the user:group, and has
        # the necessary permissions.  Set the mode separately after the
        # makedirs() call because some platforms ignore mkdir()'s mode (though
        # I think Linux does not ignore it -- better safe than sorry).
        try:
            os.makedirs(config.mailman.build.var_dir)
        except OSError, e:
            if e.errno <> errno.EEXIST:
                raise
        os.chown(config.mailman.build.var_dir, uid, gid)
        os.chmod(config.mailman.build.var_dir, 02775)

        if config.mailman.build.host_name:
            hostname = config.mailman.build.host_name
        else:
            hostname = socket.getfqdn()

        mailman_source = os.path.join('sourcecode', 'mailman')

        # Build and install the Mailman software.  Note that we don't care
        # about --with-mail-gid or --with-cgi-gid because we're not going to
        # use those Mailman subsystems.
        configure_args = (
            './configure',
            '--prefix', mailman_path,
            '--with-var-prefix=' + config.mailman.build.var_dir,
            '--with-python=' + sys.executable,
            '--with-username=' + user,
            '--with-groupname=' + group,
            '--with-mailhost=' + hostname,
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
            sys.exit(1)

    if not config.mailman.launch:
        return

    # Monkey-patch the installed Mailman 2.1 tree.
    from canonical.mailman.monkeypatches import monkey_patch
    monkey_patch(mailman_path, config)

    # Ensure that the site list has been created.  We won't use this
    # operationally, but it's required by Mailman 2.1.  This is the cheapest
    # way to do this.  Throw away the actual output, since we only care about
    # the return code.
    import Mailman.mm_cfg
    retcode = subprocess.call(('./config_list', '-o', '/dev/null',
                               Mailman.mm_cfg.MAILMAN_SITE_LIST),
                              cwd=mailman_bin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if retcode:
        if config.mailman.build.site_list_owner:
            addr, password = config.mailman.build.site_list_owner.split(':', 1)
        else:
            chars = digits + ascii_letters
            localpart = ''.join([random.choice(chars) for count in range(10)])
            addr = localpart + '@example.com'
            password = ''.join([random.choice(chars) for count in range(10)])

        # The site list does not yet exist, so create it now.
        retcode = subprocess.call(('./newlist', '--quiet',
                                   '--emailhost=' + hostname,
                                   Mailman.mm_cfg.MAILMAN_SITE_LIST,
                                   addr, password),
                                  cwd=mailman_bin)
        if retcode:
            print >> sys.stderr, 'Could not create site list'
            sys.exit(retcode)

    # Start the Mailman master qrunner.  If that succeeds, then set things up
    # so that it will be stopped when runlaunchpad.py exits.
    def stop_mailman():
        # Ignore any errors
        retcode = subprocess.call(('./mailmanctl', 'stop'), cwd=mailman_bin)
        if retcode:
            print >> sys.stderr, 'mailmanctl did not stop cleanly:', retcode
            # There's no point in calling sys.exit() since we're already
            # exiting!

    retcode = subprocess.call(('./mailmanctl', 'start'), cwd=mailman_bin)
    if retcode:
        print >> sys.stderr, 'mailmanctl did not start cleanly'
        sys.exit(retcode)
    atexit.register(stop_mailman)


def start_buildsequencer():
    # Imported here as path is not set fully on module load
    from canonical.config import config
    from canonical.pidfile import make_pidfile, pidfile_path

    # Don't run the sequencer if it wasn't asked for. We only want it
    # started up developer boxes and dogfood really, as the production
    # sequencer doesn't use this startup script.
    
    if not config.buildsequencer.launch:
        return

    pidfile = pidfile_path('buildsequencer')
    logfile = config.buildsequencer.logfile
    tacfile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'daemons', 'buildd-sequencer.tac'
        ))

    args = [
        sys.executable,
        twistd_script,
        "--no_save",
        "--nodaemon",
        "--python", tacfile,
        "--pidfile", pidfile,
        "--prefix", "Librarian",
        "--logfile", logfile,
        ]

    if config.buildsequencer.spew:
        args.append("--spew")

    # Note that startup tracebacks and evil programmers using 'print'
    # will cause output to our stdout. However, we don't want to have
    # twisted log to stdout and redirect it ourselves because we then
    # lose the ability to cycle the log files by sending a signal to the
    # twisted process.
    sequencer_process = subprocess.Popen(args, stdin=subprocess.PIPE)
    sequencer_process.stdin.close()
    # I've left this off - we still check at termination and we can
    # avoid the startup delay. -- StuartBishop 20050525
    #time.sleep(1)
    #if sequencer_process.poll() != None:
    #    raise RuntimeError(
    #            "Sequencer did not start: %d" % sequencer_process.returncode
    #            )
    def stop_sequencer():
        if sequencer_process.poll() is None:
            os.kill(sequencer_process.pid, signal.SIGTERM)
            sequencer_process.wait()
    atexit.register(stop_sequencer)


def run(argv=list(sys.argv)):

    # Sort ZCML overrides for our current config
    generate_overrides()

    # setting python paths
    program = argv[0]

    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.join(here, src)
    sys.path = [srcdir, here] + basepath

    # Import canonical modules here, after path munging
    from canonical.pidfile import make_pidfile, pidfile_path

    # We really want to replace this with a generic startup harness.
    # However, this should last us until this is developed
    start_librarian()
    start_buildsequencer()
    start_mailman()

    # Store our process id somewhere
    make_pidfile('launchpad')

    main(argv[1:])
        

if __name__ == '__main__':
    run()
