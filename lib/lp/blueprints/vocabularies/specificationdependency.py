# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The vocabularies relating to dependencies of specifications."""

__metaclass__ = type
__all__ = ['SpecificationDepCandidatesVocabulary']

from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from canonical.database.sqlbase import quote_like
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )

from lp.blueprints.interfaces.specification import SpecificationFilter
from lp.blueprints.model.specification import Specification


class SpecificationDepCandidatesVocabulary(SQLObjectVocabularyBase):
    """Specifications that could be dependencies of this spec.

    This includes only those specs that are not blocked by this spec
    (directly or indirectly), unless they are already dependencies.

    The current spec is not included.
    """

    implements(IHugeVocabulary)

    _table = Specification
    _orderBy = 'name'
    displayname = 'Select a blueprint'

    def _filter_specs(self, specs):
        # XXX intellectronica 2007-07-05: is 100 a reasonable count before
        # starting to warn?
        speclist = shortlist(specs, 100)
        return [spec for spec in speclist
                if (spec != self.context and
                    spec.target == self.context.target
                    and spec not in self.context.all_blocked)]

    def _doSearch(self, query):
        """Return terms where query is in the text of name
        or title, or matches the full text index.
        """

        if not query:
            return []

        quoted_query = quote_like(query)
        sql_query = ("""
            (Specification.name LIKE %s OR
             Specification.title LIKE %s OR
             fti @@ ftq(%s))
            """
            % (quoted_query, quoted_query, quoted_query))
        all_specs = Specification.select(sql_query, orderBy=self._orderBy)

        return self._filter_specs(all_specs)

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        search_results = self._doSearch(token)
        for search_result in search_results:
            if search_result.name == token:
                return self.toTerm(search_result)
        raise LookupError(token)

    def search(self, query):
        candidate_specs = self._doSearch(query)
        return CountableIterator(len(candidate_specs),
                                 candidate_specs)

    def _all_specs(self):
        all_specs = self.context.target.specifications(
            filter=[SpecificationFilter.ALL],
            prejoin_people=False)
        return self._filter_specs(all_specs)

    def __iter__(self):
        return (self.toTerm(spec) for spec in self._all_specs())

    def __contains__(self, obj):
        # We don't use self._all_specs here, since it will call
        # self._filter_specs(all_specs) which will cause all the specs
        # to be loaded, whereas obj in all_specs will query a single object.
        all_specs = self.context.target.specifications(
            filter=[SpecificationFilter.ALL],
            prejoin_people=False)
        return obj in all_specs and len(self._filter_specs([obj])) > 0
