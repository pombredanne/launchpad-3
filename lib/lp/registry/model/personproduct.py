# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A person's view on a product."""

__metaclass__ = type
__all__ = [
    'PersonProduct',
    ]

from zope.interface import (
    implementer,
    provider,
    )

from lp.code.model.hasbranches import HasMergeProposalsMixin
from lp.registry.interfaces.personproduct import (
    IPersonProduct,
    IPersonProductFactory,
    )


@implementer(IPersonProduct)
@provider(IPersonProductFactory)
class PersonProduct(HasMergeProposalsMixin):

    def __init__(self, person, product):
        self.person = person
        self.product = product

    @staticmethod
    def create(person, product):
        return PersonProduct(person, product)

    @property
    def displayname(self):
        return '%s in %s' % (
            self.person.displayname, self.product.displayname)

    def __eq__(self, other):
        return (
            IPersonProduct.providedBy(other) and
            self.person.id == other.person.id and
            self.product.id == other.product.id)

    def __ne__(self, other):
        return not self == other

    @property
    def private(self):
        return self.person.private or self.product.private
