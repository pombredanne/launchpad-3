# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugTracker', 'BugTrackerSet']

import urllib

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLObjectNotFound)
from sqlobject.sqlbuilder import AND

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, flush_database_updates, quote, sqlvalues)

from canonical.lp.dbschema import BugTrackerType

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.interfaces import (
    IBugTracker, IBugTrackerSet, NotFoundError)



class BugTracker(SQLBase):
    """A class to access the BugTracker table of the db. Each BugTracker is a
    distinct instance of that bug tracking tool. For example, each Bugzilla
    deployment is a separate BugTracker. bugzilla.mozilla.org and
    bugzilla.gnome.org are each distinct BugTracker's.
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

    def normalise_baseurl(self, baseurl):
        # turn https to http, and raise an exception elsewhere
        schema, rest = urllib.splittype(baseurl)
        if schema not in ['http', 'https']:
            return baseurl
        if schema == 'https':
            schema = 'http'
        return '%s:%s' % (schema, rest)

    def _baseURLPermutations(self, base_url):
        """Return all the possible variants of a base URL.

        Sometimes the URL ends with slash, sometimes not. Sometimes http
        is used, sometimes https. This gives a list of all possible
        variants, so that queryByBaseURL can match a base URL, even if
        it doesn't match exactly what is stored in the database.

            >>> BugTrackerSet()._baseURLPermutations('http://foo/bar')
            ['http://foo/bar', 'http://foo/bar/',
             'https://foo/bar', 'https://foo/bar/']
        """
        http_schemas = ['http', 'https']
        url_schema, rest = urllib.splittype(base_url)
        if url_schema in http_schemas:
            possible_schemas = http_schemas
        else:
            # This else-clause is here since we have no strict
            # requirement that bug trackers have to have http URLs.
            possible_schemas = [url_schema]
        alternative_urls = []
        for schema in possible_schemas:
            url = "%s:%s" % (schema, rest)
            alternative_urls.append(url)
            if url.endswith('/'):
                alternative_urls.append(url[:-1])
            else:
                alternative_urls.append(url + '/')
        # Make sure that the original URL is always first, to make the
        # common case require less db queries.
        alternative_urls.remove(base_url)
        return [base_url] + alternative_urls

    def queryByBaseURL(self, baseurl):
        """See IBugTrackerSet."""
        for url in self._baseURLPermutations(baseurl):
            bugtracker = BugTracker.selectOneBy(baseurl=url)
            if bugtracker is not None:
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
        baseurl = self.normalise_baseurl(baseurl)
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

