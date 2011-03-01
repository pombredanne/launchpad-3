#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a control file of file that should be migrated."""

import sys

from find import find_files
from migrater import OLD_TOP


TLA_COMMON_MAP = dict(
    ans=[],
    app=[],
    blu=['blueprint', 'specification', 'sprint', 'specgraph'],
    bug=[],
    cod=[],
    reg=[],
    sha=[],
    soy=[],
    svc=[],
    tes=[],
    tra=[],
    )


def main(argv=None):
    """Run the command line operations."""
    skip_dir_pattern = r'^[.]|templates|icing'
    for file_path in find_files(OLD_TOP, skip_dir_pattern=skip_dir_pattern ):
        file_path = file_path.replace(OLD_TOP, '.')
        code = '   '
        for app_code in TLA_COMMON_MAP:
            for common_name in TLA_COMMON_MAP[app_code]:
                if common_name in file_path:
                    code = app_code
                    break
        print '%s %s' % (code, file_path)


if __name__ == '__main__':
    sys.exit(main())
