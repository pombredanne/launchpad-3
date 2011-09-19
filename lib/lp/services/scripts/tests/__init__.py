# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'find_lp_scripts',
    ]


import os

import canonical


LP_TREE = os.path.dirname(
    os.path.dirname(os.path.dirname(canonical.__file__)))


SCRIPT_LOCATIONS = [
    'cronscripts',
    'scripts',
    ]


KNOWN_BROKEN = [
    # Needs mysqldb module
    'scripts/migrate-bugzilla-initialcontacts.py',
    'scripts/rosetta/gettext_check_messages.py',
    # sqlobject.DatbaseIndex ?
    'scripts/linkreport.py',
    # Python executable without '.py' extension.
    'scripts/list-team-members',
    'scripts/queue',
    # Bad script, no help.
    'scripts/librarian-report.py',
    'scripts/get-stacked-on-branches.py',
    'scripts/start-loggerhead.py',
    'scripts/stop-loggerhead.py',
    ]


def is_broken(script_path):
    for broken_path in KNOWN_BROKEN:
        if script_path.endswith(broken_path):
            return True
    return False


def find_lp_scripts():
    """Find all scripts/ and cronscripts/ files in the current tree.

    Skips filename starting with '_' or not ending with '.py' or
    listed in the KNOWN_BROKEN blacklist.
    """
    scripts = []
    for script_location in SCRIPT_LOCATIONS:
        location = os.path.join(LP_TREE, script_location)
        for path, dirs, filenames in os.walk(location):
            for filename in filenames:
                script_path = os.path.join(path, filename)
                if (filename.startswith('_') or
                    not filename.endswith('.py') or
                    is_broken(script_path)):
                    continue
                scripts.append(script_path)
    return sorted(scripts)
