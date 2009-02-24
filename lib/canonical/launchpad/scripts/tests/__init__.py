# Copyright Canonical Ltd
# Author: Carlos Perello Marin <carlos.perello@canonical.com>
#         David Allouche <david.allouche@canonical.com>

# Make this a package.

# Note: by adding one's name to the copyright section, one is arguably making
# a substantial modification.


import os.path
import subprocess

from canonical.config import config


def run_script(script_relpath, args, expect_returncode=0, env=None):
    """Run a script for testing purposes.

    :param script_relpath: The relative path to the script, from the tree
        root.
    :param args: Arguments to provide to the script.
    :param expect_returncode: The return code expected.  If a different value
        is returned, and exception will be raised.
    :param env: If supplied, the environment variables for the script.
    """
    script = os.path.join(config.root, script_relpath)
    args = [script] + args
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = process.communicate()
    if process.returncode != expect_returncode:
        raise AssertionError('Failed:\n%s' % stderr)
    return (process.returncode, stdout, stderr)
