# SQLObject/SQLBase
from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
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
        # FIXME: There should be a better way to look up a schema
        #  item given its value
        return [br for br in dbschema.BranchRelationships
                if br == self.label][0]
        
    def nameSelector(self, sourcepackage=None, selected=None):
        html = '<select name="binarypackagename">\n'
        if not sourcepackage: binpkgs = self._table.select()
        else: binpkgs = self._table.select("""
                binarypackagename.id = binarypackage.binarypackagename AND
                binarypackage.build = build.id AND
                build.sourcepackagerelease = sourcepackagerelease.id AND
                sourcepackagerelease.sourcepackage = %s""" % str(sourcepackage),
                clauseTables = [ 'binarypackagename', 'binarypackage',
                'build', 'sourcepackagerelease'])
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
