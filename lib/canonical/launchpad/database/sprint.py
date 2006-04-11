# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Sprint',
    'SprintSet',
    ]


from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, RelatedJoin)
from sqlobject.sqlbuilder import AND, IN, NOT

from canonical.launchpad.interfaces import ISprint, ISprintSet

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT 
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.database.sprintattendance import SprintAttendance
from canonical.launchpad.database.sprintspecification import (
    SprintSpecification)

from canonical.lp.dbschema import (
    SprintSpecificationStatus, SpecificationStatus, SpecificationFilter,
    SpecificationSort)


class Sprint(SQLBase):
    """See ISprint."""

    implements(ISprint)

    _defaultOrder = ['name']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    name = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    home_page = StringCol(notNull=False, default=None)
    address = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    time_zone = StringCol(notNull=True)
    time_starts = UtcDateTimeCol(notNull=True)
    time_ends = UtcDateTimeCol(notNull=True)

    # attributes

    # we want to use this with templates that can assume a displayname,
    # because in many ways a sprint behaves just like a project or a
    # product - it has specs
    @property
    def displayname(self):
        return self.title

    # useful joins
    attendees = RelatedJoin('Person',
        joinColumn='sprint', otherColumn='attendee',
        intermediateTable='SprintAttendance', orderBy='name')

    def specifications(self, sort=None, quantity=None, filter=None):
        """See IHasSpecifications."""

        # eliminate mutables
        if filter is None:
            filter = []

        # import here to avoid circular deps
        from canonical.launchpad.database.specification import Specification

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'status', 'name']
        elif sort == SpecificationSort.DATE:
            order = ['-datecreated', 'id']

        # figure out what set of specifications we are interested in. for
        # sprint, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - acceptance for sprint agenda.
        #  - informational.
        #
        base = """SprintSpecification.sprint = %d AND
                  SprintSpecification.specification = Specification.id
                  """ % self.id
        query = base

        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += ' AND Specification.informational IS TRUE'
        
        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # look for specs that have a particular SprintSpecification
        # status (proposed, accepted or declined)
        if SpecificationFilter.ACCEPTED in filter:
            query += ' AND SprintSpecification.status = %d' % (
                SprintSpecificationStatus.ACCEPTED.value)
        elif SpecificationFilter.PROPOSED in filter:
            query += ' AND SprintSpecification.status = %d' % (
                SprintSpecificationStatus.PROPOSED.value)
        elif SpecificationFilter.DECLINED in filter:
            query += ' AND SprintSpecification.status = %d' % (
                SprintSpecificationStatus.DECLINED.value)
        
        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base
        
        # now do the query, and remember to prejoin to people
        results = Specification.select(query, orderBy=order, limit=quantity,
            clauseTables=['SprintSpecification'])
        results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def specificationLinks(self, status=None):
        """See ISprint."""
        query = """SprintSpecification.specification = Specification.id AND
                   SprintSpecification.sprint = %s""" % sqlvalues(self.id)
        if status is not None:
            query += ' AND SprintSpecification.status=%s' % sqlvalues(status)
        results = SprintSpecification.select(query,
            clauseTables=['Specification'],
            orderBy=['-Specification.priority', 
                     'Specification.status',
                     'Specification.name'])
        results.prejoin(['specification'])
        return results

    def getSpecificationLink(self, speclink_id):
        """See ISprint.
        
        NB: we expose the horrible speclink.id because there is no unique
        way to refer to a specification outside of a product or distro
        context. Here we are a sprint that could cover many products and/or
        distros.
        """
        speclink = SprintSpecification.get(speclink_id)
        assert (speclink.sprint.id == self.id)
        return speclink

    # attendance
    def attend(self, person, time_starts, time_ends):
        """See ISprint."""
        # first see if a relevant attendance exists, and if so, update it
        for attendance in self.attendances:
            if attendance.attendee.id == person.id:
                attendance.time_starts = time_starts
                attendance.time_ends = time_ends
                return attendance
        # since no previous attendance existed, create a new one
        return SprintAttendance(sprint=self, attendee=person,
            time_starts=time_starts, time_ends=time_ends)

    def removeAttendance(self, person):
        """See ISprint."""
        for attendance in self.attendances:
            if attendance.attendee.id == person.id:
                attendance.destroySelf()
                return

    @property
    def attendances(self):
        ret = SprintAttendance.selectBy(sprintID=self.id)
        ret.prejoin(['attendee'])
        return sorted(ret, key=lambda a: a.attendee.name)

    # linking to specifications
    def linkSpecification(self, spec):
        """See ISprint."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                return speclink
        return SprintSpecification(sprint=self, specification=spec)

    def unlinkSpecification(self, spec):
        """See ISprint."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                SprintSpecification.delete(speclink.id)
                return speclink


class SprintSet:
    """The set of sprints."""

    implements(ISprintSet)

    def __init__(self):
        """See ISprintSet."""
        self.title = 'Sprints and meetings'

    def __getitem__(self, name):
        """See ISprintSet."""
        return Sprint.selectOneBy(name=name)

    def __iter__(self):
        """See ISprintSet."""
        return iter(Sprint.select(orderBy='-time_starts'))

    def new(self, owner, name, title, time_zone, time_starts, time_ends,
        summary=None, home_page=None):
        """See ISprintSet."""
        return Sprint(owner=owner, name=name, title=title,
            time_zone=time_zone, time_starts=time_starts,
            time_ends=time_ends, summary=summary, home_page=home_page)

