# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Temporary shim for fti.py.

__all__ = [
    'ConnectionString',
    ]

from lp.services.database.postgresql import ConnectionString
