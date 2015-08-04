# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface definitions for IHasSnaps."""

__metaclass__ = type
__all__ = [
    'IHasSnaps',
    ]


from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import exported
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface

from lp import _


class IHasSnaps(Interface):
    """An object that has snap packages."""

    snaps = exported(doNotSnapshot(
        CollectionField(
            title=_("All snap packages associated with the object."),
            # Really ISnap.
            value_type=Reference(schema=Interface),
            readonly=True)))
