# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BranchRelationship', 'BranchLabel']

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.lp import dbschema


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
        return dbschema.BranchRelationships.items[self.label]

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

