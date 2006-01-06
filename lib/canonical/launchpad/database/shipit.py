# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['StandardShipItRequest', 'StandardShipItRequestSet',
           'ShippingRequest', 'ShippingRequestSet', 'RequestedCDs',
           'Shipment', 'ShipmentSet', 'ShippingRun', 'ShippingRunSet',
           'ShipItReport', 'ShipItReportSet']

from StringIO import StringIO
import csv
from datetime import timedelta
import random

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLObjectNotFound, IntCol, AND)

from canonical.database.sqlbase import (
    SQLBase, sqlvalues, quote, quote_like, cursor)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.helpers import intOrZero
from canonical.launchpad.datetimeutils import make_mondays_between

from canonical.lp.dbschema import (
        ShipItDistroRelease, ShipItArchitecture, ShipItFlavour, EnumCol,
        ShippingService)
from canonical.launchpad.interfaces import (
        IStandardShipItRequest, IStandardShipItRequestSet, IShippingRequest,
        IRequestedCDs, IShippingRequestSet, ShippingRequestStatus,
        ILaunchpadCelebrities, IShipment, IShippingRun, IShippingRunSet,
        IShipmentSet, ShippingRequestPriority, IShipItReport, IShipItReportSet)
from canonical.launchpad.database.country import Country


class RequestedCDsDescriptor:
    """Property-like descriptor that gets and sets any attribute in a
    RequestedCDs object of a given architecture.
    """

    def __init__(self, architecture, attrname):
        self.attrname = attrname
        self.architecture = architecture

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        else:
            request = inst._getRequestedCDsByArch(self.architecture)
            return getattr(request, self.attrname)

    def __set__(self, inst, value):
        request = inst._getRequestedCDsByArch(self.architecture)
        setattr(request, self.attrname, value)


