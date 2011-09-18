# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This module provides the Zopeless PG environment.

This module is deprecated.
"""

# This module uses a different naming convention to support the callsites.
# pylint: disable-msg=C0103

__metaclass__ = type

from canonical.database.sqlbase import ZopelessTransactionManager

__all__ = ['isZopeless']


def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    # pylint: disable-msg=W0212
    return ZopelessTransactionManager._installed is not None
