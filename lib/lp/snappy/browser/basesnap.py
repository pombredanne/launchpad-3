# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base snap views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "BaseSnapSetNavigation",
    ]

from lp.services.webapp import GetitemNavigation
from lp.snappy.interfaces.basesnap import IBaseSnapSet


class BaseSnapSetNavigation(GetitemNavigation):
    """Navigation methods for `IBaseSnapSet`."""
    usedfor = IBaseSnapSet
