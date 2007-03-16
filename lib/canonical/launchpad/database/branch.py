# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Branch', 'BranchSet', 'BranchRelationship', 'BranchLabel']

import re

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound, AND)

from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.sqlbase import (
    cursor, quote, SQLBase, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch, IBranchSet,
    ILaunchpadCelebrities, NotFoundError)
from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.lp.dbschema import (
    BranchRelationships, BranchLifecycleStatus)


class Branch(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranch)
    _table = 'Branch'
    _defaultOrder = ['product', '-lifecycle_status', 'author', 'name']

    name = StringCol(notNull=False)
    title = StringCol(notNull=False)
    summary = StringCol(notNull=True)
    url = StringCol(dbName='url')
    whiteboard = StringCol(default=None)
    mirror_status_message = StringCol(default=None)
    started_at = ForeignKey(dbName='started_at', foreignKey='BranchRevision',
                            default=None)

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    author = ForeignKey(dbName='author', foreignKey='Person', default=None)

    product = ForeignKey(dbName='product', foreignKey='Product', default=None)
    branch_product_name = StringCol(default=None)
    product_locked = BoolCol(default=False, notNull=True)

    home_page = StringCol()
    branch_home_page = StringCol(default=None)
    home_page_locked = BoolCol(default=False, notNull=True)

    lifecycle_status = EnumCol(schema=BranchLifecycleStatus, notNull=True,
        default=BranchLifecycleStatus.NEW)

    landing_target = ForeignKey(dbName='landing_target', foreignKey='Branch',
                                default=None)
    current_delta_url = StringCol(default=None)
    current_diff_adds = IntCol(default=None)
    current_diff_deletes = IntCol(default=None)
    current_conflicts_url = StringCol(default=None)
    current_activity = IntCol(default=0, notNull=True)
    stats_updated = UtcDateTimeCol(default=None)

    last_mirrored = UtcDateTimeCol(default=None)
    last_mirrored_id = StringCol(default=None)
    last_mirror_attempt = UtcDateTimeCol(default=None)
    mirror_failures = IntCol(default=0, notNull=True)
    pull_disabled = BoolCol(default=False, notNull=True)

    last_scanned = UtcDateTimeCol(default=None)
    last_scanned_id = StringCol(default=None)
    revision_count = IntCol(default=0, notNull=True)

    cache_url = StringCol(default=None)

    @property
    def revision_history(self):
        return BranchRevision.select('''
            BranchRevision.branch = %s AND
            BranchRevision.sequence IS NOT NULL
            ''' % sqlvalues(self),
            prejoins=['revision'], orderBy='-sequence')

    subjectRelations = SQLMultipleJoin(
        'BranchRelationship', joinColumn='subject')
    objectRelations = SQLMultipleJoin(
        'BranchRelationship', joinColumn='object')

    subscriptions = SQLMultipleJoin(
        'BranchSubscription', joinColumn='branch', orderBy='id')
    subscribers = SQLRelatedJoin(
        'Person', joinColumn='branch', otherColumn='person',
        intermediateTable='BranchSubscription', orderBy='name')

    bug_branches = SQLMultipleJoin(
        'BugBranch', joinColumn='branch', orderBy='id')

    spec_links = SQLMultipleJoin('SpecificationBranch',
        joinColumn='branch',
        orderBy='id')

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    mirror_request_time = UtcDateTimeCol(default=None)

    @property
    def related_bugs(self):
        """See IBranch."""
        return [bug_branch.bug for bug_branch in self.bug_branches]

    @property
    def warehouse_url(self):
        """See IBranch."""
        root = config.supermirror.warehouse_root_url
        return "%s%08x" % (root, self.id)

    @property
    def product_name(self):
        """See IBranch."""
        if self.product is None:
            return '+junk'
        return self.product.name

    @property
    def unique_name(self):
        """See IBranch."""
        return u'~%s/%s/%s' % (self.owner.name, self.product_name, self.name)

    @property
    def displayname(self):
        """See IBranch."""
        if self.title:
            return self.title
        else:
            return self.unique_name

    @property
    def sort_key(self):
        """See IBranch."""
        if self.product is None:
            product = None
        else:
            product = self.product.name
        if self.author is None:
            author = None
        else:
            author = self.author.browsername
        status = self.lifecycle_status.sortkey
        name = self.name
        owner = self.owner.name
        return (product, status, author, name, owner)

    def latest_revisions(self, quantity=10):
        """See IBranch."""
        return self.revision_history.limit(quantity)

    def revisions_since(self, timestamp):
        """See IBranch."""
        return BranchRevision.select(
            'Revision.id=BranchRevision.revision AND '
            'BranchRevision.branch = %d AND '
            'BranchRevision.sequence IS NOT NULL AND '
            'Revision.revision_date > %s' %
            (self.id, quote(timestamp)),
            orderBy='-sequence',
            clauseTables=['Revision'])

    def createRelationship(self, branch, relationship):
        BranchRelationship(subject=self, object=branch, label=relationship)

    def getRelations(self):
        return tuple(self.subjectRelations) + tuple(self.objectRelations)

    # subscriptions
    def subscribe(self, person):
        """See IBranch."""
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub
        return BranchSubscription(branch=self, person=person)

    def unsubscribe(self, person):
        """See IBranch."""
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                BranchSubscription.delete(sub.id)
                break

    def has_subscription(self, person):
        """See IBranch."""
        assert person is not None
        subscription = BranchSubscription.selectOneBy(
            person=person, branch=self)
        return subscription is not None

    def getBranchRevision(self, sequence):
        """See IBranch.getBranchRevision()"""
        assert sequence is not None, \
               "Only use this to fetch revisions from mainline history."
        return BranchRevision.selectOneBy(branch=self, sequence=sequence)

    def createBranchRevision(self, sequence, revision):
        """See IBranch.createBranchRevision()"""
        return BranchRevision(
            branch=self, sequence=sequence, revision=revision)

    def updateScannedDetails(self, revision_id, revision_count):
        """See IBranch."""
        self.last_scanned = UTC_NOW
        self.last_scanned_id = revision_id
        self.revision_count = revision_count

    def getScannerData(self):
        """See IBranch."""
        cur = cursor()
        cur.execute("""
            SELECT BranchRevision.id, BranchRevision.sequence,
                Revision.revision_id
            FROM Revision, BranchRevision
            WHERE Revision.id = BranchRevision.revision
                AND BranchRevision.branch = %s
            ORDER BY BranchRevision.sequence
            """ % sqlvalues(self))
        ancestry = set()
        history = []
        branch_revision_map = {}
        for branch_revision_id, sequence, revision_id in cur.fetchall():
            ancestry.add(revision_id)
            branch_revision_map[revision_id] = branch_revision_id
            if sequence is not None:
                history.append(revision_id)
        return ancestry, history, branch_revision_map


