# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database constants."""

from sqlobject.sqlbuilder import SQLConstant

UTC_NOW = SQLConstant("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")

DEFAULT = SQLConstant("DEFAULT")

NEVER_EXPIRES = SQLConstant("'infinity'::TIMESTAMP WITHOUT TIMEZONE")

