# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugTracker', 'BugTrackerSet',
           'BugTrackerAlias', 'BugTrackerAliasSet']

import re
import urllib

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLObjectNotFound)
from sqlobject.sqlbuilder import AND

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, flush_database_updates, quote, quote_like, sqlvalues)

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.interfaces import (
    BugTrackerType, IBugTracker, IBugTrackerAlias, IBugTrackerAliasSet,
    IBugTrackerSet, NotFoundError)


def normalise_leading_slashes(rest):
    """Ensure that the 'rest' segment of a URL starts with //."""
    slashre = re.compile('^/*(.*)')
    return '//' + slashre.match(rest).group(1)


def normalise_base_url(base_url):
    """Convert https to http, and normalise scheme for others."""
    schema, rest = urllib.splittype(base_url)
    if schema == 'https':
        return 'http:' + rest
    elif schema is None:
        return 'http:' + normalise_leading_slashes(base_url)
    else:
        return '%s:%s' % (schema, rest)


def base_url_permutations(base_url):
    """Return all the possible variants of a base URL.

    Sometimes the URL ends with slash, sometimes not. Sometimes http
    is used, sometimes https. This gives a list of all possible
    variants, so that queryByBaseURL can match a base URL, even if it
    doesn't match exactly what is stored in the database.

    >>> base_url_permutations('http://foo/bar')
    ['http://foo/bar', 'http://foo/bar/',
     'https://foo/bar', 'https://foo/bar/']
    """
    http_schemas = ['http', 'https']
    url_schema, rest = urllib.splittype(base_url)
    if url_schema in http_schemas or url_schema is None:
        possible_schemas = http_schemas
        rest = normalise_leading_slashes(rest)
    else:
        # This else-clause is here since we have no strict
        # requirement that bug trackers have to have http URLs.
        possible_schemas = [url_schema]
    alternative_urls = [base_url]
    for schema in possible_schemas:
        url = "%s:%s" % (schema, rest)
        if url != base_url:
            alternative_urls.append(url)
        if url.endswith('/'):
            alternative_urls.append(url[:-1])
        else:
            alternative_urls.append(url + '/')
    return alternative_urls


