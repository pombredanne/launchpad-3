# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os.path
import subprocess

from canonical.config import config


def run_script(script_relpath, args, expect_returncode=0):
    """Run a script for testing purposes.

    :param script_relpath: The relative path to the script, from the tree
        root.
    :param args: Arguments to provide to the script.
    :param expect_returncode: The return code expected.  If a different value
        is returned, and exception will be raised.
    """
    script = os.path.join(config.root, script_relpath)
    args = [script] + args
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != expect_returncode:
        raise AssertionError('Failed:\n%s\n%s' % (stdout, stderr))
    return (process.returncode, stdout, stderr)
