#! /usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Check that all the launchpad scripts and cronscripts run.

Usage hint:

% utilities/check-scripts.py
"""
import os
import subprocess
import sys


script_locations = [
    'cronscripts',
    'scripts',
    ]


KNOWN_BROKEN = [
    # Needs mysqldb module
    './scripts/bugzilla-import.py',
    './scripts/migrate-bugzilla-initialcontacts.py',
    # circular import from hell (IHasOwner).
    './scripts/clean-sourceforge-project-entries.py',
    './scripts/import-zope-specs.py',
    # sqlobject.DatbaseIndex ?
    './scripts/linkreport.py',
    # Python executable without '.py' extension.
    './scripts/list-team-members',
    './scripts/queue',
    # Bad script, no help.
    './scripts/librarian-report.py',
    './scripts/rosetta/message-sharing-populate-test.py',
    ]


def check_script(script_path):
    """Run the given script in a subprocess and report its result.

    Check if the script successfully runs if 'help' is requested via
    command line argument ('-h').
    """
    sys.stdout.write('Checking: %s ' % script_path)
    sys.stdout.flush()
    args = [sys.executable, script_path, "-h"]
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != os.EX_OK:
        sys.stdout.write('... FAILED\n')
        sys.stdout.write('%s\n' % stderr)
    else:
        sys.stdout.write('... OK\n')
    sys.stdout.flush()


def should_skip(script_path):
    """Return True if the given script path should not be run.

    Skips filename starting with '_' or not ending with '.py' or
    listed in the KNOWN_BROKEN blacklist.
    """
    filename = os.path.basename(script_path)
    return (filename.startswith('_') or
            not filename.endswith('.py') or
            script_path in KNOWN_BROKEN)


def main():
    """Walk over the specified script locations and check them."""
    lp_tree = os.path.normpath(
        os.path.join(os.path.dirname(__file__), os.pardir))
    for script_location in script_locations:
        location = os.path.join(lp_tree, script_location)
        for path, dirs, filenames in os.walk(location):
            for filename in sorted(filenames):
                script_path = os.path.join(path, filename)
                if should_skip(script_path):
                    continue
                check_script(script_path)


if __name__ == '__main__':
    sys.exit(main())
