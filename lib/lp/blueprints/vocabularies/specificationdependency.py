# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The vocabularies relating to dependencies of specifications."""

__metaclass__ = type
__all__ = ['SpecificationDepCandidatesVocabulary']

from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from canonical.database.sqlbase import quote_like
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp import (
    canonical_url,
    urlparse,
    )
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )

from lp.blueprints.interfaces.specification import SpecificationFilter
from lp.blueprints.model.specification import Specification
from lp.registry.interfaces.pillar import IPillarNameSet

class SpecificationDepCandidatesVocabulary(SQLObjectVocabularyBase):
    """Specifications that could be dependencies of this spec.

    This includes only those specs that are not blocked by this spec (directly
    or indirectly), unless they are already dependencies.

    This vocabulary has a bit of a split personality.

    Tokens are *either*:

     - the name of a spec, in which case it must be a spec on the same target
       as the context, or
     - the full URL of the spec, in which case it can be any spec at all.

    For the purposes of enumeration and searching we only consider the first
    sort of spec for now.  The URL form of token only matches precisely,
    searching only looks for specs on the current target if the search term is
    not a URL.
    """

    implements(IHugeVocabulary)

    _table = Specification
    _orderBy = 'name'
    displayname = 'Select a blueprint'

    def _is_valid_candidate(self, spec, check_target=False):
        """Is `spec` a valid candidate spec for self.context?

        Invalid candidates are:

         * The spec that we're adding a depdency to,
         * Specs for a different target, and
         * Specs that depend on this one.

        Preventing the last category prevents loops in the dependency graph.
        """
        if check_target and spec.target != self.context.target:
            return False
        return spec != self.context and spec not in self.context.all_blocked

    def _filter_specs(self, specs, check_target=False):
        """Filter `specs` to remove invalid candidates.

        See `_is_valid_candidate` for what an invalid candidate is.
        """
        # XXX intellectronica 2007-07-05: is 100 a reasonable count before
        # starting to warn?
        return [spec for spec in shortlist(specs, 100)
                if self._is_valid_candidate(spec, check_target)]

    def toTerm(self, obj):
        # XXX obj.name needs to be different if target is different.
        return SimpleTerm(obj, obj.name, obj.title)

    def _spec_from_url(self, url):
        """XXX."""
        scheme, netloc, path, params, args, fragment = urlparse(url)
        if not scheme or not netloc:
            # Not enough like a URL
            return None
        path_segments = path.strip('/').split('/')
        if len(path_segments) != 3:
            # Can't be a spec url
            return None
        pillar_name, plus_spec, spec_name = path_segments
        if plus_spec != '+spec':
            # Can't be a spec url
            return None
        pillar = getUtility(IPillarNameSet).getByName(
            pillar_name, ignore_inactive=True)
        if pillar is None:
            return None
        return pillar.getSpecification(spec_name)

    def getTermByToken(self, token):
        """See `zope.schema.interfaces.IVocabularyTokenized`.

        The tokens for specifications are either the name of a spec on the
        same target or a URL for a spec.
        """
        spec = self._spec_from_url(token)
        if spec is None:
            spec = self.context.target.getSpecification(token)
        if spec and self._is_valid_candidate(spec):
            return self.toTerm(spec)
        raise LookupError(token)

    def search(self, query):
        """See `SQLObjectVocabularyBase.search`.

        We find specs where query is in the text of name or title, or matches
        the full text index and then filter out ineligible specs using
        `_filter_specs`.
        """
        if not query:
            return CountableIterator(0, [])
        spec = self._spec_from_url(query)
        if spec is not None and self._is_valid_candidate(spec):
            return CountableIterator(1, [spec])
        quoted_query = quote_like(query)
        sql_query = ("""
            (Specification.name LIKE %s OR
             Specification.title LIKE %s OR
             fti @@ ftq(%s))
            """
            % (quoted_query, quoted_query, quoted_query))
        all_specs = Specification.select(sql_query, orderBy=self._orderBy)
        candidate_specs = self._filter_specs(all_specs, check_target=True)
        return CountableIterator(len(candidate_specs), candidate_specs)

    @property
    def _all_specs(self):
        return self.context.target.specifications(
            filter=[SpecificationFilter.ALL], prejoin_people=False)

    def __iter__(self):
        return (
            self.toTerm(spec) for spec in self._filter_specs(self._all_specs))

    def __contains__(self, obj):
        return self._is_valid_candidate(obj)