class ShippingRequest(SQLBase):
    """See IShippingRequest"""

    implements(IShippingRequest)
    sortingColumns = ['daterequested', 'id']
    _defaultOrder = sortingColumns

    recipient = ForeignKey(dbName='recipient', foreignKey='Person',
                           notNull=True)

    daterequested = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    shockandawe = ForeignKey(dbName='shockandawe', foreignKey='ShockAndAwe',
                             default=None)

    # None here means that it's pending approval.
    approved = BoolCol(notNull=False, default=None)
    whoapproved = ForeignKey(dbName='whoapproved', foreignKey='Person',
                             default=None)

    cancelled = BoolCol(notNull=True, default=False)
    whocancelled = ForeignKey(dbName='whocancelled', foreignKey='Person',
                             default=None)

    reason = StringCol(default=None)
    highpriority = BoolCol(notNull=True, default=False)

    city = StringCol(notNull=True)
    phone = StringCol(default=None)
    country = ForeignKey(dbName='country', foreignKey='Country', notNull=True)
    province = StringCol(default=None)
    postcode = StringCol(default=None)
    addressline1 = StringCol(notNull=True)
    addressline2 = StringCol(default=None)
    organization = StringCol(default=None)
    recipientdisplayname = StringCol(notNull=True)

    @property
    def shipment(self):
        """See IShippingRequest"""
        return Shipment.selectOneBy(requestID=self.id)

    @property
    def countrycode(self):
        """See IShippingRequest"""
        return self.country.iso3166code2

    @property
    def shippingservice(self):
        """See IShippingRequest"""
        if self.highpriority:
            return ShippingService.TNT
        else:
            return ShippingService.SPRING

    @property
    def totalCDs(self):
        """See IShippingRequest"""
        return self.quantityx86 + self.quantityamd64 + self.quantityppc

    @property
    def totalapprovedCDs(self):
        """See IShippingRequest"""
        # All approved quantities are None if the request is not approved.
        # This is to make them consistent with self.approved, which is None if
        # an order is not yet approved.
        if not self.isApproved():
            return 0
        return (self.quantityx86approved + self.quantityamd64approved +
                self.quantityppcapproved)

    def _getRequestedCDsByArch(self, arch):
        query = AND(RequestedCDs.q.requestID==self.id,
                    RequestedCDs.q.distrorelease==ShipItDistroRelease.BREEZY,
                    RequestedCDs.q.flavour==ShipItFlavour.UBUNTU,
                    RequestedCDs.q.architecture==arch)
        return RequestedCDs.selectOne(query)

    quantityx86approved = RequestedCDsDescriptor(
        ShipItArchitecture.X86, 'quantityapproved')
    quantityamd64approved = RequestedCDsDescriptor(
        ShipItArchitecture.AMD64, 'quantityapproved')
    quantityppcapproved = RequestedCDsDescriptor(
        ShipItArchitecture.PPC, 'quantityapproved')

    quantityx86 = RequestedCDsDescriptor(ShipItArchitecture.X86, 'quantity')
    quantityamd64 = RequestedCDsDescriptor(ShipItArchitecture.AMD64, 'quantity')
    quantityppc = RequestedCDsDescriptor(ShipItArchitecture.PPC, 'quantity')

    def highlightColour(self):
        """See IShippingRequest"""
        if self.highpriority:
            return "#ff6666"
        else:
            return None

    def isStandardRequest(self):
        """See IShippingRequest"""
        return (getUtility(IStandardShipItRequestSet).getByNumbersOfCDs(
                    self.quantityx86, self.quantityamd64, self.quantityppc)
                is not None)

    def isAwaitingApproval(self):
        """See IShippingRequest"""
        return self.approved is None

    def isApproved(self):
        """See IShippingRequest"""
        return self.approved

    def isDenied(self):
        """See IShippingRequest"""
        return self.approved == False

    def deny(self):
        """See IShippingRequest"""
        assert not self.isDenied()
        if self.isApproved():
            self.clearApproval()
        self.approved = False

    def clearApproval(self):
        """See IShippingRequest"""
        assert self.isApproved()
        self.approved = None
        self.whoapproved = None
        self.quantityx86approved = None
        self.quantityamd64approved = None
        self.quantityppcapproved = None

    def approve(self, quantityx86approved, quantityamd64approved,
                quantityppcapproved, whoapproved=None):
        """See IShippingRequest"""
        assert not self.cancelled
        assert not self.isApproved()
        self.approved = True
        self.whoapproved = whoapproved
        self.setApprovedTotals(
            quantityx86approved, quantityamd64approved, quantityppcapproved)

    def setApprovedTotals(self, quantityx86approved, quantityamd64approved,
                          quantityppcapproved):
        """See IShippingRequest"""
        assert self.isApproved()
        assert quantityx86approved >= 0
        assert quantityamd64approved >= 0
        assert quantityppcapproved >= 0
        self.quantityx86approved = quantityx86approved
        self.quantityamd64approved = quantityamd64approved
        self.quantityppcapproved = quantityppcapproved

    def cancel(self, whocancelled):
        """See IShippingRequest"""
        assert not self.cancelled
        if self.isApproved():
            self.clearApproval()
        self.cancelled = True
        self.whocancelled = whocancelled


