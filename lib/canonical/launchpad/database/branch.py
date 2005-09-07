# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Branch', 'BranchRelationship', 'BranchLabel']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol, MultipleJoin
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import IBranch
from canonical.launchpad.database.revision import Revision

from canonical.lp.dbschema import (
    EnumCol, BranchRelationships, BranchLifecycleStatus)


class Branch(SQLBase):
    """An ordered revision sequence in arch"""

    implements(IBranch)

    _table = 'Branch'
    name = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    url = StringCol(dbName='url')
    whiteboard = StringCol()

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    registrant = ForeignKey(dbName='registrant', foreignKey='Person')

    product = ForeignKey(dbName='product', foreignKey='Product', default=None)
    branch_product_name = StringCol()
    product_locked = BoolCol(default=False, notNull=True)

    home_page = StringCol()
    branch_home_page = StringCol()
    home_page_locked = BoolCol(default=False, notNull=True)

    starred = IntCol(default=1, notNull=True)
    lifecycle_status = EnumCol(schema=BranchLifecycleStatus, notNull=True,
        default=BranchLifecycleStatus.NEW)

    landing_target = ForeignKey(dbName='landing_target', foreignKey='Branch')
    current_delta_url = StringCol()
    current_diff_adds = IntCol()
    current_diff_deletes = IntCol()
    current_conflicts_url = StringCol()
    current_activity = IntCol(default=0, notNull=True)
    stats_updated = UtcDateTimeCol()

    # mirror_status = EnumCol(schema=MirrorStatus, default=MirrorStatus.XXX,
    #                         notNull=True)
    last_mirrored = UtcDateTimeCol()
    last_mirror_attempt = UtcDateTimeCol()
    mirror_failures = IntCol(default=0, notNull=True)

    cache_url = StringCol()

    revisions = MultipleJoin('Revision', joinColumn='branch',
        orderBy='-id')
    # XXX: changesets is a compatibility attribute, must be removed before
    # landing, if you are a reviewer, it is your duty to prevent that from
    # landing -- David Allouche 2005-09-05
    changesets = MultipleJoin('Revision', joinColumn='branch',
        orderBy='-id')

    @property
    def product_name(self):
        if self.product is None:
            return '+junk'
        return self.product.name

    def revision_count(self):
        return Revision.selectBy(branchID=self.id).count()

    subjectRelations = MultipleJoin('BranchRelationship', joinColumn='subject')
    objectRelations = MultipleJoin('BranchRelationship', joinColumn='object')

    def createRelationship(self, branch, relationship):
        BranchRelationship(subject=self, object=branch, label=relationship)

    def getRelations(self):
        return tuple(self.subjectRelations) + tuple(self.objectRelations)


class BranchRelationship(SQLBase):
    """A relationship between branches.

    e.g. "subject is a debianization-branch-of object"
    """

    _table = 'BranchRelationship'
    _columns = [
        ForeignKey(name='subject', foreignKey='Branch', dbName='subject', 
                   notNull=True),
        IntCol(name='label', dbName='label', notNull=True),
        ForeignKey(name='object', foreignKey='Branch', dbName='subject', 
                   notNull=True),
        ]

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

