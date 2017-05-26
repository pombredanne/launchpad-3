# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'IPersonProduct',
    'IPersonProductFactory',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import TextLine

from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.code.interfaces.hasbranches import (
    IHasBranches,
    IHasMergeProposals,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct


class IPersonProduct(IHasMergeProposals, IHasBranches, IPrivacy,
                     IInformationType):
    """A person's view on a product."""

    person = Reference(IPerson)
    product = Reference(IProduct)
    displayname = TextLine()


class IPersonProductFactory(Interface):
    """Creates `IPersonProduct`s."""

    def create(person, product):
        """Create and return an `IPersonProduct`."""
