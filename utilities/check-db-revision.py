#!/usr/bin/python -S
# Copyright 2010 Canonical Ltd.  All rights reserved.

"""
Check that the database revision of the current branch matches the current
database schema number.
"""

import _pythonpath
import sys

from canonical.database.revision import (
    confirm_dbrevision_on_startup, InvalidDatabaseRevision)

try:
    confirm_dbrevision_on_startup()
except InvalidDatabaseRevision, err:
    print "Oops, we are trying to use an invalid database revision!"
    print err
    sys.exit(1)
else:
    sys.exit(0)
