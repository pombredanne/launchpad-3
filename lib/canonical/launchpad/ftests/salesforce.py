# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Helper classes for testing clients of the external Salesforce proxy."""


__metaclass__ = type

__all__ = [
    'SalesforceXMLRPCTestTransport',
    'TestSalesforceVoucherProxy',
    ]


import copy
import xmlrpclib
from zope.interface import implements

from canonical.launchpad.utilities import SalesforceVoucherProxy
from canonical.launchpad.interfaces import ISalesforceVoucherProxy


STATUSES = ['UNREDEEMED',
            'REDEEMED']


PRODUCT_TERM_MAP = dict(LPCS12=12,
                        LPCS06=6)


class Voucher:
    """Test data for a single voucher."""
    def __init__(self, voucher_id, owner):
        self.id = voucher_id
        self.owner = owner
        self.status = 'UNREDEEMED'
        self.project_id = None
        self.project_name = None
        product = self.id.split('-')[0]
        self.term = PRODUCT_TERM_MAP.get(product)

    def __str__(self):
        return "%s,%s" % (self.id, self.status)

    def asDict(self):
        return dict(voucher=self.id,
                    status=self.status,
                    term=self.term,
                    project_id=self.project_id)


class TestSalesforceVoucherProxy(SalesforceVoucherProxy):
    """Test version of the SalesforceVoucherProxy using the test transport."""
    implements(ISalesforceVoucherProxy)

    def __init__(self):
        self.xmlrpc_transport = SalesforceXMLRPCTestTransport()


class SalesforceXMLRPCTestTransport(xmlrpclib.Transport):
    """An XML-RPC test transport for the Salesforce proxy.

    This transport contains a small amount of sample data and intercepts
    requests that would normally be sent via XML-RPC but instead directly
    provides responses based on the sample data.  This transport does not
    simulate network errors or timeouts.
    """

    vouchers = [
        Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000001', 'sabdfl_oid'),
        Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000002', 'sabdfl_oid'),
        Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000003', 'sabdfl_oid'),
        Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000004', 'cprov_oid'),
        Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000005', 'cprov_oid'),
        ]

    def __init__(self):
        self.vouchers = copy.deepcopy(self.vouchers)

    def _findVoucher(self, voucher_id):
        for voucher in self.vouchers:
            if voucher.id == voucher_id:
                return voucher
        return None

    def createResponse(self, status, results=None, errors=None):
        """Create the correct response dictionary

        The 'success' key must always be present and a Boolean.
        """
        response = dict(success=status,
                        results=results,
                        errors=errors)
        return [response]

    def getServerStatus(self):
        """Get the server status.  If it responds it is healthy.

        Included here for completeness though it is never called by
        Launchpad.
        """
        return self.createResponse(status=True,
                                   results="Server is running normally"
                                   )

    def getUnredeemedVouchers(self, lp_openid):
        """Return the list of unredeemed vouchers for a given id.

        The returned value is a list of dictionaries, each having a 'voucher'
        and 'status' keys.
        """
        vouchers = [voucher.asDict() for voucher in self.vouchers
                    if (voucher.owner == lp_openid and
                        voucher.status == 'UNREDEEMED')]
        return self.createResponse(status=True, results=vouchers)

    def getAllVouchers(self, lp_openid):
        """Return the complete list of vouchers for a given id.

        The returned value is a list of dictionaries, each having a 'voucher',
        'status', and 'project_id' keys.
        """
        vouchers = [voucher.asDict() for voucher in self.vouchers
                    if voucher.owner == lp_openid]
        return self.createResponse(status=True, results=vouchers)

    def getVoucher(self, voucher_id):
        """Return the voucher."""

        voucher = self._findVoucher(voucher_id)
        if voucher is not None:
            voucher = voucher.asDict()
        return self.createResponse(status=True, results=voucher)

    def redeemVoucher(self, voucher_id, lp_openid,
                      lp_project_id, lp_project_name):
        """Redeem the voucher.

        :param voucher_id: string representing the unique voucher id.
        :param lp_openid: string representing the Launchpad user's OpenID.
        :param lp_project_id: integer representing the id for the project
           being subscribed by the use of this voucher.
        :param lp_project_name: string representing the name of the project in
            Launchpad.
        :return: Boolean representing the success or failure of the operation.
        """
        voucher = self._findVoucher(voucher_id)
        errors = []
        status = True

        if voucher is None:
            errors.append('ERROR: No such voucher %s' % voucher_id)
            status = False
        else:
            if voucher.status != 'UNREDEEMED':
                errors.append('ERROR: Voucher %s is already redeemed' % voucher_id)
                status = False

            if voucher.owner != lp_openid:
                errors.append("Voucher is not owned by named user")
                status = False

        if status:
            voucher.status = 'REDEEMED'
            voucher.project_id = lp_project_id
            voucher.project_name = lp_project_name
            product = voucher.id.split('-')[0]
            status = True

        return self.createResponse(status=status, errors=errors)

    def updateProjectName(self, lp_project_id, lp_project_name):
        """Set the project name for the given project id."""
        num_updated = 0
        for voucher in self.vouchers:
            if voucher.project_id == lp_project_id:
                voucher.project_name = lp_project_name
                num_updated += 1
        if num_updated == 0:
            status = False
            results = None
            errors = ['ERROR: No vouchers matching product id %s' % lp_project_id]
        else:
            status = True
            results = num_updated
            errors = []

        return self.createResponse(status=status,
                                   results=results,
                                   errors=errors)

    def request(self, host, handler, request, verbose=None):
        """Call the corresponding XML-RPC method.

        The method name and arguments are extracted from `request`. The
        method on this class with the same name as the XML-RPC method is
        called, with the extracted arguments passed on to it.
        """
        args, method_name = xmlrpclib.loads(request)
        method = getattr(self, method_name)
        return method(*args)
