# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies that contain branches."""


__metaclass__ = type

__all__ = [
    'BranchRestrictedOnProductVocabulary',
    'BranchVocabulary',
    'HostedBranchRestrictedOnOwnerVocabulary',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )

from lp.code.enums import BranchType
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.model.branch import Branch
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries


class BranchVocabularyBase(SQLObjectVocabularyBase):
    """A base class for Branch vocabularies.

    Override `BranchVocabularyBase._getCollection` to provide the collection
    of branches which make up the vocabulary.
    """

    implements(IHugeVocabulary)

    _table = Branch
    _orderBy = ['name', 'id']
    displayname = 'Select a branch'
    step_title = 'Search'

    def toTerm(self, branch):
        """The display should include the URL if there is one."""
        return SimpleTerm(branch, branch.unique_name, branch.unique_name)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        search_results = self.searchForTerms(token)
        if search_results.count() == 1:
            return iter(search_results).next()
        raise LookupError(token)

    def _getCollection(self):
        """Return the collection of branches the vocabulary searches.

        Subclasses MUST override and implement this.
        """
        raise NotImplementedError(self._getCollection)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        logged_in_user = getUtility(ILaunchBag).user
        collection = self._getCollection().visibleByUser(logged_in_user)
        if query is None:
            branches = collection.getBranches(eager_load=False)
        else:
            branches = collection.search(query)
        return CountableIterator(branches.count(), branches, self.toTerm)

    def __len__(self):
        """See `IVocabulary`."""
        return self.search().count()


class BranchVocabulary(BranchVocabularyBase):
    """A vocabulary for searching branches.

    The name and URL of the branch, the name of the product, and the
    name of the registrant of the branches is checked for the entered
    value.
    """

    def _getCollection(self):
        return getUtility(IAllBranches)


class BranchRestrictedOnProductVocabulary(BranchVocabularyBase):
    """A vocabulary for searching branches restricted on product.

    The query entered checks the name or URL of the branch, or the
    name of the registrant of the branch.
    """

    def __init__(self, context=None):
        BranchVocabularyBase.__init__(self, context)
        if IProduct.providedBy(self.context):
            self.product = self.context
        elif IProductSeries.providedBy(self.context):
            self.product = self.context.product
        elif IBranch.providedBy(self.context):
            self.product = self.context.product
        else:
            # An unexpected type.
            raise AssertionError('Unexpected context type')

    def _getCollection(self):
        return getUtility(IAllBranches).inProduct(self.product)


class HostedBranchRestrictedOnOwnerVocabulary(BranchVocabularyBase):
    """A vocabulary for hosted branches owned by the current user.

    These are branches that the user either owns themselves or which are
    owned by a team of which the person is a member.
    """

    def __init__(self, context=None):
        """Pass a Person as context, or anything else for the current user."""
        super(HostedBranchRestrictedOnOwnerVocabulary, self).__init__(context)
        if IPerson.providedBy(self.context):
            self.user = context
        else:
            self.user = getUtility(ILaunchBag).user

    def _getCollection(self):
        owned_branches = getUtility(IAllBranches).ownedByTeamMember(self.user)
        return owned_branches.withBranchType(BranchType.HOSTED)
