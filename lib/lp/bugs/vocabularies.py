# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug domain vocabularies"""

__metaclass__ = type
__all__ = [
    'UsesBugsDistributionVocabulary',
    'BugNominatableDistroSeriesVocabulary',
    'BugNominatableProductSeriesVocabulary',
    'BugNominatableSeriesVocabulary',
    'BugTrackerVocabulary',
    'BugVocabulary',
    'BugWatchVocabulary',
    'DistributionUsingMaloneVocabulary',
    'project_products_using_malone_vocabulary_factory',
    'UsesBugsDistributionVocabulary',
    'WebBugTrackerVocabulary',
    ]

import cgi
from operator import attrgetter

from sqlobject import (
    CONTAINSSTRING,
    OR,
    )

from storm.expr import (
    And,
    Or,
    )

from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import (
    IVocabulary,
    IVocabularyTokenized,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.helpers import (
    ensure_unicode,
    shortlist,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    NamedSQLObjectVocabulary,
    SQLObjectVocabularyBase,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.app.browser.stringformatter import FormattersAPI
from lp.app.enums import ServiceUsage
from lp.bugs.interfaces.bugtask import IBugTask
from lp.bugs.interfaces.bugtracker import BugTrackerType
from lp.bugs.model.bug import Bug
from lp.bugs.model.bugtracker import BugTracker
from lp.bugs.model.bugwatch import BugWatch
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.productseries import ProductSeries
from lp.registry.vocabularies import DistributionVocabulary


class UsesBugsDistributionVocabulary(DistributionVocabulary):
    """Distributions that use Launchpad to track bugs.

    If the context is a distribution, it is always included in the
    vocabulary. Historic data is not invalidated if a distro stops
    using Launchpad to track bugs. This vocabulary offers the correct
    choices of distributions at this moment.
    """

    def __init__(self, context=None):
        super(UsesBugsDistributionVocabulary, self).__init__(context=context)
        self.distribution = IDistribution(self.context, None)

    @property
    def _filter(self):
        if self.distribution is None:
            distro_id = 0
        else:
            distro_id = self.distribution.id
        return OR(
            self._table.q.official_malone == True,
            self._table.id == distro_id)


class BugVocabulary(SQLObjectVocabularyBase):

    _table = Bug
    _orderBy = 'id'


class BugTrackerVocabulary(SQLObjectVocabularyBase):
    """All web and email based external bug trackers."""
    displayname = 'Select a bug tracker'
    step_title = 'Search'
    implements(IHugeVocabulary)
    _table = BugTracker
    _filter = True
    _orderBy = 'title'
    _order_by = [BugTracker.title]

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        result = IStore(self._table).find(
            self._table,
            self._filter,
            BugTracker.name == token).one()
        if result is None:
            raise LookupError(token)
        return self.toTerm(result)

    def search(self, query, vocab_filter=None):
        """Search for web bug trackers."""
        query = ensure_unicode(query).lower()
        results = IStore(self._table).find(
            self._table, And(
            self._filter,
            BugTracker.active == True,
            Or(
                CONTAINSSTRING(BugTracker.name, query),
                CONTAINSSTRING(BugTracker.title, query),
                CONTAINSSTRING(BugTracker.summary, query),
                CONTAINSSTRING(BugTracker.baseurl, query))))
        results = results.order_by(self._order_by)
        return results

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        results = self.search(query, vocab_filter)
        return CountableIterator(results.count(), results, self.toTerm)


class WebBugTrackerVocabulary(BugTrackerVocabulary):
    """All web-based bug tracker types."""
    _filter = BugTracker.bugtrackertype != BugTrackerType.EMAILADDRESS


def project_products_using_malone_vocabulary_factory(context):
    """Return a vocabulary containing a project's products using Malone."""
    project = IProjectGroup(context)
    return SimpleVocabulary([
        SimpleTerm(product, product.name, title=product.displayname)
        for product in project.products
        if product.bug_tracking_usage == ServiceUsage.LAUNCHPAD])


class BugWatchVocabulary(SQLObjectVocabularyBase):
    _table = BugWatch

    def __iter__(self):
        assert IBugTask.providedBy(self.context), (
            "BugWatchVocabulary expects its context to be an IBugTask.")
        bug = self.context.bug

        for watch in bug.watches:
            yield self.toTerm(watch)

    def toTerm(self, watch):

        def escape(string):
            return cgi.escape(string, quote=True)

        if watch.url.startswith('mailto:'):
            user = getUtility(ILaunchBag).user
            if user is None:
                title = FormattersAPI(
                    watch.bugtracker.title).obfuscate_email()
                return SimpleTerm(
                    watch, watch.id, escape(title))
            else:
                url = watch.url
                title = escape(watch.bugtracker.title)
                if url in title:
                    title = title.replace(
                        url, '<a href="%s">%s</a>' % (
                            escape(url), escape(url)))
                else:
                    title = '%s &lt;<a href="%s">%s</a>&gt;' % (
                        title, escape(url), escape(url[7:]))
                return SimpleTerm(watch, watch.id, title)
        else:
            return SimpleTerm(
                watch, watch.id, '%s <a href="%s">#%s</a>' % (
                    escape(watch.bugtracker.title),
                    escape(watch.url),
                    escape(watch.remotebug)))


class DistributionUsingMaloneVocabulary:
    """All the distributions that uses Malone officially."""

    implements(IVocabulary, IVocabularyTokenized)

    _orderBy = 'displayname'

    def __init__(self, context=None):
        self.context = context

    def __iter__(self):
        """Return an iterator which provides the terms from the vocabulary."""
        distributions_using_malone = Distribution.selectBy(
            official_malone=True, orderBy=self._orderBy)
        for distribution in distributions_using_malone:
            yield self.getTerm(distribution)

    def __len__(self):
        return Distribution.selectBy(official_malone=True).count()

    def __contains__(self, obj):
        return (IDistribution.providedBy(obj)
                and obj.bug_tracking_usage == ServiceUsage.LAUNCHPAD)

    def getTerm(self, obj):
        if obj not in self:
            raise LookupError(obj)
        return SimpleTerm(obj, obj.name, obj.displayname)

    def getTermByToken(self, token):
        found_dist = Distribution.selectOneBy(
            name=token, official_malone=True)
        if found_dist is None:
            raise LookupError(token)
        return self.getTerm(found_dist)


def BugNominatableSeriesVocabulary(context=None):
    """Return a nominatable series vocabulary."""
    if getUtility(ILaunchBag).distribution:
        return BugNominatableDistroSeriesVocabulary(
            context, getUtility(ILaunchBag).distribution)
    else:
        assert getUtility(ILaunchBag).product
        return BugNominatableProductSeriesVocabulary(
            context, getUtility(ILaunchBag).product)


class BugNominatableSeriesVocabularyBase(NamedSQLObjectVocabulary):
    """Base vocabulary class for series for which a bug can be nominated."""

    def __iter__(self):
        bug = self.context.bug

        all_series = self._getNominatableObjects()

        for series in sorted(all_series, key=attrgetter("displayname")):
            if bug.canBeNominatedFor(series):
                yield self.toTerm(series)

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name.capitalize())

    def getTermByToken(self, token):
        obj = self._queryNominatableObjectByName(token)
        if obj is None:
            raise LookupError(token)

        return self.toTerm(obj)

    def _getNominatableObjects(self):
        """Return the series objects that the bug can be nominated for."""
        raise NotImplementedError

    def _queryNominatableObjectByName(self, name):
        """Return the series object with the given name."""
        raise NotImplementedError


class BugNominatableProductSeriesVocabulary(
    BugNominatableSeriesVocabularyBase):
    """The product series for which a bug can be nominated."""

    _table = ProductSeries

    def __init__(self, context, product):
        BugNominatableSeriesVocabularyBase.__init__(self, context)
        self.product = product

    def _getNominatableObjects(self):
        """See BugNominatableSeriesVocabularyBase."""
        return shortlist(self.product.series)

    def _queryNominatableObjectByName(self, name):
        """See BugNominatableSeriesVocabularyBase."""
        return self.product.getSeries(name)


class BugNominatableDistroSeriesVocabulary(
    BugNominatableSeriesVocabularyBase):
    """The distribution series for which a bug can be nominated."""

    _table = DistroSeries

    def __init__(self, context, distribution):
        BugNominatableSeriesVocabularyBase.__init__(self, context)
        self.distribution = distribution

    def _getNominatableObjects(self):
        """Return all non-obsolete distribution series"""
        return [
            series for series in shortlist(self.distribution.series)
            if series.status != SeriesStatus.OBSOLETE]

    def _queryNominatableObjectByName(self, name):
        """See BugNominatableSeriesVocabularyBase."""
        return self.distribution.getSeries(name)