class ShippingRequestSet:
    """See IShippingRequestSet"""

    implements(IShippingRequestSet)

    def get(self, id, default=None):
        """See IShippingRequestSet"""
        try:
            return ShippingRequest.get(id)
        except (SQLObjectNotFound, ValueError):
            return default

    def new(self, recipient, quantityx86, quantityamd64, quantityppc,
            recipientdisplayname, country, city, addressline1,
            addressline2=None, province=None, postcode=None, phone=None,
            organization=None, reason=None, shockandawe=None):
        """See IShippingRequestSet"""
        if not recipient.inTeam(getUtility(ILaunchpadCelebrities).shipit_admin):
            # Non shipit-admins can't place more than one order at a time
            # neither specify a name different than their own.
            assert recipient.currentShipItRequest() is None

        request = ShippingRequest(
            recipient=recipient, reason=reason, shockandawe=shockandawe,
            city=city, country=country, addressline1=addressline1,
            addressline2=addressline2, province=province, postcode=postcode,
            recipientdisplayname=recipientdisplayname,
            organization=organization, phone=phone)

        RequestedCDs(request=request, quantity=quantityx86,
                     distrorelease=ShipItDistroRelease.BREEZY,
                     architecture=ShipItArchitecture.X86)

        RequestedCDs(request=request, quantity=quantityamd64,
                     distrorelease=ShipItDistroRelease.BREEZY,
                     architecture=ShipItArchitecture.AMD64)

        RequestedCDs(request=request, quantity=quantityppc,
                     distrorelease=ShipItDistroRelease.BREEZY,
                     architecture=ShipItArchitecture.PPC)

        return request

    def getUnshippedRequests(self, priority):
        """See IShippingRequestSet"""
        query = ('ShippingRequest.cancelled = false AND '
                 'ShippingRequest.approved = true AND '
                 'ShippingRequest.id NOT IN (SELECT request from Shipment) ')
        if priority == ShippingRequestPriority.HIGH:
            query += 'AND ShippingRequest.highpriority = true'
        elif priority == ShippingRequestPriority.NORMAL:
            query += 'AND ShippingRequest.highpriority = false'
        else:
            # Nothing to filter, return all unshipped requests.
            pass
        return ShippingRequest.select(query)

    def getOldestPending(self):
        """See IShippingRequestSet"""
        q = AND(ShippingRequest.q.cancelled==False,
                ShippingRequest.q.approved==None)
        results = ShippingRequest.select(q, orderBy='daterequested', limit=1)
        try:
            return results[0]
        except IndexError:
            return None

    def search(self, request_type='any', standard_type=None,
               status=ShippingRequestStatus.ALL, recipient_text=None, 
               omit_cancelled=True, orderBy=ShippingRequest.sortingColumns):
        """See IShippingRequestSet"""
        queries = []
        clauseTables = []
        if request_type != 'any':
            type_based_query = self._getTypeBasedQuery(
                request_type, standard_type=standard_type)
            queries.append('ShippingRequest.id IN (%s)' % type_based_query)

        if recipient_text:
            recipient_text = recipient_text.lower()
            queries.append("""
                ShippingRequest.fti @@ ftq(%s) OR recipient IN 
                    (
                    SELECT Person.id FROM Person 
                        WHERE Person.fti @@ ftq(%s)
                    UNION
                    SELECT EmailAddress.person FROM EmailAddress
                        WHERE lower(EmailAddress.email) LIKE %s || '%%'
                    )
                """ % (quote(recipient_text), quote(recipient_text),
                       quote_like(recipient_text)))

        if omit_cancelled:
            queries.append("ShippingRequest.cancelled = FALSE")

        if status == ShippingRequestStatus.APPROVED:
            queries.append("ShippingRequest.approved IS TRUE")
        elif status == ShippingRequestStatus.PENDING:
            queries.append("ShippingRequest.approved IS NULL")
        elif status == ShippingRequestStatus.DENIED:
            queries.append("ShippingRequest.approved IS FALSE")
        else:
            # Okay, if you don't want any filtering I won't filter
            pass

        query = " AND ".join(queries)
        return ShippingRequest.select(query, distinct=True, orderBy=orderBy)

    def _getTypeBasedQuery(self, request_type, standard_type=None):
        """Return the SQL query to get all requests of a given type.

        The type must be either 'custom', 'standard' or 'any'.
        If the type is 'standard', then standard_type can be any of the
        StandardShipItRequests.
        """
        arch = ShipItArchitecture
        query = """
            SELECT ShippingRequest.id FROM ShippingRequest,
                                           RequestedCDs as ReqX86,
                                           RequestedCDs as ReqAMD64,
                                           RequestedCDs as ReqPPC
            WHERE ReqX86.architecture = %s AND
                  ReqAMD64.architecture = %s AND
                  ReqPPC.architecture = %s AND
                  ReqX86.request = ShippingRequest.id AND
                  ReqAMD64.request = ShippingRequest.id AND
                  ReqPPC.request = ShippingRequest.id
        """ % sqlvalues(arch.X86, arch.AMD64, arch.PPC)

        if request_type == 'custom':
            if standard_type is not None:
                raise AssertionError(
                    'standard_type must be None if request_type is custom.')
            query += """
                AND (ReqX86.quantity, ReqAMD64.quantity, ReqPPC.quantity)
                NOT IN (SELECT quantityx86, quantityamd64, quantityppc
                            FROM StandardShipItRequest)
                """
        elif request_type == 'standard' and standard_type is None:
            query += """
                AND (ReqX86.quantity, ReqAMD64.quantity, ReqPPC.quantity)
                IN (SELECT quantityx86, quantityamd64, quantityppc 
                        FROM StandardShipItRequest)
                """
        else:
            query += """
                AND ReqX86.quantity = %d AND
                ReqAMD64.quantity = %d AND
                ReqPPC.quantity = %d
                """ % (standard_type.quantityx86, standard_type.quantityamd64,
                       standard_type.quantityppc)

        return query

    def _getRequestedCDCount(self, country=None, approved=False):
        """Return the number of Requested CDs for each architecture.
        
        If country is not None, then consider only CDs requested by people on
        that country.
        
        If approved is True, then we return the number of CDs that were
        approved, which may differ from the number of requested CDs.
        """
        attr_to_sum_on = 'quantity'
        if approved:
            attr_to_sum_on = 'quantityapproved'
        quantities = {}
        for arch in ShipItArchitecture.items:
            query_str = """
                shippingrequest.id = shipment.request AND
                shippingrequest.id = requestedcds.request AND
                requestedcds.architecture = %s""" % sqlvalues(arch)
            if country is not None:
                query_str += (" AND shippingrequest.country = %s" 
                              % sqlvalues(country.id))
            requests = ShippingRequest.select(
                query_str, clauseTables=['RequestedCDs', 'Shipment'])
            quantities[arch] = intOrZero(requests.sum(attr_to_sum_on))
        return quantities

    def generateCountryBasedReport(self):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        header = ['Country', 'Shipped x86 CDs', 'Shipped AMD64 CDs',
                  'Shipped PPC CDs', 'Normal-prio shipments', 
                  'High-prio shipments', 'Average request size',
                  'Percentage of requested CDs that were approved',
                  'Percentage of total shipped CDs', 'Continent']
        csv_writer.writerow(header)
        all_shipped_cds = sum(self._getRequestedCDCount(approved=True).values())
        for country in Country.select():
            base_query = (
                "shippingrequest.country = %s AND "
                "shippingrequest.id = shipment.request" % sqlvalues(country.id))
            clauseTables = ['Shipment']
            total_shipped_requests = ShippingRequest.select(
                base_query, clauseTables=clauseTables).count()
            if not total_shipped_requests:
                continue
            
            shipped_cds_per_arch = self._getRequestedCDCount(
                country=country, approved=True)
            requested_cds_per_arch = self._getRequestedCDCount(
                country=country, approved=False)

            high_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority = TRUE",
                clauseTables=clauseTables)
            high_prio_count = intOrZero(high_prio_orders.count())

            normal_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority = FALSE",
                clauseTables=clauseTables)
            normal_prio_count = intOrZero(normal_prio_orders.count())

            shipped_cds = sum(shipped_cds_per_arch.values())
            requested_cds = sum(requested_cds_per_arch.values())
            average_request_size = shipped_cds / total_shipped_requests
            percentage_of_approved = float(shipped_cds) / float(requested_cds)
            percentage_of_total = float(shipped_cds) / float(all_shipped_cds)

            # Need to encode strings that may have non-ASCII chars into
            # unicode because we're using StringIO.
            country_name = country.name.encode('utf-8')
            continent_name = country.continent.name.encode('utf-8')
            row = [country_name, shipped_cds_per_arch[ShipItArchitecture.X86],
                   shipped_cds_per_arch[ShipItArchitecture.AMD64],
                   shipped_cds_per_arch[ShipItArchitecture.PPC],
                   normal_prio_count, high_prio_count,
                   average_request_size,
                   "%.2f%%" % (percentage_of_approved * 100),
                   "%.2f%%" % (percentage_of_total * 100),
                   continent_name]
            csv_writer.writerow(row)
        csv_file.seek(0)
        return csv_file

    def generateWeekBasedReport(self, start_date, end_date):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        header = ['Year', 'Week number', 'Requests', 'Requested X86 CDs',
                  'Requested AMD64 CDs', 'Requested PPC CDs']
        csv_writer.writerow(header)

        base_query = """
            SELECT 
              COUNT(shippingrequest.id), 
              SUM(r1.quantity),
              SUM(r2.quantity), 
              SUM(r3.quantity)
            FROM 
              shippingrequest, 
              requestedcds AS r1, 
              requestedcds AS r2,
              requestedcds AS r3 
            WHERE 
              r1.request = r2.request AND 
              r2.request = r3.request AND 
              r3.request = shippingrequest.id AND
              r1.architecture = %s AND
              r2.architecture = %s AND
              r3.architecture = %s AND
              shippingrequest.cancelled = FALSE
            """ % sqlvalues(ShipItArchitecture.X86, ShipItArchitecture.AMD64,
                            ShipItArchitecture.PPC)
        cur = cursor()
        for monday_date in make_mondays_between(start_date, end_date):
            date_filter = (
                " AND shippingrequest.daterequested BETWEEN %s AND %s"
                % sqlvalues(monday_date, monday_date + timedelta(days=7)))
            query_str = base_query + date_filter
            cur.execute(query_str)
            requests, x86cds, amdcds, ppccds = cur.fetchone()
            year, weeknum, weekday = monday_date.isocalendar()
            row = [year, weeknum, requests, x86cds, amdcds, ppccds]
            csv_writer.writerow(row)

        csv_file.seek(0)
        return csv_file

    def generateShipmentSizeBasedReport(self):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        header = ['Number of CDs', 'Number of Shipments']
        csv_writer.writerow(header)
        query_str = """
            SELECT shipment_size, COUNT(request_id) AS shipments
            FROM
            (
                SELECT shippingrequest.id AS request_id, 
                       SUM(quantityapproved) AS shipment_size
                FROM requestedcds, shippingrequest, shipment
                WHERE requestedcds.request = shippingrequest.id AND
                      shippingrequest.id = shipment.request
                GROUP BY shippingrequest.id
            )
            AS TMP GROUP BY shipment_size ORDER BY shipment_size
            """
        cur = cursor()
        cur.execute(query_str)
        for shipment_size, shipments in cur.fetchall():
            csv_writer.writerow([shipment_size, shipments])

        csv_file.seek(0)
        return csv_file


