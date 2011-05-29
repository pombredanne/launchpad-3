# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'Sprint',
    'SprintSet',
    'HasSprintsMixin',
    ]


from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.locals import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    flush_database_updates,
    quote,
    SQLBase,
    )
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon,
    IHasLogo,
    IHasMugshot,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.blueprints.enums import (
    SpecificationFilter,
    SpecificationImplementationStatus,
    SpecificationSort,
    SprintSpecificationStatus,
    )
from lp.blueprints.interfaces.sprint import (
    ISprint,
    ISprintSet,
    )
from lp.blueprints.model.specification import HasSpecificationsMixin
from lp.blueprints.model.sprintattendance import SprintAttendance
from lp.blueprints.model.sprintspecification import SprintSpecification
from lp.registry.interfaces.person import (
    IPersonSet,
    validate_public_person,
    )
from lp.registry.model.hasdrivers import HasDriversMixin


class Sprint(SQLBase, HasDriversMixin, HasSpecificationsMixin):
    """See `ISprint`."""

    implements(ISprint, IHasLogo, IHasMugshot, IHasIcon)

    _defaultOrder = ['name']

    # db field names
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    name = StringCol(notNull=True, alternateID=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    driver = ForeignKey(
        dbName='driver', foreignKey='Person',
        storm_validator=validate_public_person)
    home_page = StringCol(notNull=False, default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
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

    @property
    def drivers(self):
        """See IHasDrivers."""
        if self.driver is not None:
            return [self.driver, self.owner]
        return [self.owner]

    @property
    def attendees(self):
        # Only really used in tests.
        return [a.attendee for a in self.attendances]

    def spec_filter_clause(self, filter=None):
        """Figure out the appropriate query for specifications on a sprint.

        We separate out the query generation from the normal
        specifications() method because we want to reuse this query in the
        specificationLinks() method.
        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a sprint is to show everything approved
            filter = [SpecificationFilter.ACCEPTED]

        # figure out what set of specifications we are interested in. for
        # sprint, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - acceptance for sprint agenda.
        #  - informational.
        #
        base = """SprintSpecification.sprint = %s AND
                  SprintSpecification.specification = Specification.id AND
                  (Specification.product IS NULL OR
                   Specification.product NOT IN
                    (SELECT Product.id FROM Product
                     WHERE Product.active IS FALSE))
                  """ % quote(self)
        query = base

        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
              quote(SpecificationImplementationStatus.INFORMATIONAL))

        # import here to avoid circular deps
        from lp.blueprints.model.specification import Specification

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness = Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # look for specs that have a particular SprintSpecification
        # status (proposed, accepted or declined)
        if SpecificationFilter.ACCEPTED in filter:
            query += ' AND SprintSpecification.status = %s' % (
                quote(SprintSpecificationStatus.ACCEPTED))
        elif SpecificationFilter.PROPOSED in filter:
            query += ' AND SprintSpecification.status = %s' % (
                quote(SprintSpecificationStatus.PROPOSED))
        elif SpecificationFilter.DECLINED in filter:
            query += ' AND SprintSpecification.status = %s' % (
                quote(SprintSpecificationStatus.DECLINED))

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        return query

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See IHasSpecifications."""

        query = self.spec_filter_clause(filter=filter)
        if filter == None:
            filter = []

        # import here to avoid circular deps
        from lp.blueprints.model.specification import Specification

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.definition_status',
                     'Specification.name']
        elif sort == SpecificationSort.DATE:
            # we need to establish if the listing will show specs that have
            # been decided only, or will include proposed specs.
            show_proposed = set([
                SpecificationFilter.ALL,
                SpecificationFilter.PROPOSED,
                ])
            if len(show_proposed.intersection(set(filter))) > 0:
                # we are showing proposed specs so use the date proposed
                # because not all specs will have a date decided.
                order = ['-SprintSpecification.date_created',
                         'Specification.id']
            else:
                # this will show only decided specs so use the date the spec
                # was accepted or declined for the sprint
                order = ['-SprintSpecification.date_decided',
                         '-SprintSpecification.date_created',
                         'Specification.id']

        results = Specification.select(query, orderBy=order, limit=quantity,
            clauseTables=['SprintSpecification'])
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def specificationLinks(self, sort=None, quantity=None, filter=None):
        """See `ISprint`."""

        query = self.spec_filter_clause(filter=filter)

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'status', 'name']
        elif sort == SpecificationSort.DATE:
            order = ['-datecreated', 'id']

        results = SprintSpecification.select(query,
            clauseTables=['Specification'], orderBy=order, limit=quantity)
        return results.prejoin(['specification'])

    def getSpecificationLink(self, speclink_id):
        """See `ISprint`.

        NB: we expose the horrible speclink.id because there is no unique
        way to refer to a specification outside of a product or distro
        context. Here we are a sprint that could cover many products and/or
        distros.
        """
        speclink = SprintSpecification.get(speclink_id)
        assert (speclink.sprint.id == self.id)
        return speclink

    def acceptSpecificationLinks(self, idlist, decider):
        """See `ISprint`."""
        for sprintspec in idlist:
            speclink = self.getSpecificationLink(sprintspec)
            speclink.acceptBy(decider)

        # we need to flush all the changes we have made to disk, then try
        # the query again to see if we have any specs remaining in this
        # queue
        flush_database_updates()

        return self.specifications(
                        filter=[SpecificationFilter.PROPOSED]).count()

    def declineSpecificationLinks(self, idlist, decider):
        """See `ISprint`."""
        for sprintspec in idlist:
            speclink = self.getSpecificationLink(sprintspec)
            speclink.declineBy(decider)

        # we need to flush all the changes we have made to disk, then try
        # the query again to see if we have any specs remaining in this
        # queue
        flush_database_updates()

        return self.specifications(
                        filter=[SpecificationFilter.PROPOSED]).count()

    # attendance
    def attend(self, person, time_starts, time_ends, is_physical):
        """See `ISprint`."""
        # First see if a relevant attendance exists, and if so, update it.
        attendance = Store.of(self).find(
            SprintAttendance,
            SprintAttendance.sprint == self,
            SprintAttendance.attendee == person).one()
        if attendance is None:
            # Since no previous attendance existed, create a new one.
            attendance = SprintAttendance(sprint=self, attendee=person)
        attendance.time_starts = time_starts
        attendance.time_ends = time_ends
        attendance.is_physical = is_physical
        return attendance

    def removeAttendance(self, person):
        """See `ISprint`."""
        Store.of(self).find(
            SprintAttendance,
            SprintAttendance.sprint == self,
            SprintAttendance.attendee == person).remove()

    @property
    def attendances(self):
        result = list(Store.of(self).find(
            SprintAttendance,
            SprintAttendance.sprint == self))
        people = [a.attendeeID for a in result]
        # In order to populate the person cache we need to materialize the
        # result set.  Listification should do.
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                people, need_validity=True))
        return sorted(result, key=lambda a: a.attendee.displayname.lower())

    # linking to specifications
    def linkSpecification(self, spec):
        """See `ISprint`."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                return speclink
        return SprintSpecification(sprint=self, specification=spec)

    def unlinkSpecification(self, spec):
        """See `ISprint`."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                SprintSpecification.delete(speclink.id)
                return speclink

    def isDriver(self, user):
        """See `ISprint`."""
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.owner) or
                user.inTeam(self.driver) or
                user.inTeam(admins))


