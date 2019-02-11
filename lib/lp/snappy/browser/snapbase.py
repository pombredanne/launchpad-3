# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views of bases for snaps."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "SnapBaseSetNavigation",
    ]

from lp.services.webapp import GetitemNavigation
from lp.snappy.interfaces.snapbase import ISnapBaseSet


class SnapBaseSetNavigation(GetitemNavigation):
    """Navigation methods for `ISnapBaseSet`."""
    usedfor = ISnapBaseSet
