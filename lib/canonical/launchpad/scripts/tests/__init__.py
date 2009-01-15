# Copyright Canonical Ltd
# Author: Carlos Perello Marin <carlos.perello@canonical.com>
#         David Allouche <david.allouche@canonical.com>

# Make this a package.

# Note: by adding one's name to the copyright section, one is arguably making
# a substantial modification.


import os.path
import subprocess

from canonical.config import config


def run_script(script_relpath, args, expect_returncode=0):
    script = os.path.join(config.root, script_relpath)
    args = [script] + args
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != expect_returncode:
        raise AssertionError('Failed:\n%s' % stderr)
    return (process.returncode, stdout, stderr)
