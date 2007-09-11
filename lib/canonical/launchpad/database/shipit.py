# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['StandardShipItRequest', 'StandardShipItRequestSet',
           'ShippingRequest', 'ShippingRequestSet', 'RequestedCDs',
           'Shipment', 'ShipmentSet', 'ShippingRun', 'ShippingRunSet',
           'ShipItReport', 'ShipItReportSet',
           'MIN_KARMA_ENTRIES_TO_BE_TRUSTED_ON_SHIPIT']

from StringIO import StringIO
import csv
from datetime import datetime, timedelta
import itertools
import random
import re

from zope.interface import implements
from zope.component import getUtility

import pytz

from sqlobject.sqlbuilder import AND, SQLConstant
from sqlobject import ForeignKey, StringCol, BoolCol, SQLObjectNotFound, IntCol

from canonical.config import config
from canonical.uuid import generate_uuid

from canonical.database.sqlbase import (
    SQLBase, sqlvalues, quote, quote_like, cursor)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.helpers import intOrZero, get_email_template
from canonical.launchpad.datetimeutils import make_mondays_between
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.mail.sendmail import simple_sendmail

from canonical.launchpad.interfaces import (
    IStandardShipItRequest, IStandardShipItRequestSet, IShippingRequest,
    IRequestedCDs, IShippingRequestSet, ILaunchpadCelebrities, IShipment,
    IShippingRun, IShippingRunSet, IShipmentSet, ShippingRequestPriority,
    IShipItReport, IShipItReportSet, ShipItConstants, ILibraryFileAliasSet,
    SOFT_MAX_SHIPPINGRUN_SIZE, MAX_CDS_FOR_UNTRUSTED_PEOPLE,
    ShipItDistroSeries, ShipItArchitecture, ShipItFlavour,
    ShippingService, ShippingRequestStatus, ShippingRequestType)
from canonical.launchpad.database.country import Country


