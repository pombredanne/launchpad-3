# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['StandardShipItRequest', 'StandardShipItRequestSet',
           'ShippingRequest', 'ShippingRequestSet', 'RequestedCDs']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLObjectNotFound, IntCol, AND)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.lp.dbschema import (
        ShipItDistroRelease, ShipItArchitecture, ShipItFlavour, EnumCol)
from canonical.launchpad.interfaces import (
        IStandardShipItRequest, IStandardShipItRequestSet, IShippingRequest,
        IRequestedCDs, IShippingRequestSet, ShippingRequestStatus)


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
    _defaultOrder = 'id'

    recipient = ForeignKey(dbName='recipient', foreignKey='Person',
                           notNull=True)

    shipment = ForeignKey(dbName='shipment', foreignKey='Shipment',
                          default=None)

    daterequested = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    shockandawe = ForeignKey(dbName='shockandawe', foreignKey='ShockAndAwe',
                             default=None)

    # None here means that it's pending approval.
    approved = IntCol(default=None)
    whoapproved = ForeignKey(dbName='whoapproved', foreignKey='Person',
                             default=None)

    cancelled = BoolCol(notNull=True, default=False)
    whocancelled = ForeignKey(dbName='whocancelled', foreignKey='Person',
                             default=None)

    reason = StringCol(default=None)

    @property
    def totalCDs(self):
        """See IShippingRequest"""
        return self.quantityx86 + self.quantityamd64 + self.quantityppc

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

    # XXX: All the quantity* properties need to be refactored to share more
    # code. -- GuilhermeSalgado, 2005-09-02
#     def _get_quantityx86(self):
#         return self._getRequestedCDsByArch(ShipItArchitecture.X86).quantity
# 
#     def _set_quantityx86(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.X86)
#         request.quantity = value
#     quantityx86 = property(_get_quantityx86, _set_quantityx86)
# 
#     def _get_quantityx86approved(self):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.X86)
#         return request.quantityapproved
# 
#     def _set_quantityx86approved(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.X86)
#         request.quantityapproved = value
#     quantityx86approved = property(_get_quantityx86approved,
#                                    _set_quantityx86approved)
# 
#     def _get_quantityamd64(self):
#         return self._getRequestedCDsByArch(ShipItArchitecture.AMD64).quantity
# 
#     def _set_quantityamd64(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.AMD64)
#         request.quantity = value
#     quantityamd64 = property(_get_quantityamd64, _set_quantityamd64)
# 
#     def _get_quantityamd64approved(self):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.AMD64)
#         return request.quantityapproved
# 
#     def _set_quantityamd64approved(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.AMD64)
#         request.quantityapproved = value
#     quantityamd64approved = property(_get_quantityamd64approved,
#                                      _set_quantityamd64approved)
# 
#     def _get_quantityppc(self):
#         return self._getRequestedCDsByArch(ShipItArchitecture.PPC).quantity
# 
#     def _set_quantityppc(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.PPC)
#         request.quantity = value
#     quantityppc = property(_get_quantityppc, _set_quantityppc)
# 
#     def _get_quantityppcapproved(self):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.PPC)
#         return request.quantityapproved
# 
#     def _set_quantityppcapproved(self, value):
#         request = self._getRequestedCDsByArch(ShipItArchitecture.PPC)
#         request.quantityapproved = value
#     quantityppcapproved = property(_get_quantityppcapproved,
#                                    _set_quantityppcapproved)

    def isStandardRequest(self):
        """See IShippingRequest"""
        return (getUtility(IStandardShipItRequestSet).getByNumbersOfCDs(
                    self.quantityx86, self.quantityamd64, self.quantityppc)
                is not None)

    def clearApproval(self):
        """See IShippingRequest"""
        assert self.approved
        self.approved = None
        self.whoapproved = None

    def approve(self, whoapproved=None):
        """See IShippingRequest"""
        assert not self.cancelled
        self.approved = True
        self.whoapproved = whoapproved
        self.quantityx86approved = self.quantityx86
        self.quantityamd64approved = self.quantityamd64
        self.quantityppcapproved = self.quantityppc

    def cancel(self, whocancelled):
        """See IShippingRequest"""
        assert not self.cancelled
        self.approved = None
        self.whoapproved = None
        self.cancelled = True
        self.whocancelled = whocancelled
        self.quantityx86approved = None
        self.quantityamd64approved = None
        self.quantityppcapproved = None

    def reactivate(self):
        """See IShippingRequest"""
        assert self.cancelled
        self.cancelled = False
        self.whocancelled = None


class ShippingRequestSet:
    """See IShippingRequestSet"""

    implements(IShippingRequestSet)

    def get(self, id, default=None):
        """See IShippingRequestSet"""
        try:
            return ShippingRequest.get(id)
        except SQLObjectNotFound:
            return default

    def new(self, recipient, quantityx86, quantityamd64, quantityppc,
            reason=None, shockandawe=None):
        """See IShippingRequestSet"""
        assert recipient.currentShipItRequest() is None
        request = ShippingRequest(recipient=recipient, reason=reason,
                                  shockandawe=shockandawe)

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

    def searchCustomRequests(self, status=ShippingRequestStatus.ALL,
                             omit_cancelled=True):
        """See IShippingRequestSet"""
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
                  (ReqX86.quantity, ReqAMD64.quantity, ReqPPC.quantity) NOT IN
                  (SELECT quantityx86, quantityamd64, quantityppc FROM
                  StandardShipItRequest)
        """ % sqlvalues(arch.X86, arch.AMD64, arch.PPC)

        if status == ShippingRequestStatus.APPROVED:
            query += " AND ShippingRequest.approved IS TRUE"
        elif status == ShippingRequestStatus.UNAPPROVED:
            query += " AND ShippingRequest.approved IS NULL"
        else:
            # Okay, if you don't want any filtering I won't filter
            pass

        if omit_cancelled:
            query += " AND ShippingRequest.cancelled = FALSE"

        results = ShippingRequest._connection.queryAll(query)
        ids = ', '.join([str(id) for [id]in results])
        if not ids:
            # Doing a 'SELECT id FROM ShippingRequest WHERE id IN ()' will
            # fail, so we need to do this little hack
            return ShippingRequest.select('1 = 2')
        return ShippingRequest.select('id in (%s)' % ids)

    def searchStandardRequests(self, status=ShippingRequestStatus.ALL,
                               omit_cancelled=True, standard_type=None):
        """See IShippingRequestSet"""
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

        if standard_type is None:
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

        if status == ShippingRequestStatus.APPROVED:
            query += " AND ShippingRequest.approved IS NOT NULL"
        elif status == ShippingRequestStatus.UNAPPROVED:
            query += " AND ShippingRequest.approved IS NULL"

        if omit_cancelled:
            query += " AND ShippingRequest.cancelled = FALSE"

        results = ShippingRequest._connection.queryAll(query)
        ids = ', '.join([str(id) for [id]in results])
        if not ids:
            # Doing a 'SELECT id FROM ShippingRequest WHERE id IN ()' will
            # fail, so we need to do this little hack
            return ShippingRequest.select('1 = 2')
        return ShippingRequest.select('id in (%s)' % ids)




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
        except SQLObjectNotFound:
            return default

    def getByNumbersOfCDs(self, quantityx86, quantityamd64, quantityppc):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest.selectOneBy(quantityx86=quantityx86,
                                                 quantityamd64=quantityamd64,
                                                 quantityppc=quantityppc)