class RequestedCDs(SQLBase):
    """See IRequestedCDs"""

    implements(IRequestedCDs)

    quantity = IntCol(notNull=True)
    quantityapproved = IntCol(default=None)

    request = ForeignKey(dbName='request', foreignKey='ShippingRequest',
                         notNull=True)

    distrorelease = EnumCol(schema=ShipItDistroRelease, notNull=True)
    architecture = EnumCol(schema=ShipItArchitecture, notNull=True)
    flavour = EnumCol(schema=ShipItFlavour, notNull=True,
                      default=ShipItFlavour.UBUNTU)


class StandardShipItRequest(SQLBase):
    """See IStandardShipItRequest"""

    implements(IStandardShipItRequest)
    _table = 'StandardShipItRequest'

    quantityx86 = IntCol(notNull=True)
    quantityppc = IntCol(notNull=True)
    quantityamd64 = IntCol(notNull=True)
    description = StringCol(notNull=True, unique=True)
    isdefault = BoolCol(notNull=True, default=False)

    @property
    def totalCDs(self):
        """See IStandardShipItRequest"""
        return self.quantityx86 + self.quantityppc + self.quantityamd64


class StandardShipItRequestSet:
    """See IStandardShipItRequestSet"""

    implements(IStandardShipItRequestSet)

    def new(self, quantityx86, quantityamd64, quantityppc, description,
            isdefault):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest(quantityx86=quantityx86,
                quantityppc=quantityppc, quantityamd64=quantityamd64,
                description=description, isdefault=isdefault)

    def getAll(self):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.select()

    def get(self, id, default=None):
        """See IStandardShipItRequestSet"""
        try:
            return StandardShipItRequest.get(id)
        except (SQLObjectNotFound, ValueError):
            return default

    def getByNumbersOfCDs(self, quantityx86, quantityamd64, quantityppc):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.selectOneBy(quantityx86=quantityx86,
                                                 quantityamd64=quantityamd64,
                                                 quantityppc=quantityppc)

