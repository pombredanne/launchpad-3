# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a temporary shim to support database/schema/fti.py in devel.

__all__ = [
    'db_options',
    'logger',
    'logger_options',
    ]

from lp.services.scripts import (
    db_options,
    logger,
    logger_options,
    )
