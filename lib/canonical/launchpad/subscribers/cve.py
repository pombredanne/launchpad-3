# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.database.constants import UTC_NOW

def cve_modified(cve, object_modified_event):
    cve.datemodified = UTC_NOW

