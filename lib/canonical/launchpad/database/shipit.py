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
        IShipmentSet, ShippingRequestPriority, IShipItReport, IShipItReportSet,
        CURRENT_SHIPIT_DISTRO_RELEASE)
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
    def recipient_email(self):
        """See IShippingRequest"""
        return self.recipient.preferredemail.email

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
    def totalapprovedCDs(self):
        """See IShippingRequest"""
        total = 0
        for requested_cds in self.getAllRequestedCDs():
            total += requested_cds.quantityapproved
        return total

    @property
    def totalCDs(self):
        """See IShippingRequest"""
        total = 0
        for requested_cds in self.getAllRequestedCDs():
            total += requested_cds.quantity
        return total

    def getQuantitiesByFlavour(self, flavour):
        """See IShippingRequest"""
        return self.getRequestedCDsGroupedByFlavourAndArch()[flavour]

    def _getRequestedCDsByFlavourAndArch(self, flavour, arch):
        query = AND(RequestedCDs.q.requestID==self.id,
                    RequestedCDs.q.distrorelease==CURRENT_SHIPIT_DISTRO_RELEASE,
                    RequestedCDs.q.flavour==flavour,
                    RequestedCDs.q.architecture==arch)
        return RequestedCDs.selectOne(query)

    def getAllRequestedCDs(self):
        """See IShippingRequest"""
        return RequestedCDs.selectBy(requestID=self.id)

    def getRequestedCDsGroupedByFlavourAndArch(self):
        requested_cds = {}
        for flavour in ShipItFlavour.items:
            requested_arches = {}
            for arch in ShipItArchitecture.items:
                cds = self._getRequestedCDsByFlavourAndArch(flavour, arch)
                assert cds is not None
                requested_arches[arch] = cds
            requested_cds[flavour] = requested_arches
        return requested_cds

    def setQuantitiesBasedOnStandardRequest(self, request_type):
        """See IShippingRequestSet"""
        quantities = {
            request_type.flavour:
                {ShipItArchitecture.X86: request_type.quantityx86,
                 ShipItArchitecture.AMD64: request_type.quantityamd64,
                 ShipItArchitecture.PPC: request_type.quantityppc}
            }
        self.setQuantities(quantities)
        
    def setApprovedQuantities(self, quantities):
        """See IShippingRequestSet"""
        assert self.isApproved()
        self._setQuantities(quantities, only_approved=True)

    def setQuantities(self, quantities):
        """See IShippingRequestSet"""
        self._setQuantities(quantities)

    def _setQuantities(self, quantities, only_approved=False):
