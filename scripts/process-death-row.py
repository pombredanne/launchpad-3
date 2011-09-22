#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Stop lint warning about relative import:
# pylint: disable-msg=W0403
"""Death row processor script.

This script removes obsolete files from the selected archive(s) pool.

You can select a specific distribution or let it default to 'ubuntu'.

It operates in 2 modes:
 * all distribution archive (PRIMARY and PARTNER) [default]
 * all PPAs [--ppa]

You can optionally specify a different 'pool-root' path which will be used
as the base path for removing files, instead of the real archive pool root.
This feature is used to inspect the removed files without actually modifying
the archive tree.

There is also a 'dry-run' mode that can be used to operate on the real
archive tree without removing the files.
"""
import _pythonpath

# This is needed to prevent circular imports until we get rid of the
# abomination that is known as
# canonical/launchpad/interfaces/__init.py__ that imports the whole
# freaking world.
import canonical.launchpad.interfaces

from lp.soyuz.scripts.processdeathrow import DeathRowProcessor


if __name__ == "__main__":
    script = DeathRowProcessor(
        'process-death-row', dbuser='process_death_row')
    script.lock_and_run()
