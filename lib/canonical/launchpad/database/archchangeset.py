# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Changeset', 'RevisionMapper']

from canonical.database.sqlbase import quote, SQLBase
from canonical.database.constants import UTC_NOW
from sqlobject import StringCol, ForeignKey, IntCol
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered

from canonical.launchpad.database.archbranch import VersionMapper


class Changeset(SQLBase):
    """A changeset."""

    _table = 'changeset'
    _columns = [
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
                   notNull=True),
        UtcDateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('logmessage', dbName='logmessage', notNull=True),
        ForeignKey(name='archID', foreignKey='ArchUserID', dbName='archID',
                   default=None),
        ForeignKey(name='gpgkey', foreignKey='GPGKey', dbName='gpgkey',
                   default=None),
    ]

    def getPackageName(self):
        """Arch package name for the changeset."""
        packagename = self.branch.getPackageName()
        packagename += "--" + self.name
        return packagename

class RevisionMapper:
    """Map revisions in and out of the db."""

    def findByName(self, name):
        from pybaz import NameParser
        from canonical.arch import broker
        if self.exists(name):
            parser = NameParser(name)
            archive = broker.Archive(parser.get_archive())
            category = broker.Category(parser.get_category(), archive)
            branch = broker.Branch(parser.get_branch(), category)
            version = broker.Version(parser.get_version(), branch)
            return broker.Revision(parser.get_revision(), version)

    def insert(self, revision):
        """Insert a revision into the database."""
        if self.exists(revision):
            raise RevisionAlreadyRegistered(revision.fullname)
        #FIXME: ask Mark if we should include correct date?
        revision.set_changeset(Changeset(
            branch=VersionMapper()._getDBBranchId(revision.version),
            datecreated=UTC_NOW,
            name=revision.name,
            logmessage='',
            ))

    def changeset(self, revision):
        """Get a cset object."""
        mapper = VersionMapper()
        version_id = mapper._getDBBranchId(revision.version)
        return Changeset.selectOneBy(name=revision.name, branchID=version_id)

    def update_log(self, revision, log):
        """Update a revision's log in the database."""
        log = quote(log)
        revision.log_message = log

    def exists(self, revision):
        """Does revision exist in the archice?"""
        mapper = VersionMapper()
        version_id = mapper._getDBBranchId(revision.version)
        return bool(
            Changeset.selectBy(name=revision.name, branchID=version_id)
            )

    def _getId(self, revision):
        """Get the id of a revision."""
        branch_id = VersionMapper()._getDBBranchId(revision.version)
        changeset = Changeset.selectOneBy(name=revision.name,
                                          branchID=branch_id)
        if changeset is None:
            raise RevisionNotRegistered(revision.fullname)
        else:
            return changeset.id
