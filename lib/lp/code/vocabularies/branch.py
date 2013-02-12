# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies that contain branches."""

__metaclass__ = type

__all__ = [
    'BranchRestrictedOnProductVocabulary',
    'BranchVocabulary',
    'HostedBranchRestrictedOnOwnerVocabulary',
    ]

from storm.locals import Join
from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from lp.code.enums import BranchType
from lp.code.interfaces.branch import IBranch
from lp.code.model.branch import Branch
from lp.code.model.branchcollection import search_branches
from lp.registry.enums import EXCLUSIVE_TEAM_POLICY
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.model.person import Person
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )


class BranchVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for searching branches."""

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

    def searchForTerms(self, query=None, vocab_filter=None, extra_joins=[],
                       extra_clauses=[]):
        """See `IHugeVocabulary`."""
        user = getUtility(ILaunchBag).user
        branches = search_branches(
            self.context, user, query, extra_joins=extra_joins,
            extra_clauses=extra_clauses)
        return CountableIterator(len(branches), branches, self.toTerm)

    def __len__(self):
        """See `IVocabulary`."""
        return self.search().count()


class BranchRestrictedOnProductVocabulary(BranchVocabulary):
    """A vocabulary for searching branches restricted on product."""

    def __init__(self, context=None):
        super(BranchRestrictedOnProductVocabulary, self).__init__(context)
        if IProduct.providedBy(self.context):
            self.context = context
        elif IProductSeries.providedBy(self.context):
            self.context = context.product
        elif IBranch.providedBy(self.context):
            self.context = context.product
        else:
            # An unexpected type.
            raise AssertionError('Unexpected context type')

    def searchForTerms(self, query=None, vocab_filter=None):
        extra_joins = [Join(Person, Person.id == Branch.ownerID)]
        extra_clauses = [
            Person.membership_policy.is_in(EXCLUSIVE_TEAM_POLICY)]
        return super(BranchRestrictedOnProductVocabulary, self).searchForTerms(
            query, vocab_filter, extra_joins=extra_joins,
            extra_clauses=extra_clauses)


class HostedBranchRestrictedOnOwnerVocabulary(BranchVocabulary):
    """A vocabulary for hosted branches owned by the current user.

    These are branches that the user either owns themselves or which are
    owned by a team of which the person is a member.
    """

    def __init__(self, context=None):
        """Pass a Person as context, or anything else for the current user."""
        super(HostedBranchRestrictedOnOwnerVocabulary, self).__init__(context)
        if not IPerson.providedBy(self.context):
            self.context = getUtility(ILaunchBag).user

    def searchForTerms(self, query=None, vocab_filter=None):
        extra_clauses = [Branch.branch_type == BranchType.HOSTED]
        return super(
            HostedBranchRestrictedOnOwnerVocabulary, self).searchForTerms(
                query, vocab_filter, extra_joins=[],
                extra_clauses=extra_clauses)