class BranchSet:
    """The set of all branches."""

    implements(IBranchSet)

    def __getitem__(self, branch_id):
        """See IBranchSet."""
        branch = self.get(branch_id)
        if branch is None:
            raise NotFoundError(branch_id)
        return branch

    def __iter__(self):
        """See IBranchSet."""
        return iter(Branch.select(prejoins=['owner', 'product']))

    def count(self):
        """See IBranchSet."""
        return Branch.select().count()

    def countBranchesWithAssociatedBugs(self):
        """See IBranchSet."""
        return Branch.select(
            'Branch.id = BugBranch.branch',
            clauseTables=['BugBranch'],
            distinct=True).count()

    def get(self, branch_id, default=None):
        """See IBranchSet."""
        try:
            return Branch.get(branch_id)
        except SQLObjectNotFound:
            return default

    def new(self, name, owner, product, url, title=None,
            lifecycle_status=BranchLifecycleStatus.NEW, author=None,
            summary=None, home_page=None, whiteboard=None, date_created=None):
        """See IBranchSet."""
        if not home_page:
            home_page = None
        if date_created is None:
            date_created = UTC_NOW
        return Branch(
            name=name, owner=owner, author=author, product=product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            home_page=home_page, whiteboard=whiteboard,
            date_created=date_created)

    def getByUrl(self, url, default=None):
        """See IBranchSet."""
        assert not url.endswith('/')
        prefix = config.launchpad.supermirror_root
        if url.startswith(prefix):
            branch = self.getByUniqueName(url[len(prefix):])
        else:
            branch = Branch.selectOneBy(url=url)
        if branch is None:
            return default
        else:
            return branch

    def getByUniqueName(self, unique_name, default=None):
        """Find a branch by its ~owner/product/name unique name."""
        # import locally to avoid circular imports
        match = re.match('^~([^/]+)/([^/]+)/([^/]+)$', unique_name)
        if match is None:
            return default
        owner_name, product_name, branch_name = match.groups()
        if product_name == '+junk':
            query = ("Branch.owner = Person.id"
                     + " AND Branch.product IS NULL"
                     + " AND Person.name = " + quote(owner_name)
                     + " AND Branch.name = " + quote(branch_name))
            tables=['Person']
        else:
            query = ("Branch.owner = Person.id"
                     + " AND Branch.product = Product.id"
                     + " AND Person.name = " + quote(owner_name)
                     + " AND Product.name = " + quote(product_name)
                     + " AND Branch.name = " + quote(branch_name))
            tables=['Person', 'Product']
        branch = Branch.selectOne(query, clauseTables=tables)
        if branch is None:
            return default
        else:
            return branch

    def getBranchesToScan(self):
        """See IBranchSet.getBranchesToScan()"""
        # Return branches where the scanned and mirrored IDs don't match.
        # Branches with a NULL last_mirrored_id have never been
        # successfully mirrored so there is no point scanning them.
        # Branches with a NULL last_scanned_id have not been scanned yet,
        # so are included.

        return Branch.select('''
            Branch.last_mirrored_id IS NOT NULL AND
            (Branch.last_scanned_id IS NULL OR
             Branch.last_scanned_id <> Branch.last_mirrored_id)
            ''')

    def getProductDevelopmentBranches(self, products):
        """See IBranchSet."""
        product_ids = [product.id for product in products]
        query = Branch.select('''
            (Branch.id = ProductSeries.import_branch OR
            Branch.id = ProductSeries.user_branch) AND
            ProductSeries.id = Product.development_focus AND
            Branch.product IN %s''' % sqlvalues(product_ids),
            clauseTables = ['Product', 'ProductSeries'])
        return query.prejoin(['author'])
            
    def getActiveUserBranchSummaryForProducts(self, products):
        """See IBranchSet."""
        product_ids = [product.id for product in products]
        if not product_ids:
            return []
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        lifecycle_clause = self._lifecycleClause(
            DEFAULT_BRANCH_STATUS_IN_LISTING)
        cur = cursor()
        cur.execute("""
            SELECT
                Branch.product, COUNT(Branch.id), MAX(Revision.revision_date)
            FROM Branch
            LEFT OUTER JOIN Revision
            ON Branch.last_scanned_id = Revision.revision_id
            WHERE Branch.product in %s
            AND Branch.owner <> %d %s
            GROUP BY Product
            """ % (quote(product_ids), vcs_imports.id, lifecycle_clause))
        result = {}
        product_map = dict([(product.id, product) for product in products])
        for product_id, branch_count, last_commit in cur.fetchall():
            product = product_map[product_id]
            result[product] = {'branch_count' : branch_count,
                               'last_commit' : last_commit}
        return result

    def getRecentlyChangedBranches(self, branch_count):
        """See IBranchSet."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        query = '''
            Branch.last_scanned IS NOT NULL
            AND Branch.owner <> %d
            ''' % vcs_imports.id
        branches = Branch.select(
            query, orderBy=['-last_scanned'], limit=branch_count)
        return branches.prejoin(['author', 'product'])

    def getRecentlyImportedBranches(self, branch_count):
        """See IBranchSet."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        query = '''
            Branch.last_scanned IS NOT NULL
            AND Branch.owner = %d
            ''' % vcs_imports.id
        branches = Branch.select(
            query, orderBy=['-last_scanned'], limit=branch_count)
        return branches.prejoin(['author', 'product'])

    def getRecentlyRegisteredBranches(self, branch_count):
        """See IBranchSet."""

        branches = Branch.select(orderBy=['-date_created'], limit=branch_count)
        return branches.prejoin(['author', 'product'])

    def getLastCommitForBranches(self, branches):
        """Return a map of branch id to last commit time."""
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            # Return a sensible default if given no branches
            return {}
        cur = cursor()
        cur.execute("""
            SELECT Branch.id, Revision.revision_date
            FROM Branch
            LEFT OUTER JOIN Revision
            ON Branch.last_scanned_id = Revision.revision_id
            WHERE Branch.id IN %s
            """ % quote(branch_ids))
        commits = dict(cur.fetchall())
        return dict([(branch, commits.get(branch.id, None))
                     for branch in branches])

    def getBranchesForOwners(self, people):
        """Return the branches that are owned by the people specified."""
        owner_ids = [person.id for person in people]
        if not owner_ids:
            return []
        branches = Branch.select('Branch.owner in %s' % quote(owner_ids))
        return branches.prejoin(['product'])

    def _lifecycleClause(self, lifecycle_statuses):
        lifecycle_clause = ''
        if lifecycle_statuses:
            lifecycle_clause = (
                ' AND Branch.lifecycle_status in %s' %
                quote(lifecycle_statuses))
        return lifecycle_clause

    def getBranchesForPerson(self, person, lifecycle_statuses=None):
        """See IBranchSet."""
        owner_ids = [str(team.id) for team in person.teams_participated_in]
        owner_ids.append(str(person.id))
        owner_ids = ','.join(owner_ids)

        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)

        subscribed_branches = Branch.select(
            '''Branch.id = BranchSubscription.branch
            AND BranchSubscription.person in (%s) %s
            ''' % (owner_ids, lifecycle_clause),
            clauseTables=['BranchSubscription'])

        owner_author_branches = Branch.select(
            '''(Branch.owner in (%s) OR
            Branch.author = %s) %s
            ''' % (owner_ids, person.id, lifecycle_clause))
        
        return subscribed_branches.union(
            owner_author_branches, orderBy=Branch._defaultOrder)

    def getBranchesAuthoredByPerson(self, person, lifecycle_statuses=None):
        """See IBranchSet."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)

        return Branch.select(
            'Branch.author = %s %s' % (person.id, lifecycle_clause))

    def getBranchesRegisteredByPerson(self, person, lifecycle_statuses=None):
        """See IBranchSet."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)

        return Branch.select(
            '''Branch.owner = %s AND
            (Branch.author is NULL OR
             Branch.author != %s) %s''' %
            (person.id, person.id, lifecycle_clause))

    def getBranchesSubscribedByPerson(self, person, lifecycle_statuses=None):
        """See IBranchSet."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)

        return Branch.select(
            '''Branch.id = BranchSubscription.branch
            AND BranchSubscription.person = %s %s
            ''' % (person.id, lifecycle_clause),
            clauseTables=['BranchSubscription'])

    def getBranchesForProduct(self, product, lifecycle_statuses=None):
        """See IBranchSet."""
        lifecycle_clause = self._lifecycleClause(lifecycle_statuses)

        return Branch.select(
            'Branch.product = %s %s' % (product.id, lifecycle_clause))



class BranchRelationship(SQLBase):
    """A relationship between branches.

    e.g. "subject is a debianization-branch-of object"
    """

    _table = 'BranchRelationship'
    subject = ForeignKey(foreignKey='Branch', dbName='subject', notNull=True),
    label = IntCol(dbName='label', notNull=True),
    object = ForeignKey(foreignKey='Branch', dbName='object', notNull=True),

    def _get_src(self):
        return self.subject
    def _set_src(self, value):
        self.subject = value

    def _get_dst(self):
        return self.object
    def _set_dst(self, value):
        self.object = value

    def _get_labelText(self):
        return BranchRelationships.items[self.label]

    def nameSelector(self, sourcepackage=None, selected=None):
        # XXX: Let's get HTML out of the database code.
        #      -- SteveAlexander, 2005-04-22
        html = '<select name="binarypackagename">\n'
        if not sourcepackage:
            # Return nothing for an empty query.
            binpkgs = []
        else:
            binpkgs = self._table.select("""
                binarypackagename.id = binarypackage.binarypackagename AND
                binarypackage.build = build.id AND
                build.sourcepackagerelease = sourcepackagerelease.id AND
                sourcepackagerelease.sourcepackage = %s"""
                % sqlvalues(sourcepackage),
                clauseTables = ['binarypackagename', 'binarypackage',
                                'build', 'sourcepackagerelease']
                )
        for pkg in binpkgs:
            html = html + '<option value="' + pkg.name + '"'
            if pkg.name==selected: html = html + ' selected'
            html = html + '>' + pkg.name + '</option>\n'
        html = html + '</select>\n'
        return html


class BranchLabel(SQLBase):
    _table = 'BranchLabel'

    label = ForeignKey(foreignKey='Label', dbName='label', notNull=True)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', notNull=True)
