# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'BugTracker',
    'BugTrackerAlias',
    'BugTrackerAliasSet',
    'BugTrackerSet']

import re

from itertools import chain
# splittype is not formally documented, but is in urllib.__all__, is
# simple, and is heavily used by the rest of urllib, hence is unlikely
# to change or go away.
from urllib import splittype

from zope.interface import implements

from sqlobject import (
    ForeignKey, OR, SQLMultipleJoin, SQLObjectNotFound, StringCol)
from sqlobject.sqlbuilder import AND

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, flush_database_updates, quote, sqlvalues)

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.interfaces import (
    BugTrackerType, IBugTracker, IBugTrackerAlias, IBugTrackerAliasSet,
    IBugTrackerSet, NotFoundError)
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp.uri import URI


def normalise_leading_slashes(rest):
    """Ensure that the 'rest' segment of a URL starts with //."""
    return '//' + rest.lstrip('/')


def normalise_base_url(base_url):
    """Convert https to http, and normalise scheme for others."""
    schema, rest = splittype(base_url)
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
    url_schema, rest = splittype(base_url)
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

def make_bugtracker_name(uri):
    """Return a name string for a bug tracker based on a URI.

    :param uri: The base URI to be used to identify the bug tracker,
        e.g. http://bugs.example.com or mailto:bugs@example.com
    """
    base_uri = URI(uri)
    if base_uri.scheme == 'mailto':
        if valid_email(base_uri.path):
            base_name = base_uri.path.split('@', 1)[0]
        else:
            raise ValueError(
                'Not a valid email address: %s' % base_uri.path)
    else:
        base_name = base_uri.host

    return 'auto-%s' % base_name


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
    summary = StringCol(notNull=False)
    baseurl = StringCol(notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
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
        # We special-case email address bug trackers. Since we don't
        # record a remote bug id for them we can never know which bugs
        # are already watching a remote bug.
        if self.bugtrackertype == BugTrackerType.EMAILADDRESS:
            return []

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

    # Join to return a list of BugTrackerAliases relating to this
    # BugTracker.
    _bugtracker_aliases = SQLMultipleJoin(
        'BugTrackerAlias', joinColumn='bugtracker')

    def _get_aliases(self):
        """See `IBugTracker.aliases`."""
        alias_urls = set(alias.base_url for alias in self._bugtracker_aliases)
        # Although it does no harm if the current baseurl is also an
        # alias, we hide it and all its permutations to avoid
        # confusion.
        alias_urls.difference_update(base_url_permutations(self.baseurl))
        return tuple(sorted(alias_urls))

    def _set_aliases(self, alias_urls):
        """See `IBugTracker.aliases`."""
        if alias_urls is None:
            alias_urls = set()
        else:
            alias_urls = set(alias_urls)

        current_aliases_by_url = dict(
            (alias.base_url, alias) for alias in self._bugtracker_aliases)
        # Make a set of the keys, i.e. a set of current URLs.
        current_alias_urls = set(current_aliases_by_url)

        # URLs we need to add as aliases.
        to_add = alias_urls - current_alias_urls
        # URL aliases we need to delete.
        to_del = current_alias_urls - alias_urls

        for url in to_add:
            BugTrackerAlias(bugtracker=self, base_url=url)
        for url in to_del:
            alias = current_aliases_by_url[url]
            alias.destroySelf()

    aliases = property(
        _get_aliases, _set_aliases, None,
        """A list of the alias URLs. See `IBugTracker`.

        The aliases are found by querying BugTrackerAlias. Assign an
        iterable of URLs or None to set or remove aliases.
        """)

    @property
    def imported_bug_messages(self):
        """See `IBugTracker`."""
        return BugMessage.select(
            AND((BugMessage.q.bugwatchID == BugWatch.q.id),
                (BugWatch.q.bugtrackerID == self.id)),
            orderBy=BugMessage.q.id)


class BugTrackerSet:
    """Implements IBugTrackerSet for a container or set of BugTracker's,
    either the full set in the db, or a subset.
    """

    implements(IBugTrackerSet)

    table = BugTracker

    def __init__(self):
        self.title = 'Bug trackers registered in Launchpad'

    def get(self, bugtracker_id, default=None):
        """See `IBugTrackerSet`."""
        try:
            return BugTracker.get(bugtracker_id)
        except SQLObjectNotFound:
            return default

    def getByName(self, name, default=None):
        """See `IBugTrackerSet`."""
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
        """See `IBugTrackerSet`."""
        # All permutations we'll search for.
        permutations = base_url_permutations(baseurl)
        # All permutations that are needed for substring matches (trim
        # trailing slashes and de-duplicate).
        permutations_simple = set(url.rstrip('/') for url in permutations)
        # Construct the search. All the important parts in the next
        # expression are lazily evaluated. SQLObject queries do not
        # execute any SQL until results are pulled, so the first query
        # to return a match will be the last query executed.
        matching_bugtrackers = chain(
            # Search for any permutation in BugTracker.
            BugTracker.select(
                OR(*(BugTracker.q.baseurl == url
                     for url in permutations))),
            # Search for any permutation in BugTrackerAlias.
            (alias.bugtracker for alias in
             BugTrackerAlias.select(
                    OR(*(BugTrackerAlias.q.base_url == url
                         for url in permutations)))),
            # Search for a substring match in BugTracker.
            BugTracker.select(
                OR(*(BugTracker.q.baseurl.contains(url)
                     for url in permutations_simple)),
                limit=1),
            # Search for a substring match in BugTrackerAlias.
            (alias.bugtracker for alias in
             BugTrackerAlias.select(
                    OR(*(BugTrackerAlias.q.base_url.contains(url)
                         for url in permutations_simple)),
                    limit=1)))
        # Return the first match.
        for bugtracker in matching_bugtrackers:
            return bugtracker
        return None

    def search(self):
        """See `IBugTrackerSet`."""
        return BugTracker.select()

    def ensureBugTracker(self, baseurl, owner, bugtrackertype,
        title=None, summary=None, contactdetails=None, name=None):
        """See `IBugTrackerSet`."""
        # Try to find an existing bug tracker that matches.
        bugtracker = self.queryByBaseURL(baseurl)
        if bugtracker is not None:
            return bugtracker
        # Create the bugtracker; we don't know about it.
        if name is None:
            base_name = make_bugtracker_name(baseurl)
            # If we detect that this name exists already we mutate it
            # until it doesn't.
            name = base_name
            name_increment = 1
            while self.getByName(name) is not None:
                name = "%s-%d" % (base_name, name_increment)
                name_increment += 1
        if title is None:
            title = baseurl
        bugtracker = BugTracker(
            name=name, bugtrackertype=bugtrackertype,
            title=title, summary=summary, baseurl=baseurl,
            contactdetails=contactdetails, owner=owner)
        flush_database_updates()
        return bugtracker

    @property
    def bugtracker_count(self):
        return BugTracker.select().count()

    def getMostActiveBugTrackers(self, limit=None):
        """See `IBugTrackerSet`."""
        result = shortlist(self.search(), longest_expected=20)
        result.sort(key=lambda bugtracker: -bugtracker.watches.count())
        if limit and limit > 0:
            return result[:limit]
        else:
            return result

    def getPillarsForBugtrackers(self, bugtrackers):
        """See `IBugTrackerSet`."""
        from canonical.launchpad.database.product import Product
        from canonical.launchpad.database.project import Project
        ids = [str(b.id) for b in bugtrackers]
        products = Product.select(
            "bugtracker in (%s)" % ",".join(ids), orderBy="name")
        projects = Project.select(
            "bugtracker in (%s)" % ",".join(ids), orderBy="name")
        ret = {}
        for product in products:
            ret.setdefault(product.bugtracker, []).append(product)
        for project in projects:
            ret.setdefault(project.bugtracker, []).append(project)
        return ret


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

    def queryByBugTracker(self, bugtracker):
        """See IBugTrackerSet."""
        return self.table.selectBy(bugtracker=bugtracker.id)

