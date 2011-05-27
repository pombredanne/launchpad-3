# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'IPersonProduct',
    'IPersonProductFactory',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    TextLine,
)

from lp.code.interfaces.hasbranches import IHasMergeProposals
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct


class IPersonProduct(IHasMergeProposals):
    """A person's view on a product."""

    person = Reference(IPerson)

    product = Reference(IProduct)

    displayname = TextLine()


class IPersonProductFactory(Interface):
    """Creates `IPersonProduct`s."""

    def create(person, product):
        """Create and return an `IPersonProduct`."""
