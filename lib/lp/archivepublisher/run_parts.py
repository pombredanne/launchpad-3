# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Publisher support for running programs from a plug-in directory."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'execute_subprocess',
    'find_run_parts_dir',
    'run_parts',
    ]

import os
try:
    from shlex import quote as shell_quote
except ImportError:
    from pipes import quote as shell_quote
import subprocess

from lp.services.config import config
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists


def find_run_parts_dir(distribution_name, parts):
    """Find the requested run-parts directory, if it exists."""
    run_parts_location = config.archivepublisher.run_parts_location
    if not run_parts_location:
        return None

    parts_dir = os.path.join(run_parts_location, distribution_name, parts)
    if file_exists(parts_dir):
        return parts_dir
    else:
        return None


def execute_subprocess(args, log=None, failure=None, **kwargs):
    """Run `args`, handling logging and failures.

    :param args: Program argument array.
    :param log: An optional logger.
    :param failure: Raise `failure` as an exception if the command returns a
        nonzero value.  If omitted, nonzero return values are ignored.
    :param kwargs: Other keyword arguments passed on to `subprocess.call`.
    """
    if log is not None:
        log.debug("Executing: %s", " ".join(shell_quote(arg) for arg in args))
    retval = subprocess.call(args, **kwargs)
    if retval != 0:
        if log is not None:
            log.debug("Command returned %d.", retval)
        if failure is not None:
            if log is not None:
                log.debug("Command failed: %s", failure)
            raise failure


def run_parts(distribution_name, parts, log=None, env=None):
    """Execute run-parts.

    :param distribution_name: The name of the distribution to execute
        run-parts scripts for.
    :param parts: The run-parts directory to execute:
        "publish-distro.d" or "finalize.d".
    :param log: An optional logger.
    :param env: A dict of additional environment variables to pass to the
        scripts in the run-parts directory, or None.
    """
    parts_dir = find_run_parts_dir(distribution_name, parts)
    if parts_dir is None:
        if log is not None:
            log.debug("Skipping run-parts %s: not configured.", parts)
        return
    cmd = ["run-parts", "--", parts_dir]
    failure = LaunchpadScriptFailure(
        "Failure while executing run-parts %s." % parts_dir)
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    scripts_dir = os.path.join(config.root, "cronscripts", "publishing")
    path_elements = full_env.get("PATH", "").split(os.pathsep)
    path_elements.append(scripts_dir)
    full_env["PATH"] = os.pathsep.join(path_elements)
    execute_subprocess(cmd, log=None, failure=failure, env=full_env)
