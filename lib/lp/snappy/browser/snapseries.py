# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SnapSeries views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapSeriesNavigation',
    'SnapSeriesSetNavigation',
    ]

from lp.services.webapp import (
    GetitemNavigation,
    Navigation,
    )
from lp.snappy.interfaces.snapseries import (
    ISnapSeries,
    ISnapSeriesSet,
    )


class SnapSeriesSetNavigation(GetitemNavigation):
    """Navigation methods for `ISnapSeriesSet`."""
    usedfor = ISnapSeriesSet


class SnapSeriesNavigation(Navigation):
    """Navigation methods for `ISnapSeries`."""
    usedfor = ISnapSeries