class Shipment(SQLBase):
    """See IShipment"""

    implements(IShipment)

    logintoken = StringCol(unique=True, notNull=True)
    dateshipped = UtcDateTimeCol(default=None)
    shippingservice = EnumCol(schema=ShippingService, notNull=True)
    shippingrun = ForeignKey(dbName='shippingrun', foreignKey='ShippingRun',
                             notNull=True)
    request = ForeignKey(dbName='request', foreignKey='ShippingRequest',
                         notNull=True, unique=True)
    trackingcode = StringCol(default=None)


class ShipmentSet:
    """See IShipmentSet"""

    implements(IShipmentSet)

    def new(self, request, shippingservice, shippingrun, trackingcode=None,
            dateshipped=None):
        """See IShipmentSet"""
        token = self._generateToken()
        while self.getByToken(token):
            token = self._generateToken()

        return Shipment(
            shippingservice=shippingservice, shippingrun=shippingrun,
            trackingcode=trackingcode, logintoken=token,
            dateshipped=dateshipped, request=request)

    def _generateToken(self):
        characters = '23456789bcdfghjkmnpqrstwxz'
        length = 10
        return ''.join([random.choice(characters) for count in range(length)])

    def getByToken(self, token):
        """See IShipmentSet"""
        return Shipment.selectOneBy(logintoken=token)


