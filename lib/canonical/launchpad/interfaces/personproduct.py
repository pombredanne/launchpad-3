# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'IPersonProduct',
    'IPersonProductFactory',
    ]

from zope.interface import Interface

from lazr.restful.fields import Reference

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct


class IPersonProduct(Interface):
    """A person's view on a product."""

    person = Reference(IPerson)

    product = Reference(IProduct)


class IPersonProductFactory(Interface):
    """Creates `IPersonProduct`s."""

    def create(person, product):
        """Create and return an `IPersonProduct`."""