class BugTracker(SQLBase):
    """A class to access the BugTracker table in the database.

    Each BugTracker is a distinct instance of that bug tracking
    tool. For example, each Bugzilla deployment is a separate
    BugTracker. bugzilla.mozilla.org and bugzilla.gnome.org are each
    distinct BugTrackers.
    """
    implements(IBugTracker)

    _table = 'BugTracker'

    bugtrackertype = EnumCol(dbName='bugtrackertype',
        schema=BugTrackerType, notNull=True)
    name = StringCol(notNull=True, unique=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    baseurl = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    contactdetails = StringCol(notNull=False)
    projects = SQLMultipleJoin(
        'Project', joinColumn='bugtracker', orderBy='name')
    products = SQLMultipleJoin(
        'Product', joinColumn='bugtracker', orderBy='name')
    watches = SQLMultipleJoin('BugWatch', joinColumn='bugtracker',
                              orderBy='-datecreated', prejoins=['bug'])

    @property
    def latestwatches(self):
        """See IBugTracker"""
        return self.watches[:10]

    def getBugsWatching(self, remotebug):
        """See IBugTracker"""
        return shortlist(Bug.select(AND(BugWatch.q.bugID == Bug.q.id,
                                        BugWatch.q.bugtrackerID == self.id,
                                        BugWatch.q.remotebug == remotebug),
                                    distinct=True,
                                    orderBy=['datecreated']))

    def getBugWatchesNeedingUpdate(self, hours_since_last_check):
        """See IBugTracker."""
        query = (
            """bugtracker = %s AND
               (lastchecked < (now() at time zone 'UTC' - interval '%s hours')
                OR lastchecked IS NULL)""" % sqlvalues(
                    self.id, hours_since_last_check))
        return BugWatch.select(query, orderBy=["remotebug", "id"])

    _bugtracker_aliases = SQLMultipleJoin(
        'BugTrackerAlias', joinColumn='bugtracker', orderBy='base_url')

    def _get_aliases(self):
        return [alias.base_url for alias in self._bugtracker_aliases]

    def _set_aliases(self, alias_urls=None):
        if alias_urls is None:
            alias_urls = []

        current_aliases_by_url = dict(
            (alias.base_url, alias) for alias in self._bugtracker_aliases)

        alias_urls = set(alias_urls)
        current_alias_urls = set(current_aliases_by_url)

        to_add = alias_urls - current_alias_urls
        to_del = current_alias_urls - alias_urls

        for url in to_add:
            BugTrackerAlias(bugtracker=self, base_url=url)
        for url in to_del:
            alias = current_aliases_by_url[url]
            alias.destroySelf()

    aliases = property(_get_aliases, _set_aliases, _set_aliases)


class BugTrackerSet:
    """Implements IBugTrackerSet for a container or set of BugTracker's,
    either the full set in the db, or a subset.
    """

    implements(IBugTrackerSet)

    table = BugTracker

    def __init__(self):
        self.title = 'Bug trackers registered in Malone'

    def get(self, bugtracker_id, default=None):
        """See IBugTrackerSet"""
        try:
            return BugTracker.get(bugtracker_id)
        except SQLObjectNotFound:
            return default

    def getByName(self, name, default=None):
        """See IBugTrackerSet"""
        return self.table.selectOne(self.table.q.name == name)

    def __getitem__(self, name):
        item = self.table.selectOne(self.table.q.name == name)
        if item is None:
            raise NotFoundError(name)
        else:
            return item

    def __iter__(self):
        for row in self.table.select(orderBy="title"):
            yield row

    def queryByBaseURL(self, baseurl):
        """See IBugTrackerSet."""
        for url in base_url_permutations(baseurl):
            bugtracker = BugTracker.selectOneBy(baseurl=url)
            if bugtracker is not None:
                return bugtracker
        # If we didn't find the exact URL but there is
        # a substring match, use that instead.
        for bugtracker in BugTracker.select(
            "baseurl LIKE '%%' || %s || '%%'" % quote_like(baseurl), limit=1):
            return bugtracker
        return None

    def search(self):
        """See canonical.launchpad.interfaces.IBugTrackerSet."""
        return BugTracker.select()

    def ensureBugTracker(self, baseurl, owner, bugtrackertype,
        title=None, summary=None, contactdetails=None, name=None):
        # first try and find one without normalisation
        bugtracker = self.queryByBaseURL(baseurl)
        if bugtracker is not None:
            return bugtracker
        # now try and normalise it
        baseurl = normalise_base_url(baseurl)
        bugtracker = self.queryByBaseURL(baseurl)
        if bugtracker is not None:
            return bugtracker
        # create the bugtracker, we don't know about it. we'll use the
        # normalised base url
        if name is None:
            scheme, host = urllib.splittype(baseurl)
            host, path = urllib.splithost(host)
            name = 'auto-%s' % host
        if title is None:
            title = quote('Bug tracker at %s' % baseurl)
        bugtracker = BugTracker(name=name,
            bugtrackertype=bugtrackertype,
            title=title, summary=summary, baseurl=baseurl,
            contactdetails=contactdetails, owner=owner)
        flush_database_updates()
        return bugtracker

    @property
    def bugtracker_count(self):
        return BugTracker.select().count()

    def getMostActiveBugTrackers(self, limit=None):
        """See canonical.launchpad.interfaces.IBugTrackerSet."""
        result = shortlist(self.search(), longest_expected=20)
        result.sort(key=lambda bugtracker: -bugtracker.watches.count())
        if limit and limit > 0:
            return result[:limit]
        else:
            return result


class BugTrackerAlias(SQLBase):
    """See `IBugTrackerAlias`."""
    implements(IBugTrackerAlias)

    bugtracker = ForeignKey(
        foreignKey="BugTracker", dbName="bugtracker", notNull=True)
    base_url = StringCol(notNull=True)


class BugTrackerAliasSet:
    """See `IBugTrackerAliasSet`."""
    implements(IBugTrackerAliasSet)

    table = BugTrackerAlias

    def get(self, bugtrackeralias_id, default=None):
        """See `IBugTrackerAliasSet`."""
        try:
            return BugTrackerAlias.get(bugtrackeralias_id)
        except SQLObjectNotFound:
            return default

    def queryByBaseURL(self, base_url):
        """See IBugTrackerSet."""
        for url in base_url_permutations(base_url):
            bugtrackeralias = BugTrackerAlias.selectOneBy(base_url=url)
            if bugtrackeralias is not None:
                return bugtrackeralias
        # If we didn't find the exact URL but there is
        # a substring match, use that instead.
        query = "base_url LIKE '%%' || %s || '%%'" % quote_like(base_url)
        for bugtrackeralias in BugTrackerAlias.select(query, limit=1):
            return bugtrackeralias
        return None
