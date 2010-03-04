# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Common implementations for a series."""

__metaclass__ = type

from zope.interface import implements

from lp.registry.interfaces.distroseries import ISeriesMixin
from lp.registry.interfaces.series import SeriesStatus


class SeriesMixin:
    """See `ISeriesMixin`."""
    implements(ISeriesMixin)

    @property
    def active(self):
        return self.status in [
            SeriesStatus.DEVELOPMENT,
            SeriesStatus.FROZEN,
            SeriesStatus.CURRENT,
            SeriesStatus.SUPPORTED,
            ]
