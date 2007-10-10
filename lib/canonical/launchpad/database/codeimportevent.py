# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes related to and including CodeImportEvent."""

__metaclass__ = type
__all__ = [
    'CodeImportEvent',
    'CodeImportEventSet',
    ]


from sqlobject import StringCol, ForeignKey

from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeImportEventDataType, CodeImportEventType, ICodeImportEvent,
    ICodeImportEventSet, RevisionControlSystems)


class CodeImportEvent(SQLBase):
    """See `ICodeImportEvent`."""

    implements(ICodeImportEvent)
    _table = 'CodeImportEvent'

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    event_type = EnumCol(
        dbName='entry_type', enum=CodeImportEventType, notNull=True)
    code_import = ForeignKey(
        dbName='code_import', foreignKey='CodeImport', default=None)
    person = ForeignKey(
        dbName='person', foreignKey='Person', default=None)
    machine = ForeignKey(
        dbName='machine', foreignKey='CodeImportMachine', default=None)

    def items(self):
        """See `ICodeImportEvent`."""
        return [(data.data_type, data.data_value)
                for data in _CodeImportEventData.selectBy(event=self)]


class _CodeImportEventData(SQLBase):
    """Additional data associated to a CodeImportEvent.

    This class is for internal use only. This data should be created by
    CodeImportEventSet event creation methods, and should be accessed by
    CodeImport methods.
    """

    _table = 'CodeImportEventData'

    event = ForeignKey(dbName='event', foreignKey='CodeImportEvent')
    data_type = EnumCol(enum=CodeImportEventDataType, notNull=True)
    data_value = StringCol()


class CodeImportEventSet:
    """See `ICodeImportEventSet`."""

    implements(ICodeImportEventSet)

    def getAll(self):
        """See `ICodeImportEventSet`."""
        return CodeImportEvent.select(orderBy=['date_created', 'id'])

    def getEventsForCodeImport(self, code_import):
        """See `ICodeImportEventSet`."""
        return CodeImportEvent.selectBy(code_import=code_import).orderBy(
            ['date_created', 'id'])

    # All CodeImportEvent creation methods should assert arguments against
    # None. The database schema and the interface allow all foreign keys to be
    # NULL, but specific event types should be created with specific non-NULL
    # values. We want to fail when the client code is buggy and passes None
    # where a real object is expected.

    def newCreate(self, code_import, person):
        """See `ICodeImportEventSet`."""
        assert code_import is not None
        assert person is not None
        event = CodeImportEvent(
            event_type=CodeImportEventType.CREATE,
            code_import=code_import, person=person)
        self._recordSnapshot(event, code_import)
        return event

    def _recordSnapshot(self, event, code_import):
        """Record a snapshot of the code import in the event data."""
        self._recordItems(event, self._iterItemsForSnapshot(code_import))

    def _recordItems(self, event, items):
        """Record the specified event data into the database."""
        for key, value in items:
            data_type = getattr(CodeImportEventDataType, key)
            _CodeImportEventData(
                event=event, data_type=data_type, data_value=value)

    def _iterItemsForSnapshot(self, code_import):
        """Yield key-value tuples to save a snapshot of the code import."""
        yield 'CODE_IMPORT', str(code_import.id)
        yield 'REVIEW_STATUS', code_import.review_status.name
        yield 'OWNER', str(code_import.owner.id)
        yield 'UPDATE_INTERVAL', self._getNullableValue(
            code_import.update_interval)
        yield 'ASSIGNEE', self._getNullableValue(
            code_import.assignee, use_id=True)
        for detail in self._iterSourceDetails(code_import):
            yield detail

    def _getNullableValue(self, value, use_id=False):
        """Return the string value for a nullable value.

        :param value: The value to represent as a string.
        :param use_id: Return the id of the object instead of the object, such
            as for a foreign key.
        """
        if value is None:
            return None
        elif use_id:
            return str(value.id)
        else:
            return str(value)

    def _iterSourceDetails(self, code_import):
        """Yield key-value tuples describing the source of the import."""
        if code_import.rcs_type == RevisionControlSystems.SVN:
            yield 'SVN_BRANCH_URL', code_import.svn_branch_url
        elif code_import.rcs_type == RevisionControlSystems.CVS:
            yield 'CVS_ROOT', code_import.cvs_root
            yield 'CVS_MODULE', code_import.cvs_module
        else:
            raise AssertionError(
                "Unknown RCS type: %s" % (code_import.rcs_type,))




