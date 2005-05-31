# Copyright 2004 Canonical Ltd
#

from sqlobject.sqlbuilder import SQLConstant

nowUTC = SQLConstant("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
UTC_NOW = nowUTC # All upper because this is the constants module

DEFAULT = SQLConstant("DEFAULT")

