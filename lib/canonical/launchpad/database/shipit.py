# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['StandardShipItRequest', 'StandardShipItRequestSet',
           'ShippingRequest', 'ShippingRequestSet', 'RequestedCDs',
           'Shipment', 'ShipmentSet', 'ShippingRun', 'ShippingRunSet']

import random

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLObjectNotFound, IntCol, AND)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.lp.dbschema import (
        ShipItDistroRelease, ShipItArchitecture, ShipItFlavour, EnumCol,
        ShippingService)
from canonical.launchpad.interfaces import (
        IStandardShipItRequest, IStandardShipItRequestSet, IShippingRequest,
        IRequestedCDs, IShippingRequestSet, ShippingRequestStatus,
        ILaunchpadCelebrities, IShipment, IShippingRun, IShippingRunSet,
        IShipmentSet, ShippingRequestPriority)


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
    _defaultOrder = ['daterequested', 'id']

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
               omit_cancelled=True, orderBy=ShippingRequest._defaultOrder):
        """See IShippingRequestSet"""
        queries = []
        clauseTables = []
        if request_type != 'any':
            type_based_query = self._getTypeBasedQuery(
                request_type, standard_type=standard_type)
            queries.append('ShippingRequest.id IN (%s)' % type_based_query)

        if recipient_text is not None:
            recipient_text = recipient_text.lower()
            queries.append("""
                ((Person.id = ShippingRequest.recipient AND
                  Person.fti @@ ftq(%s))
                 OR (EmailAddress.person = ShippingRequest.recipient AND
                     lower(EmailAddress.email) LIKE %s)
                 OR (ShippingRequest.fti @@ ftq(%s))
                )
                """ % sqlvalues(recipient_text, recipient_text + '%%',
                                recipient_text))
            clauseTables = ['Person', 'EmailAddress']

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
        return ShippingRequest.select(
            query, distinct=True, clauseTables=clauseTables, orderBy=orderBy)

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

