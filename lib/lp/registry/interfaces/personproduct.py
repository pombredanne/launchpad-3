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

