# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from subprocess import Popen, PIPE, STDOUT
from canonical.launchpad.scripts import log

def call(cmd):
    """Run a command, raising a RuntimeError if the command failed"""
    log.debug("Running %s" % cmd)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    (out, err) = p.communicate()
    for line in out.splitlines():
        log.debug("> %s" % line)
    if p.returncode != 0:
        msg = "Error %d running %s" % (p.returncode, cmd)
        log.error(msg)
        raise RuntimeError(msg)
    return p.returncode
