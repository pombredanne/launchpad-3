# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database constants."""

from sqlobject.sqlbuilder import SQLConstant

UTC_NOW = SQLConstant("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")

DEFAULT = SQLConstant("DEFAULT")

# We can't use infinity, as psycopg doesn't know how to handle it. And
# neither does Python I guess.
#NEVER_EXPIRES = SQLConstant("'infinity'::TIMESTAMP")

NEVER_EXPIRES = SQLConstant("'3000-01-01'::TIMESTAMP WITHOUT TIME ZONE")

