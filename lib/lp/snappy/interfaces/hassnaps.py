# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface definitions for IHasSnaps."""

__metaclass__ = type
__all__ = [
    'IHasSnaps',
    ]

from zope.interface import Interface


class IHasSnaps(Interface):
    """An object that has snap packages."""

    # For internal convenience and intentionally not exported.
    # XXX cjwatson 2015-09-16: Export something suitable on ISnapSet.
    def getSnaps(eager_load=False, order_by_date=True):
        """Return all snap packages associated with the object."""
