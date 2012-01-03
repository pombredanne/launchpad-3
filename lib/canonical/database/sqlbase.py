# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Temporary shim for fti.py.

__all__ = [
    'connect',
    'ISOLATION_LEVEL_AUTOCOMMIT',
    'ISOLATION_LEVEL_READ_COMMITTED',
    'quote',
    'quote_identifier',
    ]

from lp.services.database.sqlbase import (
    connect,
    ISOLATION_LEVEL_AUTOCOMMIT,
    ISOLATION_LEVEL_READ_COMMITTED,
    quote,
    quote_identifier,
    )
