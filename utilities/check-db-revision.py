#!/usr/bin/python2.5 -S
# Copyright 2010 Canonical Ltd.  All rights reserved.

"""
Check that the database revision of the current branch matches the current
database schema number.
"""

import canonical.database.revision

canonical.database.revision.confirm_dbrevision_on_startup()