class SprintSet:
    """The set of sprints."""

    implements(ISprintSet)

    def __init__(self):
        """See `ISprintSet`."""
        self.title = 'Sprints and meetings'

    def __getitem__(self, name):
        """See `ISprintSet`."""
        return Sprint.selectOneBy(name=name)

    def __iter__(self):
        """See `ISprintSet`."""
        return iter(Sprint.select("time_ends > 'NOW'", orderBy='time_starts'))

    @property
    def all(self):
        return Sprint.select(orderBy='-time_starts')

    def new(self, owner, name, title, time_zone, time_starts, time_ends,
            summary, address=None, driver=None, home_page=None,
            mugshot=None, logo=None, icon=None):
        """See `ISprintSet`."""
        return Sprint(owner=owner, name=name, title=title,
            time_zone=time_zone, time_starts=time_starts,
            time_ends=time_ends, summary=summary, driver=driver,
            home_page=home_page, mugshot=mugshot, icon=icon,
            logo=logo, address=address)


class HasSprintsMixin:
    """A mixin class implementing the common methods for any class
    implementing IHasSprints.
    """

    def _getBaseQueryAndClauseTablesForQueryingSprints(self):
        """Return the base SQL query and the clauseTables to be used when
        querying sprints related to this object.

        Subclasses must overwrite this method if it doesn't suit them.
        """
        query = """
            Specification.%s = %s
            AND Specification.id = SprintSpecification.specification
            AND SprintSpecification.sprint = Sprint.id
            AND SprintSpecification.status = %s
            """ % (self._table, self.id,
                   quote(SprintSpecificationStatus.ACCEPTED))
        return query, ['Specification', 'SprintSpecification']

    @property
    def sprints(self):
        """See IHasSprints."""
        query, tables = self._getBaseQueryAndClauseTablesForQueryingSprints()
        return Sprint.select(
            query, clauseTables=tables, orderBy='-time_starts', distinct=True)

    @property
    def coming_sprints(self):
        """See IHasSprints."""
        query, tables = self._getBaseQueryAndClauseTablesForQueryingSprints()
        query += " AND Sprint.time_ends > 'NOW'"
        return Sprint.select(
            query, clauseTables=tables, orderBy='time_starts',
            distinct=True, limit=5)

    @property
    def past_sprints(self):
        """See IHasSprints."""
        query, tables = self._getBaseQueryAndClauseTablesForQueryingSprints()
        query += " AND Sprint.time_ends <= 'NOW'"
        return Sprint.select(
            query, clauseTables=tables, orderBy='-time_starts',
            distinct=True)
