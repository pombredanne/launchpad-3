# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SnappySeries views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnappySeriesNavigation',
    'SnappySeriesSetNavigation',
    ]

from lp.services.webapp import (
    GetitemNavigation,
    Navigation,
    )
from lp.snappy.interfaces.snappyseries import (
    ISnappySeries,
    ISnappySeriesSet,
    )


class SnappySeriesSetNavigation(GetitemNavigation):
    """Navigation methods for `ISnappySeriesSet`."""
    usedfor = ISnappySeriesSet


class SnappySeriesNavigation(Navigation):
    """Navigation methods for `ISnappySeries`."""
    usedfor = ISnappySeries
