# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database constants."""

from storm.expr import SQL

UTC_NOW = SQL("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")

DEFAULT = SQL("DEFAULT")

# We can't use infinity, as psycopg doesn't know how to handle it. And
# neither does Python I guess.
#NEVER_EXPIRES = SQL("'infinity'::TIMESTAMP")

NEVER_EXPIRES = SQL("'3000-01-01'::TIMESTAMP WITHOUT TIME ZONE")