#         attrname = 'quantity'
#         if approved:
#             attrname = 'quantityapproved'
        for flavour, arches_and_quantities in quantities.items():
            for arch, quantity in arches_and_quantities.items():
                assert quantity >= 0
                requested_cds = self._getRequestedCDsByFlavourAndArch(
                    flavour, arch)
                if not only_approved:
                    setattr(requested_cds, 'quantity', quantity)
                setattr(requested_cds, 'quantityapproved', quantity)

    def highlightColour(self):
        """See IShippingRequest"""
        if self.highpriority:
            return "#ff6666"
        else:
            return None

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

    def approve(self, whoapproved=None):
        """See IShippingRequest"""
        assert not self.cancelled
        assert not self.isApproved()
        self.approved = True
        self.whoapproved = whoapproved

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

    def new(self, recipient, recipientdisplayname, country, city, addressline1,
            phone, addressline2=None, province=None, postcode=None,
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

        # Now we create RequestedCDs objects for all different flavours and
        # architectures so we don't need to bother about creating them later.
        for flavour in ShipItFlavour.items:
            for arch in ShipItArchitecture.items:
                RequestedCDs(request=request, flavour=flavour, 
                             architecture=arch, quantity=0)

        return request

    def getUnshippedRequests(self, priority):
        """See IShippingRequestSet"""
        query = ('ShippingRequest.cancelled IS FALSE AND '
                 'ShippingRequest.approved IS TRUE AND '
                 'ShippingRequest.id NOT IN (SELECT request FROM Shipment) ')
        if priority == ShippingRequestPriority.HIGH:
            query += 'AND ShippingRequest.highpriority IS TRUE'
        elif priority == ShippingRequestPriority.NORMAL:
            query += 'AND ShippingRequest.highpriority IS FALSE'
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
                (ShippingRequest.fti @@ ftq(%s) OR recipient IN 
                    (
                    SELECT Person.id FROM Person 
                        WHERE Person.fti @@ ftq(%s)
                    UNION
                    SELECT EmailAddress.person FROM EmailAddress
                        WHERE lower(EmailAddress.email) LIKE %s || '%%'
                    ))
                """ % (quote(recipient_text), quote(recipient_text),
                       quote_like(recipient_text)))

        if omit_cancelled:
            queries.append("ShippingRequest.cancelled IS FALSE")

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
                  ReqPPC.request = ShippingRequest.id AND
                  ReqX86.flavour = ReqAMD64.flavour AND
                  ReqPPC.flavour = ReqAMD64.flavour
        """ % sqlvalues(arch.X86, arch.AMD64, arch.PPC)

        if request_type == 'custom':
            if standard_type is not None:
                raise AssertionError(
                    'standard_type must be None if request_type is custom.')
            query += """
                AND ReqX86.quantity != 0 AND ReqAMD64.quantity != 0
                AND ReqPPC.quantity != 0
                AND (ReqX86.flavour, ReqX86.quantity, ReqAMD64.quantity,
                     ReqPPC.quantity)
                NOT IN (SELECT flavour, quantityx86, quantityamd64, quantityppc
                        FROM StandardShipItRequest)
                """
        elif request_type == 'standard' and standard_type is None:
            query += """
                AND (ReqX86.flavour, ReqX86.quantity, ReqAMD64.quantity,
                     ReqPPC.quantity)
                IN (SELECT flavour, quantityx86, quantityamd64, quantityppc
                    FROM StandardShipItRequest)
                """
        else:
            query += """
                AND ReqX86.flavour = %s
                AND ReqX86.quantity = %s
                AND ReqAMD64.quantity = %s
                AND ReqPPC.quantity = %s
                """ % sqlvalues(standard_type.flavour, 
                                standard_type.quantityx86,
                                standard_type.quantityamd64, 
                                standard_type.quantityppc)

        return query

    def _sumRequestedCDCount(self, quantities):
        """Sum the values of a dictionary mapping flavour and architectures 
        to quantities of requested CDs.

        This dictionary must be of the same format of the one returned by
        _getRequestedCDCount().
        """
        total = 0
        for flavour in quantities:
            for arch in quantities[flavour]:
                total += quantities[flavour][arch]
        return total

    def _getRequestedCDCount(self, country=None, approved=False):
        """Return the number of Requested CDs for each flavour and architecture.
        
        If country is not None, then consider only CDs requested by people on
        that country.
        
        If approved is True, then we return the number of CDs that were
        approved, which may differ from the number of requested CDs.
        """
        attr_to_sum_on = 'quantity'
        if approved:
            attr_to_sum_on = 'quantityapproved'
        quantities = {}
        for flavour in ShipItFlavour.items:
            quantities[flavour] = {}
            for arch in ShipItArchitecture.items:
                query_str = """
                    shippingrequest.id = shipment.request AND
                    shippingrequest.id = requestedcds.request AND
                    requestedcds.flavour = %s AND
                    requestedcds.architecture = %s""" % sqlvalues(flavour, arch)
                if country is not None:
                    query_str += (" AND shippingrequest.country = %s" 
                                  % sqlvalues(country.id))
                requests = ShippingRequest.select(
                    query_str, clauseTables=['RequestedCDs', 'Shipment'])
                quantities[flavour][arch] = requests.sum(attr_to_sum_on)
        return quantities

    def generateCountryBasedReport(self):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        header = [
            'Country', 'Shipped Ubuntu x86 CDs', 'Shipped Ubuntu AMD64 CDs',
            'Shipped Ubuntu PPC CDs', 'Shipped KUbuntu x86 CDs',
            'Shipped KUbuntu AMD64 CDs', 'Shipped KUbuntu PPC CDs',
            'Shipped EdUbuntu x86 CDs', 'Shipped EdUbuntu AMD64 CDs',
            'Shipped EdUbuntu PPC CDs', 'Normal-prio shipments',
            'High-prio shipments', 'Average request size',
            'Percentage of requested CDs that were approved',
            'Percentage of total shipped CDs', 'Continent']
        csv_writer.writerow(header)
        all_shipped_cds = self._sumRequestedCDCount(
            self._getRequestedCDCount(approved=True))
        ubuntu = ShipItFlavour.UBUNTU
        kubuntu = ShipItFlavour.KUBUNTU
        edubuntu = ShipItFlavour.EDUBUNTU
        x86 = ShipItArchitecture.X86
        amd64 = ShipItArchitecture.AMD64
        ppc = ShipItArchitecture.PPC
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

            high_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority IS TRUE",
                clauseTables=clauseTables)
            high_prio_count = intOrZero(high_prio_orders.count())

            normal_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority IS FALSE",
                clauseTables=clauseTables)
            normal_prio_count = intOrZero(normal_prio_orders.count())

            shipped_cds = self._sumRequestedCDCount(shipped_cds_per_arch)
            requested_cds = self._sumRequestedCDCount(
                self._getRequestedCDCount(country=country, approved=False))
            average_request_size = shipped_cds / total_shipped_requests
            percentage_of_approved = float(shipped_cds) / float(requested_cds)
            percentage_of_total = float(shipped_cds) / float(all_shipped_cds)

            # Need to encode strings that may have non-ASCII chars into
            # unicode because we're using StringIO.
            country_name = country.name.encode('utf-8')
            continent_name = country.continent.name.encode('utf-8')
            row = [country_name,
                   shipped_cds_per_arch[ubuntu][x86],
                   shipped_cds_per_arch[ubuntu][amd64],
                   shipped_cds_per_arch[ubuntu][ppc],
                   shipped_cds_per_arch[kubuntu][x86],
                   shipped_cds_per_arch[kubuntu][amd64],
                   shipped_cds_per_arch[kubuntu][ppc],
                   shipped_cds_per_arch[edubuntu][x86],
                   shipped_cds_per_arch[edubuntu][amd64],
                   shipped_cds_per_arch[edubuntu][ppc],
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
        header = ['Year', 'Week number', 'Requests', 
                  'Ubuntu Requested X86 CDs',
                  'Ubuntu Requested AMD64 CDs', 
                  'Ubuntu Requested PPC CDs',
                  'KUbuntu Requested X86 CDs',
                  'KUbuntu Requested AMD64 CDs', 
                  'KUbuntu Requested PPC CDs',
                  'EdUbuntu Requested X86 CDs',
                  'EdUbuntu Requested AMD64 CDs', 
                  'EdUbuntu Requested PPC CDs']
        csv_writer.writerow(header)

        replacements = {'x86': ShipItArchitecture.X86, 
                        'amd64': ShipItArchitecture.AMD64, 
                        'ppc': ShipItArchitecture.PPC,
                        'ubuntu': ShipItFlavour.UBUNTU,
                        'kubuntu': ShipItFlavour.KUBUNTU,
                        'edubuntu': ShipItFlavour.EDUBUNTU}

        base_query = """
            SELECT 
              COUNT(shippingrequest.id), 
              -- Ubuntu requested CDs
              SUM(r1.quantity),
              SUM(r2.quantity), 
              SUM(r3.quantity),

              -- KUbuntu requested CDs
              SUM(r4.quantity),
              SUM(r5.quantity), 
              SUM(r6.quantity),

              -- EdUbuntu requested CDs
              SUM(r7.quantity),
              SUM(r8.quantity), 
              SUM(r9.quantity)
            FROM 
              shippingrequest, 
              -- Ubuntu requested CDs
              requestedcds AS r1, 
              requestedcds AS r2,
              requestedcds AS r3,

              -- KUbuntu requested CDs
              requestedcds AS r4, 
              requestedcds AS r5,
              requestedcds AS r6,

              -- EdUbuntu requested CDs
              requestedcds AS r7, 
              requestedcds AS r8,
              requestedcds AS r9 
            WHERE 
              r1.request = r2.request AND 
              r2.request = r3.request AND 
              r3.request = r4.request AND
              r4.request = r5.request AND 
              r5.request = r6.request AND 
              r6.request = r7.request AND
              r7.request = r8.request AND 
              r8.request = r9.request AND 
              r9.request = shippingrequest.id AND
              shippingrequest.cancelled = FALSE AND

              -- Ubuntu requested CDs
              r1.architecture = %(x86)s AND
              r2.architecture = %(amd64)s AND
              r3.architecture = %(ppc)s AND
              r1.flavour = r2.flavour AND
              r2.flavour = r3.flavour AND
              r3.flavour = %(ubuntu)s AND

              -- KUbuntu requested CDs
              r4.architecture = %(x86)s AND
              r5.architecture = %(amd64)s AND
              r6.architecture = %(ppc)s AND
              r4.flavour = r5.flavour AND
              r5.flavour = r6.flavour AND
              r6.flavour = %(kubuntu)s AND

              -- EdUbuntu requested CDs
              r7.architecture = %(x86)s AND
              r8.architecture = %(amd64)s AND
              r9.architecture = %(ppc)s AND
              r7.flavour = r8.flavour AND
              r8.flavour = r9.flavour AND
              r9.flavour = %(edubuntu)s
            """ % sqlvalues(**replacements)

        cur = cursor()
        for monday_date in make_mondays_between(start_date, end_date):
            date_filter = (
                " AND shippingrequest.daterequested BETWEEN %s AND %s"
                % sqlvalues(monday_date, monday_date + timedelta(days=7)))
            query_str = base_query + date_filter
            cur.execute(query_str)
            #requests, x86cds, amdcds, ppccds = cur.fetchone()
            year, weeknum, weekday = monday_date.isocalendar()
            row = [year, weeknum]
            row.extend(cur.fetchone())
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

    request = ForeignKey(
        dbName='request', foreignKey='ShippingRequest', notNull=True)

    distrorelease = EnumCol(
        schema=ShipItDistroRelease, notNull=True,
        default=CURRENT_SHIPIT_DISTRO_RELEASE)
    architecture = EnumCol(schema=ShipItArchitecture, notNull=True)
    flavour = EnumCol(schema=ShipItFlavour, notNull=True)

    @property
    def description(self):
        return "%d %s CDs for %s" % (
                self.quantity, self.flavour.title, self.architecture.title)


class StandardShipItRequest(SQLBase):
    """See IStandardShipItRequest"""

    implements(IStandardShipItRequest)
    _table = 'StandardShipItRequest'

    quantityx86 = IntCol(notNull=True)
    quantityppc = IntCol(notNull=True)
    quantityamd64 = IntCol(notNull=True)
    isdefault = BoolCol(notNull=True, default=False)
    flavour = EnumCol(schema=ShipItFlavour, notNull=True)

    @property
    def description_without_flavour(self):
        """See IStandardShipItRequest"""
        description = "%d CDs" % self.totalCDs
        return "%s (%s)" % (description, self._detailed_description())

    @property
    def description(self):
        """See IStandardShipItRequest"""
        description = "%d %s CDs" % (self.totalCDs, self.flavour.title)
        return "%s (%s)" % (description, self._detailed_description())

    def _detailed_description(self):
        detailed = []
        if self.quantityx86:
            detailed.append('%d for %s' % 
                            (self.quantityx86, ShipItArchitecture.X86.title))
        if self.quantityamd64:
            detailed.append('%d for %s' % 
                            (self.quantityamd64, 
                             ShipItArchitecture.AMD64.title))
        if self.quantityppc:
            detailed.append('%d for %s' % 
                            (self.quantityppc, ShipItArchitecture.PPC.title))
        return ", ".join(detailed)

    @property
    def totalCDs(self):
        """See IStandardShipItRequest"""
        return self.quantityx86 + self.quantityppc + self.quantityamd64


class StandardShipItRequestSet:
    """See IStandardShipItRequestSet"""

    implements(IStandardShipItRequestSet)

    def new(self, flavour, quantityx86, quantityamd64, quantityppc, description,
            isdefault):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest(flavour=flavour, quantityx86=quantityx86,
                quantityppc=quantityppc, quantityamd64=quantityamd64,
                description=description, isdefault=isdefault)

    def getAll(self):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.select()

    def getByFlavour(self, flavour):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.selectBy(flavour=flavour)

    def getAllGroupedByFlavour(self):
        """See IStandardShipItRequestSet"""
        standard_requests = {}
        for flavour in ShipItFlavour.items:
            standard_requests[flavour] = self.getByFlavour(flavour)
        return standard_requests

    def get(self, id, default=None):
        """See IStandardShipItRequestSet"""
        try:
            return StandardShipItRequest.get(id)
        except (SQLObjectNotFound, ValueError):
            return default

    def getByNumbersOfCDs(
        self, flavour, quantityx86, quantityamd64, quantityppc):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.selectOneBy(
            flavour=flavour, quantityx86=quantityx86,
            quantityamd64=quantityamd64, quantityppc=quantityppc)

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

    def exportToCSVFile(self):
        """See IShippingRun"""
        file_fields = (('recordnr', 'id'),
                       ('Ship to company', 'organization'),
                       ('Ship to name', 'recipientdisplayname'),
                       ('Ship to addr1', 'addressline1'),
                       ('Ship to addr2', 'addressline2'),
                       ('Ship to city', 'city'),
                       ('Ship to county', 'province'),
                       ('Ship to zip', 'postcode'),
                       ('Ship to country', 'countrycode'),
                       ('Ship to phone', 'phone'),
                       ('Ship to email address', 'recipient_email'))

        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        row = [label for label, attr in file_fields]
        # The values for these fields we can't get using getattr(), so we have
        # to set them manually.
        extra_fields = ['ship Ubuntu quantity PC',
                        'ship Ubuntu quantity 64-bit PC',
                        'ship Ubuntu quantity Mac', 
                        'ship KUbuntu quantity PC',
                        'ship KUbuntu quantity 64-bit PC',
                        'ship KUbuntu quantity Mac',
                        'ship EdUbuntu quantity PC',
                        'ship EdUbuntu quantity 64-bit PC',
                        'ship EdUbuntu quantity Mac',
                        'token', 'Ship via', 'display']
        row.extend(extra_fields)
        csv_writer.writerow(row)

        ubuntu = ShipItFlavour.UBUNTU
        kubuntu = ShipItFlavour.KUBUNTU
        edubuntu = ShipItFlavour.EDUBUNTU
        x86 = ShipItArchitecture.X86
        ppc = ShipItArchitecture.PPC
        amd64 = ShipItArchitecture.AMD64
        for request in self.requests:
            row = []
            for label, attr in file_fields:
                value = getattr(request, attr)
                if isinstance(value, (unicode, str)):
                    # Text fields can't have non-ASCII characters or commas.
                    # This is a restriction of the shipping company.
                    value = value.replace(',', ';')
                    value = value.encode('ASCII')
                row.append(value)

            requested_cds = request.getRequestedCDsGroupedByFlavourAndArch()
            # The order that the flavours and arches appear in the following
            # two for loops must match the order the headers appear in
            # extra_fields.
            for flavour in [ubuntu, kubuntu, edubuntu]:
                for arch in [x86, amd64, ppc]:
                    quantity = requested_cds[flavour][arch].quantityapproved
                    row.append(quantity)

            row.append(request.shipment.logintoken)
            row.append(request.shippingservice.title)
            # XXX: 'display' is some magic number that's used by the shipping
            # company. Need to figure out what's it for and use a better name.
            # -- Guilherme Salgado, 2005-10-04
            if request.totalapprovedCDs >= 100:
                display = 1
            else:
                display = 0
            row.append(display)
            csv_writer.writerow(row)

        return csv_file


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
