# Copyright 2009 Canonical Ltd.  All rights reserved.

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'PersonProduct',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.personproduct import IPersonProduct


class PersonProduct:

    implements(IPersonProduct)

    def __init__(self, person, product):
        self.person = person
        self.product = product

