#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Run meld(1) on a launchpad branch against the most recent patchlevel of
rocketfuel it has been merged with.
"""

__metaclass__ = type

import _pythonpath

import sys, shutil, os.path, atexit, re
from tempfile import mkdtemp
from optparse import OptionParser
from glob import glob
from subprocess import Popen, PIPE

from canonical.launchpad.scripts import logger_options, logger

log = None # Global logger

def call(cmd):
    global log
    log.info("Running %s" % ' '.join(cmd))
    p = Popen(
            cmd, stdin=PIPE,
            #stdout=PIPE, stderr=PIPE
            )
    (out, err) = p.communicate()
    if p.returncode != 0:
        log.error("Error (%d) running %s" % (p.returncode, cmd))
        #log.info(err)
        #log.debug(out)
        sys.exit(p.returncode)


def baz_get(version, dest):
    """Retrieve a version from baz storing it in a directory dest"""
    call(['baz', 'get', '--link', '--no-pristine', version, dest])


def main(version):
    global log
    
    # Setup our temporary working directory.
    root = mkdtemp(prefix='meld.')
    def nuke_root():
        shutil.rmtree(root, ignore_errors=True)
        log.debug("Removed %s", root)
    atexit.register(nuke_root)
    log.debug("Temporary work directory is %s" % root)

    # Directories where we unpack rocketfuel (trunk) and our version.
    trunk_dir = os.path.join(root, 'trunk')
    changed_dir = os.path.join(root, 'changed')

    # Pull our version.
    baz_get(version, changed_dir)

    # Work out the most recent revision of rocketfuel that has been merged
    # into this version.
    cmd = 'baz logs --dir %s rocketfuel@canonical.com/launchpad--devel--0' % (
            changed_dir,
            )
    p = Popen(cmd.split(), stdin=PIPE, stdout=PIPE)
    (out, err) = p.communicate()
    rocketfuel_version = out.splitlines()[-1]
    assert re.search('^patch-\d+$', rocketfuel_version) is not None
    rocketfuel_version = 'rocketfuel@canonical.com/launchpad--devel--0--%s' % (
            rocketfuel_version,
            )

    # Pull in the rocketfuel version.
    baz_get(rocketfuel_version, trunk_dir)

    # Trash noise that slows meld.
    noise_dirnames = ['{arch}', '.arch-ids', '.arch-inventory']
    for top_dir in [trunk_dir, changed_dir]:
        for root, dirs, files in os.walk(top_dir):
            for noise_dirname in noise_dirnames:
                if noise_dirname in dirs:
                    path = os.path.join(root, noise_dirname)
                    log.debug("Removing %s" % path)
                    shutil.rmtree(path)
                    dirs.remove(noise_dirname)
                    
    # Run meld(1)
    call(['meld', trunk_dir, changed_dir])


if __name__ == "__main__":
    parser = OptionParser("Usage: %prog VERSION")
    logger_options(parser)
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("VERSION must be specified")

    log = logger()

    main(args[0])