MIN_KARMA_ENTRIES_TO_BE_TRUSTED_ON_SHIPIT = 10


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

    type = EnumCol(enum=ShippingRequestType, default=None)
    status = EnumCol(
        enum=ShippingRequestStatus, notNull=True,
        default=ShippingRequestStatus.PENDING)
    whoapproved = ForeignKey(dbName='whoapproved', foreignKey='Person',
                             default=None)

    whocancelled = ForeignKey(dbName='whocancelled', foreignKey='Person',
                              default=None)

    reason = StringCol(default=None)
    highpriority = BoolCol(notNull=True, default=False)

    # This is maintained by a DB trigger, so it can be None here even though
    # the DB won't allow that.
    normalized_address = StringCol(default=None)
    city = StringCol(notNull=True)
    phone = StringCol(default=None)
    country = ForeignKey(dbName='country', foreignKey='Country', notNull=True)
    province = StringCol(default=None)
    postcode = StringCol(default=None)
    addressline1 = StringCol(notNull=True)
    addressline2 = StringCol(default=None)
    organization = StringCol(default=None)
    recipientdisplayname = StringCol(notNull=True)
    shipment = ForeignKey(
            dbName='shipment', foreignKey='Shipment',
            notNull=False, unique=True, default=None
            )

    @property
    def distroseries(self):
        """See IShippingRequest"""
        requested_cds = self.getAllRequestedCDs()
        assert requested_cds.count() > 0
        # We know that a request cannot contain CDs of more than one distro
        # series, so it's safe to get the first element here.
        return requested_cds[0].distroseries

    @property
    def recipient_email(self):
        """See IShippingRequest"""
        if self.recipient == getUtility(ILaunchpadCelebrities).shipit_admin:
            # The shipit_admin celebrity is the team to which we assign all
            # ShippingRequests made using the admin UI, but teams don't
            # necessarily have a preferredemail, so we have to special case it
            # here.
            return config.shipit.admins_email_address
        elif self.recipient.preferredemail is not None:
            return self.recipient.preferredemail.email
        else:
            return u'inactive account -- no email address'

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

    def getContainedFlavours(self):
        """See IShippingRequest"""
        flavours = set()
        for requested_cds in self.getAllRequestedCDs():
            flavours.add(requested_cds.flavour)
        return sorted(flavours)

    def getTotalApprovedCDs(self):
        """See IShippingRequest"""
        total = 0
        for requested_cds in self.getAllRequestedCDs():
            total += requested_cds.quantityapproved
        return total

    def getTotalCDs(self):
        """See IShippingRequest"""
        total = 0
        for requested_cds in self.getAllRequestedCDs():
            total += requested_cds.quantity
        return total

    def _getRequestedCDsByFlavourAndArch(self, flavour, arch):
        query = AND(RequestedCDs.q.requestID==self.id,
                    RequestedCDs.q.flavour==flavour,
                    RequestedCDs.q.architecture==arch)
        return RequestedCDs.selectOne(query)

    def getAllRequestedCDs(self):
        """See IShippingRequest"""
        return RequestedCDs.selectBy(request=self)

    def getRequestedCDsGroupedByFlavourAndArch(self):
        """See IShippingRequest"""
        requested_cds = {}
        for flavour in ShipItFlavour.items:
            requested_arches = {}
            for arch in ShipItArchitecture.items:
                cds = self._getRequestedCDsByFlavourAndArch(flavour, arch)
                requested_arches[arch] = cds

            requested_cds[flavour] = requested_arches

        return requested_cds

    def setRequestedQuantities(self, quantities):
        """See IShippingRequest"""
        assert not (self.isShipped() or self.isCancelled())
        self._setQuantities(quantities, set_approved=False, set_requested=True)

    def setApprovedQuantities(self, quantities):
        """See IShippingRequest"""
        assert self.isApproved()
        self._setQuantities(quantities, set_approved=True)

    def setQuantities(self, quantities,
                      distroseries=ShipItConstants.current_distroseries):
        """See IShippingRequest"""
        self._setQuantities(
            quantities, set_approved=True, set_requested=True,
            distroseries=distroseries)

    def _setQuantities(
            self, quantities, set_approved=False, set_requested=False,
            distroseries=ShipItConstants.current_distroseries):
        """Set the approved and/or requested quantities of this request.

        Also set this request's status to indicate whether it's a standard or
        custom one.
            :param quantities: A dictionary like the described in
                               IShippingRequestSet.setQuantities.
        """
        assert set_approved or set_requested
        standardrequestset = getUtility(IStandardShipItRequestSet)
        type = ShippingRequestType.STANDARD
        for flavour, arches_and_quantities in quantities.items():
            x86 = arches_and_quantities.get(ShipItArchitecture.X86, 0)
            amd64 = arches_and_quantities.get(ShipItArchitecture.AMD64, 0)
            ppc = arches_and_quantities.get(ShipItArchitecture.PPC, 0)
            standard_template = standardrequestset.getByNumbersOfCDs(
                flavour, x86, amd64, ppc)
            if standard_template is None:
                type = ShippingRequestType.CUSTOM
            for arch, quantity in arches_and_quantities.items():
                assert quantity >= 0
                requested_cds = self._getRequestedCDsByFlavourAndArch(
                    flavour, arch)
                if requested_cds is None:
                    requested_cds = RequestedCDs(
                        request=self, flavour=flavour, architecture=arch,
                        distroseries=distroseries)
                if set_approved:
                    requested_cds.quantityapproved = quantity
                if set_requested:
                    requested_cds.quantity = quantity
        self.type = type

    def containsCustomQuantitiesOfFlavour(self, flavour):
        """See IShippingRequest"""
        quantities = self.getQuantitiesOfFlavour(flavour)
        if not sum(quantities.values()):
            # This is an existing order that contains CDs of other
            # flavours only.
            return False
        else:
            standardrequestset = getUtility(IStandardShipItRequestSet)
            standard_request = standardrequestset.getByNumbersOfCDs(
                flavour, quantities[ShipItArchitecture.X86],
                quantities[ShipItArchitecture.AMD64],
                quantities[ShipItArchitecture.PPC])
            return standard_request is None

    def getQuantitiesOfFlavour(self, flavour):
        """See IShippingRequest"""
        requested_cds = self.getRequestedCDsGroupedByFlavourAndArch()[flavour]
        quantities = {}
        for arch in ShipItArchitecture.items:
            arch_requested_cds = requested_cds[arch]
            # Any of {x86,amd64,ppc}_requested_cds can be None here, so we use
            # a default value for getattr to make things easier.
            quantities[arch] = getattr(arch_requested_cds, 'quantity', 0)
        return quantities

    @property
    def status_desc(self):
        """See IShippingRequest"""
        if self.isAwaitingApproval():
            return ShippingRequestStatus.PENDING.title.lower()
        elif self.isApproved():
            return ShippingRequestStatus.APPROVED.title.lower()
        elif self.isShipped():
            return ("approved (sent for shipping on %s)"
                    % self.shipment.shippingrun.datecreated.date())
        elif self.isPendingSpecial():
            return ShippingRequestStatus.PENDINGSPECIAL.title.lower()
        elif self.isDuplicatedAddress():
            return ShippingRequestStatus.DUPLICATEDADDRESS.title.lower()
        elif self.isDenied():
            return ShippingRequestStatus.DENIED.title.lower()
        elif self.isCancelled():
            return "cancelled by %s" % self.whocancelled.displayname
        else:
            raise AssertionError("Invalid status: %s" % self.status)

    def isAwaitingApproval(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.PENDING

    def isApproved(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.APPROVED

    def isShipped(self):
        """See IShippingRequest"""
        if self.status == ShippingRequestStatus.SHIPPED:
            assert self.shipment is not None
            return True
        else:
            return False

    def isCancelled(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.CANCELLED

    def isDenied(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.DENIED

    def isDuplicatedAddress(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.DUPLICATEDADDRESS

    def isPendingSpecial(self):
        """See IShippingRequest"""
        return self.status == ShippingRequestStatus.PENDINGSPECIAL

    def canBeApproved(self):
        """See IShippingRequest"""
        statuses = [ShippingRequestStatus.DENIED,
                    ShippingRequestStatus.PENDINGSPECIAL,
                    ShippingRequestStatus.DUPLICATEDADDRESS,
                    ShippingRequestStatus.PENDING]
        return self.status in statuses

    def canBeDenied(self):
        """See IShippingRequest"""
        statuses = [ShippingRequestStatus.APPROVED,
                    ShippingRequestStatus.PENDINGSPECIAL,
                    ShippingRequestStatus.DUPLICATEDADDRESS,
                    ShippingRequestStatus.PENDING]
        return self.status in statuses

    def markAsDuplicatedAddress(self):
        """See IShippingRequest"""
        self.status = ShippingRequestStatus.DUPLICATEDADDRESS

    def markAsPendingSpecial(self):
        """See IShippingRequest"""
        self.status = ShippingRequestStatus.PENDINGSPECIAL

    def deny(self):
        """See IShippingRequest"""
        assert not self.isDenied()
        if self.isApproved():
            self.clearApproval()
        self.status = ShippingRequestStatus.DENIED

    def clearApproval(self):
        """See IShippingRequest"""
        assert self.isApproved()
        self.status = ShippingRequestStatus.PENDING
        self.whoapproved = None
        self.clearApprovedQuantities()

    def clearApprovedQuantities(self):
        """See IShippingRequest"""
        assert not self.isApproved()
        for requestedcds in self.getAllRequestedCDs():
            requestedcds.quantityapproved = 0

    def approve(self, whoapproved=None):
        """See IShippingRequest"""
        assert not (self.isCancelled() or self.isApproved() or
                    self.isShipped())
        self.status = ShippingRequestStatus.APPROVED
        self.whoapproved = whoapproved

    def cancel(self, whocancelled):
        """See IShippingRequest"""
        assert not self.isCancelled()
        if self.isApproved():
            self.clearApproval()
        self.status = ShippingRequestStatus.CANCELLED
        self.whocancelled = whocancelled

    def addressIsDuplicated(self):
        """See IShippingRequest"""
        return self.getRequestsWithSameAddressFromOtherUsers().count() > 0

    def getRequestsWithSameAddressFromOtherUsers(self, limit=5):
        """See IShippingRequest"""
        query = """
            SELECT ShippingRequest.id
            FROM ShippingRequest
            JOIN RequestedCDs ON ShippingRequest.id = RequestedCDs.request
            WHERE normalized_address = %(address)s
                AND country = %(country)s
                AND recipient != %(recipient)s
                AND status NOT IN (%(cancelled)s, %(denied)s)
                AND RequestedCDs.distrorelease = %(series)s
            """ % sqlvalues(
                address=self.normalized_address, recipient=self.recipient,
                denied=ShippingRequestStatus.DENIED, country=self.country,
                cancelled=ShippingRequestStatus.CANCELLED,
                series=self.distroseries)
        return ShippingRequest.select(
            "id IN (%s)" % query, limit=limit, orderBy='-daterequested')


class ShippingRequestSet:
    """See IShippingRequestSet"""

    implements(IShippingRequestSet)

    def get(self, id, default=None):
        """See IShippingRequestSet"""
        try:
            return ShippingRequest.get(id)
        except (SQLObjectNotFound, ValueError):
            return default

    def processRequests(self, status, new_status):
        """See IShippingRequestSet"""
        if new_status == ShippingRequestStatus.APPROVED:
            action = 'approved'
            method_name = 'approve'
        elif new_status == ShippingRequestStatus.DENIED:
            action = 'denied'
            method_name = 'deny'
        else:
            raise AssertionError(
                'new_status must be APPROVED or DENIED: %r' % new_status)

        requests = ShippingRequest.selectBy(status=status)
        request_messages = []
        for request in requests:
            info = ("Request #%d, made by '%s' containing %d CDs\n(%s)"
                    % (request.id, request.recipientdisplayname,
                       request.getTotalCDs(), canonical_url(request)))
            request_messages.append(info)
            getattr(request, method_name)()
        template = get_email_template('shipit-mass-process-notification.txt')
        body = template % {
            'requests_info': "\n".join(request_messages),
            'action': action, 'status': status}
        to_addr = shipit_admins = config.shipit.admins_email_address
        from_addr = config.shipit.ubuntu_from_email_address
        subject = "Report of auto-%s requests" % action
        simple_sendmail(from_addr, to_addr, subject, body)

    def new(self, recipient, recipientdisplayname, country, city, addressline1,
            phone, addressline2=None, province=None, postcode=None,
            organization=None, reason=None, shockandawe=None):
        """See IShippingRequestSet"""
        # Only the shipit-admins team can have more than one open request
        # at a time.
        assert (recipient == getUtility(ILaunchpadCelebrities).shipit_admin
                or recipient.currentShipItRequest() is None)

        request = ShippingRequest(
            recipient=recipient, reason=reason, shockandawe=shockandawe,
            city=city, country=country, addressline1=addressline1,
            addressline2=addressline2, province=province, postcode=postcode,
            recipientdisplayname=recipientdisplayname,
            organization=organization, phone=phone)

        return request

    def getTotalsForRequests(self, requests):
        """See IShippingRequestSet"""
        requests_ids = ','.join(str(request.id) for request in requests)
        cur = cursor()
        cur.execute("""
            SELECT
                request,
                SUM(quantity) AS total_cds,
                SUM(quantityapproved) AS total_approved_cds
            FROM RequestedCDs
            WHERE request IN (%s)
            GROUP BY request
            """ % requests_ids)
        totals = {}
        for request, total_cds, total_approved_cds in cur.fetchall():
            totals[request] = (total_cds, total_approved_cds)
        return totals

    def getUnshippedRequestsIDs(
            self, priority,
            distroseries=ShipItConstants.current_distroseries):
        """See IShippingRequestSet"""
        if priority == ShippingRequestPriority.HIGH:
            priorityfilter = 'AND ShippingRequest.highpriority IS TRUE'
        elif priority == ShippingRequestPriority.NORMAL:
            priorityfilter = 'AND ShippingRequest.highpriority IS FALSE'
        else:
            # Nothing to filter, return all unshipped requests.
            priorityfilter = ''

        replacements = sqlvalues(distroseries=distroseries,
                                 status=ShippingRequestStatus.APPROVED)
        replacements.update({'priorityfilter': priorityfilter})
        query = """
            SELECT DISTINCT ShippingRequest.id
            FROM ShippingRequest, RequestedCDs
            WHERE shipment IS NULL
                  AND ShippingRequest.id = RequestedCDs.request
                  AND RequestedCDs.distrorelease = %(distroseries)s
                  AND status = %(status)s
                  %(priorityfilter)s
            ORDER BY id
            """ % replacements

        cur = cursor()
        cur.execute(query)
        return [id for (id,) in cur.fetchall()]

    def getOldestPending(self):
        """See IShippingRequestSet"""
        return ShippingRequest.selectFirstBy(
            status=ShippingRequestStatus.PENDING,
            orderBy='daterequested')

    def search(self, status=None, flavour=None, distroseries=None,
               recipient_text=None, orderBy=ShippingRequest.sortingColumns):
        """See IShippingRequestSet"""
        queries = []

        # We use subqueries To filter based on distroseries/flavour so that
        # we don't have to join the RequestedCDs table with a DISTINCT, which
        # causes the query to run a _lot_ slower.
        if distroseries is not None:
            queries.append("""
                ShippingRequest.id IN (
                    SELECT request FROM RequestedCDs WHERE distrorelease = %s)
                """ % sqlvalues(distroseries))

        if flavour is not None:
            queries.append("""
                ShippingRequest.id IN (
                    SELECT request FROM RequestedCDs WHERE flavour = %s)
                """ % sqlvalues(flavour))

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

        if status:
            queries.append("ShippingRequest.status = %s" % sqlvalues(status))

        query = " AND ".join(queries)
        return ShippingRequest.select(
            query, orderBy=orderBy, prejoins=["recipient"])

    def exportRequestsToFiles(
            self, priority, ztm,
            distroseries=ShipItConstants.current_distroseries):
        """See IShippingRequestSet"""
        request_ids = self.getUnshippedRequestsIDs(priority, distroseries)
        # The SOFT_MAX_SHIPPINGRUN_SIZE is not a hard limit, and it doesn't
        # make sense to split a shippingrun into two just because there's 10
        # requests more than the limit, so we only split them if there's at
        # least 50% more requests than SOFT_MAX_SHIPPINGRUN_SIZE.
        file_counter = 0
        while len(request_ids):
            file_counter += 1
            ztm.begin()
            if len(request_ids) > SOFT_MAX_SHIPPINGRUN_SIZE * 1.5:
                request_ids_subset = request_ids[:SOFT_MAX_SHIPPINGRUN_SIZE]
                request_ids[:SOFT_MAX_SHIPPINGRUN_SIZE] = []
            else:
                request_ids_subset = request_ids[:]
                request_ids = []
            shippingrun = self._create_shipping_run(request_ids_subset)
            now = datetime.now(pytz.timezone('UTC'))
            filename = 'Ubuntu-%s' % distroseries.name
            if priority == ShippingRequestPriority.HIGH:
                filename += '-High-Pri'
            filename += '-%s-%d.%s.csv' % (
                now.strftime('%y-%m-%d'), file_counter, generate_uuid())
            shippingrun.exportToCSVFile(filename)
            ztm.commit()

    def _create_shipping_run(self, request_ids):
        """Create and return a ShippingRun containing all requests whose ids
        are in request_ids.

        Each request will be added to the ShippingRun only if it's approved
        and not part of another shipment.
        """
        shippingrun = ShippingRunSet().new()
        for request_id in request_ids:
            request = self.get(request_id)
            if not request.isApproved():
                # This request's status may have been changed after we started
                # running the script. Now it's not approved anymore and we can't
                # export it.
                continue
            assert not (request.isCancelled() or request.isShipped())
            request.status = ShippingRequestStatus.SHIPPED
            shipment = ShipmentSet().new(
                request, request.shippingservice, shippingrun)
        shippingrun.requests_count = shippingrun.requests.count()
        return shippingrun

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

    def _getRequestedCDCount(
        self, current_series_only, country=None, approved=False):
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
        series_filter = ""
        if current_series_only:
            series_filter = (
                " AND RequestedCDs.distrorelease = %s"
                % sqlvalues(ShipItConstants.current_distroseries))
        for flavour in ShipItFlavour.items:
            quantities[flavour] = {}
            for arch in ShipItArchitecture.items:
                query_str = """
                    shippingrequest.shipment IS NOT NULL AND
                    shippingrequest.id = requestedcds.request AND
                    requestedcds.flavour = %s AND
                    requestedcds.architecture = %s""" % sqlvalues(flavour, arch)
                query_str += series_filter
                if country is not None:
                    query_str += (" AND shippingrequest.country = %s"
                                  % sqlvalues(country.id))
                requests = ShippingRequest.select(
                    query_str, clauseTables=['RequestedCDs'])
                quantities[flavour][arch] = intOrZero(
                    requests.sum(attr_to_sum_on))
        return quantities

    def generateCountryBasedReport(self, current_series_only=True):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        header = [
            'Country', 'Total Shipped Ubuntu', 'Total Shipped Kubuntu',
            'Total Shipped Edubuntu', 'Total Shipped', 'Shipped Ubuntu x86 CDs',
            'Shipped Ubuntu AMD64 CDs', 'Shipped Ubuntu PPC CDs',
            'Shipped Kubuntu x86 CDs', 'Shipped Kubuntu AMD64 CDs',
            'Shipped Kubuntu PPC CDs', 'Shipped Edubuntu x86 CDs',
            'Shipped Edubuntu AMD64 CDs', 'Shipped Edubuntu PPC CDs',
            'Normal-prio shipments', 'High-prio shipments',
            'Average request size', 'Approved CDs (percentage)',
            'Percentage of total shipped CDs', 'Continent']
        csv_writer.writerow(header)
        requested_cd_count = self._getRequestedCDCount(
            current_series_only, approved=True)
        all_shipped_cds = self._sumRequestedCDCount(requested_cd_count)
        ubuntu = ShipItFlavour.UBUNTU
        kubuntu = ShipItFlavour.KUBUNTU
        edubuntu = ShipItFlavour.EDUBUNTU
        x86 = ShipItArchitecture.X86
        amd64 = ShipItArchitecture.AMD64
        ppc = ShipItArchitecture.PPC
        for country in Country.select():
            base_query = (
                "shippingrequest.country = %s AND "
                "shippingrequest.shipment IS NOT NULL"
                % sqlvalues(country.id)
                )
            clauseTables = []
            if current_series_only:
                base_query += """
                    AND RequestedCDs.distrorelease = %s
                    AND RequestedCDs.request = ShippingRequest.id
                    """ % sqlvalues(ShipItConstants.current_distroseries)
                clauseTables.append('RequestedCDs')
            total_shipped_requests = ShippingRequest.select(
                base_query, clauseTables=clauseTables, distinct=True).count()
            if not total_shipped_requests:
                continue

            shipped_cds_per_arch = self._getRequestedCDCount(
                current_series_only, country=country, approved=True)

            high_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority IS TRUE",
                clauseTables=clauseTables, distinct=True)
            high_prio_count = intOrZero(high_prio_orders.count())

            normal_prio_orders = ShippingRequest.select(
                base_query + " AND highpriority IS FALSE",
                clauseTables=clauseTables, distinct=True)
            normal_prio_count = intOrZero(normal_prio_orders.count())

            shipped_cds = self._sumRequestedCDCount(shipped_cds_per_arch)
            requested_cd_count = self._getRequestedCDCount(
                current_series_only, country=country, approved=False)
            requested_cds = self._sumRequestedCDCount(requested_cd_count)
            average_request_size = shipped_cds / total_shipped_requests
            percentage_of_approved = float(shipped_cds) / float(requested_cds)
            percentage_of_total = float(shipped_cds) / float(all_shipped_cds)

            # Need to encode strings that may have non-ASCII chars into
            # unicode because we're using StringIO.
            country_name = country.name.encode('utf-8')
            continent_name = country.continent.name.encode('utf-8')
            total_ubuntu = sum(shipped_cds_per_arch[ubuntu].values())
            total_kubuntu = sum(shipped_cds_per_arch[kubuntu].values())
            total_edubuntu = sum(shipped_cds_per_arch[edubuntu].values())
            row = [country_name, total_ubuntu, total_kubuntu, total_edubuntu,
                   total_ubuntu + total_kubuntu + total_edubuntu,
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

    def generateWeekBasedReport(
            self, start_date, end_date, only_current_distroseries=False):
        """See IShippingRequestSet"""
        # This is to ensure we include only full weeks of requests.
        start_monday = start_date - timedelta(days=start_date.isoweekday() - 1)
        end_sunday = end_date - timedelta(days=end_date.isoweekday())

        flavour = ShipItFlavour
        arch = ShipItArchitecture
        quantities_order = [
            [flavour.UBUNTU, arch.X86, 'Ubuntu Requested PC CDs'],
            [flavour.UBUNTU, arch.AMD64, 'Ubuntu Requested 64-bit PC CDs'],
            [flavour.UBUNTU, arch.PPC, 'Ubuntu Requested Mac CDs'],
            [flavour.KUBUNTU, arch.X86, 'Kubuntu Requested PC CDs'],
            [flavour.KUBUNTU, arch.AMD64, 'Kubuntu Requested 64-bit PC CDs'],
            [flavour.KUBUNTU, arch.PPC, 'Kubuntu Requested Mac CDs'],
            [flavour.EDUBUNTU, arch.X86, 'Edubuntu Requested PC CDs'],
            [flavour.EDUBUNTU, arch.AMD64, 'Edubuntu Requested 64-bit PC CDs'],
            [flavour.EDUBUNTU, arch.PPC, 'Edubuntu Requested Mac CDs']]

        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        header = ['Year', 'Week number', 'Week start', 'Requests',
                  'Ubuntu Total', 'Kubuntu Total', 'Edubuntu Total',
                  'Grand Total']
        for dummy, dummy, label in quantities_order:
            header.append(label)
        csv_writer.writerow(header)

        if only_current_distroseries:
            requests_base_query = """
                SELECT COUNT(DISTINCT ShippingRequest.id)
                FROM ShippingRequest, RequestedCDs
                WHERE ShippingRequest.status != %s
                      AND RequestedCDs.request = ShippingRequest.id
                      AND RequestedCDs.distrorelease = %s
                """ % sqlvalues(ShippingRequestStatus.CANCELLED,
                                ShipItConstants.current_distroseries)
        else:
            requests_base_query = """
                SELECT COUNT(ShippingRequest.id)
                FROM ShippingRequest
                WHERE ShippingRequest.status != %s
                """ % sqlvalues(ShippingRequestStatus.CANCELLED)

        sum_base_query = """
            SELECT flavour, architecture, SUM(quantity)
            FROM RequestedCDs, ShippingRequest
            WHERE RequestedCDs.request = ShippingRequest.id
                  AND ShippingRequest.status != %s
            """ % sqlvalues(ShippingRequestStatus.CANCELLED)
        if only_current_distroseries:
            sum_base_query += (
                " AND RequestedCDs.distrorelease = %s"
                % sqlvalues(ShipItConstants.current_distroseries))

        sum_group_by = " GROUP BY flavour, architecture"

        cur = cursor()
        for monday_date in make_mondays_between(start_monday, end_sunday):
            year, weeknum, weekday = monday_date.isocalendar()
            row = [year, weeknum, monday_date.strftime('%Y-%m-%d')]

            date_filter = (
                " AND shippingrequest.daterequested BETWEEN %s AND %s"
                % sqlvalues(monday_date, monday_date + timedelta(days=7)))
            requests_query = requests_base_query + date_filter
            sum_query = sum_base_query + date_filter + sum_group_by

            cur.execute(requests_query)
            row.extend(cur.fetchone())

            cur.execute(sum_query)
            sum_dict = self._convertResultsToDict(cur.fetchall())

            quantities_row = []
            flavours = []
            summed_flavours = {}

            for flavour, arch, dummy in quantities_order:
                item = sum_dict.get(flavour, {})
                sum_by_flavor_and_arch = item.get(arch, 0)

                if summed_flavours.get(flavour) is None:
                    flavours.append(flavour)
                    summed_flavours[flavour] = 0
                summed_flavours[flavour] += sum_by_flavor_and_arch
                quantities_row.append(sum_by_flavor_and_arch)

            for flavour in flavours:
                row.append(summed_flavours[flavour])

            weekly_total = sum(summed_flavours.values())
            row.append(weekly_total)

            row.extend(quantities_row)
            csv_writer.writerow(row)

        csv_file.seek(0)
        return csv_file

    def _convertResultsToDict(self, results):
        """Convert a list of (flavour_id, architecture_id, quantity) tuples
        returned by a raw SQL query into a dictionary mapping ShipItFlavour
        and ShipItArchitecture objects to the quantities.
        """
        sum_dict = {}
        for flavour_id, arch_id, sum in results:
            flavour = ShipItFlavour.items[flavour_id]
            sum_dict.setdefault(flavour, {})
            arch = ShipItArchitecture.items[arch_id]
            sum_dict[flavour].update({arch: sum})
        return sum_dict

    def generateShipmentSizeBasedReport(self, current_series_only=True):
        """See IShippingRequestSet"""
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        header = ['Number of CDs', 'Number of Shipments']
        csv_writer.writerow(header)
        series_filter = ""
        if current_series_only:
            series_filter = (
                " AND RequestedCDs.distrorelease = %s"
                % sqlvalues(ShipItConstants.current_distroseries))
        query_str = """
            SELECT shipment_size, COUNT(request_id) AS shipments
            FROM
            (
                SELECT shippingrequest.id AS request_id,
                       SUM(quantityapproved) AS shipment_size
                FROM requestedcds, shippingrequest
                WHERE requestedcds.request = shippingrequest.id
                      AND shippingrequest.shipment IS NOT NULL
                      %(series_filter)s
                GROUP BY shippingrequest.id
            )
            AS TMP GROUP BY shipment_size ORDER BY shipment_size
            """ % vars()
        cur = cursor()
        cur.execute(query_str)
        for shipment_size, shipments in cur.fetchall():
            csv_writer.writerow([shipment_size, shipments])

        csv_file.seek(0)
        return csv_file

    def generateRequestDistributionReport(self):
        """See IShippingRequestSet"""
        # First we get the distribution of requests/shipments for the current
        # series only.
        shipit_admins = getUtility(ILaunchpadCelebrities).shipit_admin
        cur = cursor()
        query = """
            SELECT requests, requesters,
                cds_requested / (requests * requesters) AS avg_requested_cds
            FROM (
                SELECT requests, COUNT(recipient) AS requesters,
                    SUM(requested_cds_per_user) AS cds_requested
                FROM (
                    SELECT recipient,
                        COUNT(DISTINCT request) AS requests,
                        SUM(quantity) AS requested_cds_per_user
                    FROM RequestedCDs
                        JOIN ShippingRequest ON
                            ShippingRequest.id = RequestedCDs.request
                    WHERE distrorelease = %(current_series)s
                        AND status != %(cancelled)s
                        AND recipient != %(shipit_admins)s
                    GROUP BY recipient
                    ) AS REQUEST_DISTRIBUTION
                GROUP BY requests
                ) AS REQUEST_DISTRIBUTION_AND_TOTALS
            """ % sqlvalues(
                    current_series=ShipItConstants.current_distroseries,
                    shipit_admins=shipit_admins,
                    cancelled=ShippingRequestStatus.CANCELLED)
        cur.execute(query)
        current_series_request_distribution = cur.fetchall()

        query = """
            SELECT approved_requests, recipients,
                cds_approved / (approved_requests * recipients)
                    AS avg_shipment_size
            FROM (
                SELECT COUNT(recipient) AS recipients, approved_requests,
                    SUM(approved_cds_per_user) AS cds_approved
                FROM (
                    SELECT recipient,
                        COUNT(DISTINCT request) AS approved_requests,
                        SUM(quantityapproved) AS approved_cds_per_user
                    FROM RequestedCDs
                        JOIN ShippingRequest ON
                            ShippingRequest.id = RequestedCDs.request
                    WHERE distrorelease = %(current_series)s
                        AND status IN (%(approved)s, %(shipped)s)
                        AND recipient != %(shipit_admins)s
                    GROUP BY recipient
                    ) AS SHIPMENT_DISTRIBUTION
                GROUP BY approved_requests
                ) AS SHIPMENT_DISTRIBUTION_AND_TOTALS
            """ % sqlvalues(
                    current_series=ShipItConstants.current_distroseries,
                    shipit_admins=shipit_admins,
                    approved=ShippingRequestStatus.APPROVED,
                    shipped=ShippingRequestStatus.SHIPPED)
        cur.execute(query)
        current_series_shipment_distribution = cur.fetchall()

        # We need to create some temporary tables to make the next queries run
        # in non-geological time.
        create_tables = """
            -- People with non-cancelled requests for the current series.
            CREATE TEMPORARY TABLE current_series_requester
                (recipient integer);
            INSERT INTO current_series_requester (
                SELECT DISTINCT recipient
                FROM ShippingRequest
                    JOIN RequestedCDs
                        ON RequestedCDs.request = ShippingRequest.id
                WHERE distrorelease = %(current_series)s
                    AND recipient != %(shipit_admins)s
                    AND status != %(cancelled)s);
            CREATE UNIQUE INDEX current_series_requester__unq
                ON current_series_requester(recipient);

            -- People with with non-cancelled requests for any series other
            -- than the current one.
            CREATE TEMPORARY TABLE previous_series_requester
                (recipient integer);
            INSERT INTO previous_series_requester (
                SELECT DISTINCT recipient
                FROM ShippingRequest
                    JOIN RequestedCDs
                        ON RequestedCDs.request = ShippingRequest.id
                WHERE distrorelease < %(current_series)s
                    AND recipient != %(shipit_admins)s
                    AND status != %(cancelled)s);
            CREATE UNIQUE INDEX previous_series_requester__unq
                ON previous_series_requester(recipient);

            -- People which made requests for any series other than the
            -- current one, but none of the requests were ever shipped.
            CREATE TEMPORARY TABLE previous_series_non_recipient
                (recipient integer);
            INSERT INTO previous_series_non_recipient (
                SELECT DISTINCT recipient
                FROM ShippingRequest
                    JOIN RequestedCDs
                        ON RequestedCDs.request = ShippingRequest.id
                WHERE distrorelease < %(current_series)s
                    AND recipient != %(shipit_admins)s
                    AND status NOT IN (%(shipped)s, %(cancelled)s)
                EXCEPT
                SELECT DISTINCT recipient
                FROM ShippingRequest
                    JOIN RequestedCDs
                        ON RequestedCDs.request = ShippingRequest.id
                WHERE distrorelease < %(current_series)s
                    AND recipient != %(shipit_admins)s
                    AND status = %(shipped)s);
            CREATE UNIQUE INDEX previous_series_non_recipient__unq
                ON previous_series_non_recipient(recipient);
            """ % sqlvalues(
                    current_series=ShipItConstants.current_distroseries,
                    shipit_admins=shipit_admins,
                    shipped=ShippingRequestStatus.SHIPPED,
                    cancelled=ShippingRequestStatus.CANCELLED)
        cur.execute(create_tables)

        # Now we get the distribution of other-than-current-series
        # requests/shipments for the people which made requests of the current
        # series.
        query = """
            SELECT requests, requesters,
                CASE WHEN requests > 0
                        THEN cds_requested / (requests * requesters)
                     ELSE 0
                END AS avg_requested_cds
            FROM (
                SELECT requests, SUM(requested_cds_per_user) AS cds_requested,
                    COUNT(recipient) AS requesters
                FROM (
                    -- This select will give us the people which made feisty
                    -- requests and which also made requests for other series.
                    SELECT recipient, SUM(quantity) AS requested_cds_per_user,
                        COUNT(DISTINCT request) AS requests
                    FROM RequestedCDs, ShippingRequest
                    WHERE distrorelease < %(current_series)s
                        AND status != %(cancelled)s
                        AND ShippingRequest.id = RequestedCDs.request
                        AND recipient IN (
                            SELECT recipient FROM current_series_requester)
                        AND recipient != %(shipit_admins)s
                    GROUP BY recipient
                    UNION
                    -- This one gives us the people which made feisty requests
                    -- but haven't made requests for any other series.
                    SELECT recipient, 0 AS requested_cds_per_user,
                        0 AS requests
                    FROM (SELECT recipient FROM current_series_requester
                          EXCEPT
                          SELECT recipient FROM previous_series_requester
                         ) AS FIRST_TIME_REQUESTERS
                    WHERE recipient != %(shipit_admins)s
                    ) AS RECIPIENTS_AND_COUNTS
                GROUP BY requests
                ) AS REQUEST_DISTRIBUTION_AND_TOTALS
            WHERE requesters > 0
            """ % sqlvalues(
                    current_series=ShipItConstants.current_distroseries,
                    shipit_admins=shipit_admins,
                    cancelled=ShippingRequestStatus.CANCELLED)
        cur.execute(query)
        other_serieses_request_distribution = cur.fetchall()

        query = """
            SELECT requests, requesters,
                CASE WHEN requests > 0
                        THEN cds_approved / (requests * requesters)
                     ELSE 0
                END AS avg_approved_cds
            FROM (
                SELECT requests, SUM(approved_cds_per_user) AS cds_approved,
                    COUNT(recipient) AS requesters
                FROM (
                    -- This select will give us the people which made feisty
                    -- requests and which also had shipped requests for other
                    -- serieses.
                    SELECT recipient,
                        SUM(quantityapproved) AS approved_cds_per_user,
                        COUNT(DISTINCT request) AS requests
                    FROM RequestedCDs, ShippingRequest
                    WHERE distrorelease < %(current_series)s
                        AND status = %(shipped)s
                        AND ShippingRequest.id = RequestedCDs.request
                        AND recipient IN (
                            SELECT recipient FROM current_series_requester)
                    GROUP BY recipient
                    UNION
                    -- This one gives us the people which made feisty requests
                    -- but haven't had any shipped request of previous
                    -- serieses.
                    SELECT recipient, 0 AS approved_cds_per_user, 0 AS requests
                    FROM RequestedCDs, ShippingRequest
                    WHERE distrorelease < %(current_series)s
                        AND status != %(shipped)s
                        AND ShippingRequest.id = RequestedCDs.request
                        AND recipient IN (
                            SELECT recipient FROM current_series_requester)
                        AND recipient IN (
                            SELECT recipient
                            FROM previous_series_non_recipient)
                    UNION
                    -- This one gives us the people which made feisty requests
                    -- but haven't made requests for any other serieses.
                    SELECT recipient, 0 AS approved_cds_per_user, 0 AS requests
                    FROM (SELECT recipient FROM current_series_requester
                          EXCEPT
                          SELECT recipient FROM previous_series_requester
                         ) AS FIRST_TIME_RECIPIENTS
                    ) AS RECIPIENTS_AND_COUNTS
                GROUP BY requests
                ) AS SHIPMENT_DISTRIBUTION_AND_TOTALS
            WHERE requesters > 0
            """ % sqlvalues(
                    current_series=ShipItConstants.current_distroseries,
                    shipit_admins=shipit_admins,
                    approved=ShippingRequestStatus.APPROVED,
                    shipped=ShippingRequestStatus.SHIPPED)
        cur.execute(query)
        other_serieses_shipment_distribution = cur.fetchall()

        # Get the numbers of the rows we want to display.
        all_results = itertools.chain(
            current_series_shipment_distribution,
            current_series_request_distribution,
            other_serieses_shipment_distribution,
            other_serieses_request_distribution)
        row_numbers = set()
        for requests, requesters, avg_size in all_results:
            row_numbers.add(requests)

        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        header1 = ['', '', 'Current Series Only', '', '',
                  '', '', 'Previous Series Only', '']
        header2 = ['', 'requests', '', 'shipped', '', 'requests', '',
                   'shipped', '']
        header3 = ['# of requests', '# of people', '%', 'avg CDs per request',
                   '# of people', '%', 'avg CDs per shipment', '# of people',
                   '%', 'avg CDs per request', '# of people', '%',
                   'avg CDs per shipment']
        csv_writer.writerow(header1)
        csv_writer.writerow(header2)
        csv_writer.writerow(header3)

        # XXX: Guilherme Salgado 2007-04-25:
        # I admit these names couldn't be worse, but they're only used
        # a few lines below and I can't think of anything better.
        cr = self._convert_results_to_dict_and_fill_gaps(
            current_series_request_distribution, row_numbers)
        cr = self._add_percentage_to_number_of_people(cr)
        cs = self._convert_results_to_dict_and_fill_gaps(
            current_series_shipment_distribution, row_numbers)
        cs = self._add_percentage_to_number_of_people(cs)
        or_ = self._convert_results_to_dict_and_fill_gaps(
            other_serieses_request_distribution, row_numbers)
        or_ = self._add_percentage_to_number_of_people(or_)
        os = self._convert_results_to_dict_and_fill_gaps(
            other_serieses_shipment_distribution, row_numbers)
        os = self._add_percentage_to_number_of_people(os)

        for number in sorted(row_numbers):
            row = [number]
            for dictionary in cr, cs, or_, os:
                row.extend(dictionary[number])
            csv_writer.writerow(row)
        csv_file.seek(0)
        return csv_file

    def _add_percentage_to_number_of_people(self, results_dict):
        """For each element of the given dict change its value to contain the
        percentage of people relative to the total of people from all items.

        The given dict must be of the form:
            {number_of_requests: (number_of_people, average_size)}
        """
        total = sum(people for people, size in results_dict.values())
        total = float(total) / 100
        d = {}
        for key, value in results_dict.items():
            people, size = value
            percentage = float(people) / total
            d[key] = (people, percentage, size)
        return d

    def _convert_results_to_dict_and_fill_gaps(self, results, row_numbers):
        """Convert results to a dict, also filling any missing keys.

        Results must be a sequence of 3-tuples in which the first element of
        each 3-tuple is the dict's key and the other two are its value. If any
        of the items in row_numbers are not in the dict's keys, they're added
        with a value of (0,0).
        """
        d = {}
        for requests, requesters, avg_size in results:
            d[requests] = (requesters, avg_size)
        for number in set(row_numbers) - set(d.keys()):
            d[number] = (0, 0)
        return d


class RequestedCDs(SQLBase):
    """See IRequestedCDs"""

    implements(IRequestedCDs)

    quantity = IntCol(notNull=True, default=0)
    quantityapproved = IntCol(notNull=True, default=0)

    request = ForeignKey(
        dbName='request', foreignKey='ShippingRequest', notNull=True)

    distroseries = EnumCol(dbName='distrorelease',
        enum=ShipItDistroSeries, notNull=True)
    architecture = EnumCol(enum=ShipItArchitecture, notNull=True)
    flavour = EnumCol(enum=ShipItFlavour, notNull=True)

    @property
    def description(self):
        text = "%(quantity)d %(flavour)s "
        if self.quantity > 1:
            text += "CDs "
        else:
            text += "CD "
        text += "for %(arch)s"
        replacements = {
            'quantity': self.quantity, 'flavour': self.flavour.title,
            'arch': self.architecture.title}
        return text % replacements


class StandardShipItRequest(SQLBase):
    """See IStandardShipItRequest"""

    implements(IStandardShipItRequest)
    _table = 'StandardShipItRequest'

    quantityx86 = IntCol(notNull=True)
    quantityppc = IntCol(notNull=True)
    quantityamd64 = IntCol(notNull=True)
    isdefault = BoolCol(notNull=True, default=False)
    flavour = EnumCol(enum=ShipItFlavour, notNull=True)

    @property
    def description_without_flavour(self):
        """See IStandardShipItRequest"""
        if self.totalCDs > 1:
            description = "%d CDs" % self.totalCDs
        else:
            description = "%d CD" % self.totalCDs
        return "%s (%s)" % (description, self._detailed_description())

    @property
    def description(self):
        """See IStandardShipItRequest"""
        if self.totalCDs > 1:
            description = "%d %s CDs" % (self.totalCDs, self.flavour.title)
        else:
            description = "%d %s CD" % (self.totalCDs, self.flavour.title)
        return "%s (%s)" % (description, self._detailed_description())

    @property
    def quantities(self):
        """See IStandardShipItRequest"""
        return {ShipItArchitecture.X86: self.quantityx86,
                ShipItArchitecture.AMD64: self.quantityamd64,
                ShipItArchitecture.PPC: self.quantityppc}

    def _detailed_description(self):
        detailed = []
        text = '%d %s Edition'
        if self.quantityx86:
            detailed.append(
                text % (self.quantityx86, ShipItArchitecture.X86.title))
        if self.quantityamd64:
            detailed.append(
                text % (self.quantityamd64, ShipItArchitecture.AMD64.title))
        if self.quantityppc:
            detailed.append(
                text % (self.quantityppc, ShipItArchitecture.PPC.title))
        return ", ".join(detailed)

    @property
    def totalCDs(self):
        """See IStandardShipItRequest"""
        return self.quantityx86 + self.quantityppc + self.quantityamd64


class StandardShipItRequestSet:
    """See IStandardShipItRequestSet"""

    implements(IStandardShipItRequestSet)

    def new(self, flavour, quantityx86, quantityamd64, quantityppc, isdefault):
        """See IStandardShipItRequestSet"""
        return StandardShipItRequest(flavour=flavour, quantityx86=quantityx86,
                quantityppc=quantityppc, quantityamd64=quantityamd64,
                isdefault=isdefault)

    def getByFlavour(self, flavour, user=None):
        """See IStandardShipItRequestSet"""
        query = "flavour = %s" % sqlvalues(flavour)
        if user is None or not user.is_trusted_on_shipit:
            query += (" AND quantityx86 + quantityppc + quantityamd64 <= %s"
                      % sqlvalues(MAX_CDS_FOR_UNTRUSTED_PEOPLE))
        orderBy = SQLConstant("quantityx86 + quantityppc + quantityamd64, id")
        return StandardShipItRequest.select(query, orderBy=orderBy)

    def getAllGroupedByFlavour(self):
        """See IStandardShipItRequestSet"""
        standard_requests = {}
        for flavour in ShipItFlavour.items:
            standard_requests[flavour] = StandardShipItRequest.selectBy(
                flavour=flavour)
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
    shippingservice = EnumCol(enum=ShippingService, notNull=True)
    shippingrun = ForeignKey(dbName='shippingrun', foreignKey='ShippingRun',
                             notNull=True)
    request = ForeignKey(dbName='request', foreignKey='ShippingRequest',
                         notNull=True, unique=True)
    trackingcode = StringCol(default=None)

    @property
    def request(self):
        """See IShipment"""
        return ShippingRequest.selectOneBy(shipment=self)



class ShipmentSet:
    """See IShipmentSet"""

    implements(IShipmentSet)

    def new(self, request, shippingservice, shippingrun, trackingcode=None,
            dateshipped=None):
        """See IShipmentSet"""
        token = self._generateToken()
        while self.getByToken(token):
            token = self._generateToken()

        shipment = Shipment(
            shippingservice=shippingservice, shippingrun=shippingrun,
            trackingcode=trackingcode, logintoken=token,
            dateshipped=dateshipped)
        request.shipment = shipment
        # We must sync as callsites need to lookup a request for the shipment.
        request.sync()
        return shipment

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
    requests_count = IntCol(notNull=True, default=0)

    @property
    def requests(self):
        query = ("ShippingRequest.shipment = Shipment.id AND "
                 "Shipment.shippingrun = ShippingRun.id AND "
                 "ShippingRun.id = %s" % sqlvalues(self.id))

        clausetables = ['ShippingRun', 'Shipment']
        return ShippingRequest.select(query, clauseTables=clausetables)

    def exportToCSVFile(self, filename):
        """See IShippingRun"""
        csv_file = self._createCSVFile()
        csv_file.seek(0)
        self.csvfile = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(csv_file.getvalue()), file=csv_file,
            contentType='text/plain')

    def _createCSVFile(self):
        """Return a csv file containing all requests that are part of this
        shippingrun.
        """
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
        # Instead of using quoting=csv.QUOTE_ALL here, we need to do the
        # quoting ourselves and prepend the postcode with an "=" sign, to make
        # sure OpenOffice/Excel doesn't drop leading zeros. This is not
        # supposed to work on applications other than OpenOffice/Excel, but it
        # shouldn't be a problem for us, as we'll always open it with one of
        # those and save the file as xls before sending to MediaMotion.
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_NONE)
        row = ['"%s"' % label for label, attr in file_fields]
        # The values for these fields we can't get using getattr(), so we have
        # to set them manually.
        extra_fields = ['ship Ubuntu quantity PC',
                        'ship Ubuntu quantity 64-bit PC',
                        'ship Ubuntu quantity Mac',
                        'ship Kubuntu quantity PC',
                        'ship Kubuntu quantity 64-bit PC',
                        'ship Kubuntu quantity Mac',
                        'ship Edubuntu quantity PC',
                        'ship Edubuntu quantity 64-bit PC',
                        'ship Edubuntu quantity Mac',
                        'token', 'Ship via', 'display']
        row.extend('"%s"' % field for field in extra_fields)
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
                if isinstance(value, basestring):
                    # Text fields can't have non-ASCII characters or commas.
                    # This is a restriction of the shipping company.
                    value = value.replace(',', ';')
                    # Because we do the quoting ourselves, we need to manually
                    # escape any '"' character.
                    value = value.replace('"', '""')
                    # And normalize whitespace - linefeeds will break the CSV
                    # writer.
                    value = re.sub(r'\s+', ' ', value.strip())
                    # Here we can be sure value can be encoded into ASCII
                    # because we always check this in the UI.
                    value = value.encode('ASCII')

                value = '"%s"' % value
                # See the comment about the use of quoting=csv.QUOTE_ALL a few
                # lines above for an explanation of this hack.
                if attr == 'postcode':
                    value = "=%s" % value

                row.append(value)

            all_requested_cds = request.getRequestedCDsGroupedByFlavourAndArch()
            # The order that the flavours and arches appear in the following
            # two for loops must match the order the headers appear in
            # extra_fields.
            for flavour in [ubuntu, kubuntu, edubuntu]:
                for arch in [x86, amd64, ppc]:
                    requested_cds = all_requested_cds[flavour][arch]
                    if requested_cds is None:
                        quantityapproved = 0
                    else:
                        quantityapproved = requested_cds.quantityapproved
                    row.append('"%s"' % quantityapproved)

            row.append('"%s"' % request.shipment.logintoken.encode('ASCII'))
            row.append('"%s"' % request.shippingservice.title.encode('ASCII'))
            # XXX: Guilherme Salgado 2005-10-04:
            # 'display' is some magic number that's used by the shipping
            # company. Need to figure out what's it for and use a better name.
            if request.getTotalApprovedCDs() >= 100:
                display = 1
            else:
                display = 0
            row.append('"%s"' % display)
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
