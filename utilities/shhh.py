#! /usr/bin/python -S
#
# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run a command and suppress output unless it returns a non-zero exit status.
"""

__metaclass__ = type

import os
from subprocess import (
    PIPE,
    Popen,
    )
import sys


def shhh(cmd):
    r"""Run a command and suppress output unless it returns a non-zero exitcode

    If output is generated, stderr will be output before stdout, so output
    order may be messed up if the command attempts to control order by
    flushing stdout at points or setting it to unbuffered.

    To test, we invoke both this method and this script with some commands
    and examine the output and exit status.

    >>> python = sys.executable

    >>> def shhh_script(cmd):
    ...     from subprocess import Popen, PIPE
    ...     cmd = [python, __file__] + cmd
    ...     p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    ...     (out, err) = p.communicate()
    ...     return (out, err, p.returncode)

    >>> cmd = [python, "-c", "import sys; sys.exit(0)"]
    >>> shhh(cmd)
    0
    >>> shhh_script(cmd)
    ('', '', 0)

    >>> cmd = [python, "-c", "import sys; sys.exit(1)"]
    >>> shhh(cmd)
    1
    >>> shhh_script(cmd)
    ('', '', 1)

    >>> cmd = [python, "-c", "import sys; print 666; sys.exit(42)"]
    >>> shhh(cmd)
    666
    42
    >>> shhh_script(cmd)
    ('666\n', '', 42)

    >>> cmd = [
    ...     python, "-c",
    ...     "import sys; print 666; print >> sys.stderr, 667; sys.exit(42)",
    ...     ]
    >>> shhh_script(cmd)
    ('666\n', '667\n', 42)

    >>> cmd = ["TEST=sentinel value=0", "sh", "-c", 'echo "$TEST"; exit 1']
    >>> shhh(cmd)
    sentinel value=0
    1
    >>> shhh_script(cmd)
    ('sentinel value=0\n', '', 1)
    """

    env = dict(os.environ)
    cmd = list(cmd)
    while cmd:
        if "=" in cmd[0]:
            name, value = cmd[0].split("=", 1)
            env[name] = value
            del cmd[0]
        else:
            break
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env)
    (out, err) = process.communicate()
    if process.returncode == 0:
        return 0
    else:
        sys.stderr.write(err)
        sys.stdout.write(out)
        return process.returncode


if __name__ == '__main__':
    sys.exit(shhh(sys.argv[1:]))