class ShippingRun(SQLBase):
    """See IShippingRun"""

    implements(IShippingRun)
    _defaultOrder = ['-datecreated', 'id']

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    csvfile = ForeignKey(
        dbName='csvfile', foreignKey='LibraryFileAlias', default=None)
    sentforshipping = BoolCol(notNull=True, default=False)

    @property
    def requests(self):
        query = ("ShippingRequest.id = Shipment.request AND "
                 "Shipment.shippingrun = ShippingRun.id AND "
                 "ShippingRun.id = %s" % sqlvalues(self.id))

        clausetables = ['ShippingRun', 'Shipment']
        return ShippingRequest.select(query, clauseTables=clausetables)


class ShippingRunSet:
    """See IShippingRunSet"""

    implements(IShippingRunSet)

    def new(self):
        """See IShippingRunSet"""
        return ShippingRun()

    def get(self, id):
        """See IShippingRunSet"""
        try:
            return ShippingRun.get(id)
        except SQLObjectNotFound:
            return None

    def getUnshipped(self):
        """See IShippingRunSet"""
        return ShippingRun.select(ShippingRun.q.sentforshipping==False)

    def getShipped(self):
        """See IShippingRunSet"""
        return ShippingRun.select(ShippingRun.q.sentforshipping==True)


class ShipItReport(SQLBase):
    """See IShipItReport"""

    implements(IShipItReport)
    _defaultOrder = ['-datecreated', 'id']
    _table = 'ShipItReport'

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    csvfile = ForeignKey(
        dbName='csvfile', foreignKey='LibraryFileAlias', notNull=True)


class ShipItReportSet:
    """See IShipItReportSet"""

    implements(IShipItReportSet)

    def new(self, csvfile):
        """See IShipItReportSet"""
        return ShipItReport(csvfile=csvfile)

    def getAll(self):
        """See IShipItReportSet"""
        return ShipItReport.select()
