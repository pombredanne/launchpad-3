#!/usr/bin/env python
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Script to check the size of the generated javascript.

This script tests to ensure optimized javascript never gets over a certain
size.  If it gets too big, Windmill has issues. This is a hack until we can
find out why Windmill has such issues.
"""

import os


FILE_NAME = 'lib/canonical/launchpad/icing/build/launchpad.js'
MAX_FILE_SIZE = 512 * 1024

def main():
    size = os.path.getsize(FILE_NAME)
    if size > MAX_FILE_SIZE:
        raise Exception(
            'launchpad.js is greater than %d bytes' % MAX_FILE_SIZE)
