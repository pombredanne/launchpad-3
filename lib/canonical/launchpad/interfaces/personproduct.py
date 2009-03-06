# Copyright 2009 Canonical Ltd.  All rights reserved.

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'IPersonProduct',
    ]

from zope.interface import Interface

from canonical.lazr.fields import Reference

from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.product import IProduct


class IPersonProduct(Interface):
    """A person's view on a product."""

    person = Reference(IPerson)

    product = Reference(IProduct)


class IPersonProductFactory(Interface):
    """Creates `IPersonProduct`s."""

    def create(person, product):
        """Create and return an `IPersonProduct`."""

