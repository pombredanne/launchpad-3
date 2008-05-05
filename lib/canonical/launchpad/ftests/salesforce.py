# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Helper classes for testing clients of the external Salesforce proxy."""


__metaclass__ = type

__all__ = [
    'SalesforceXMLRPCTestTransport',
    ]


import copy
import os
import re
import time
import urlparse
import xmlrpclib

STATUSES = ['UNREDEEMED',
            'REDEEMED']

PRODUCT_TERM_MAP = dict(LPCS12=12,
                        LPCS06=6)

class Voucher:
    def __init__(self, voucher_id, owner):
        self.id = voucher_id
        self.owner = owner
        self.status = 'UNREDEEMED'
        self.project_id = None
        self.project_name = None

    def __repr__(self):
        return "%s %s" % (self.id, self.status)


class SalesforceXMLRPCTestTransport(xmlrpclib.Transport):
    """An XML-RPC test transport for the Salesforce proxy."""

    vouchers = [Voucher('LPCS12-f78df324-0cc2-11dd-8b6b-000000000001', 'sabdfl_oid'),
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

    def getServerStatus(self):
        return "Server is running normally"

    def getUnredeemedVouchers(self, lp_openid):
        """Return the list of unredeemed vouchers for a given id.

        The returned value is a list of dictionaries, each having a 'voucher'
        and 'status' keys.
        """

        vouchers = [dict(voucher=voucher.id,
                         status=voucher.status)
                    for voucher in self.vouchers
                    if (voucher.owner == lp_openid and
                        voucher.status == 'UNREDEEMED')
                    ]
        return vouchers

    def transferVoucher(self, voucher_id, from_lp_openid, to_lp_openid):
        voucher = self._findVoucher(voucher_id)
        if voucher is not None:
            return [False]
        voucher.owner = to_lp_openid
        return [True]

    def redeemVoucher(self, voucher_id, lp_openid,
                      lp_project_id, lp_project_name):
        voucher = self._findVoucher(voucher_id)
        if (voucher is None or
            voucher.status != 'UNREDEEMED' or
            voucher.owner != lp_openid):
            return [False, 0]
        voucher.status = 'REDEEMED'
        voucher.project_id = lp_project_id
        voucher.project_name = lp_project_name
        product = voucher.id.split('-')[0]
        term = PRODUCT_TERM_MAP.get(product)
        if term is None:
            return [False, 0]
        else:
            return [True, term]

    def updateProjectName(self, lp_project_id, lp_project_name):
        num_updated = 0
        for voucher in self.vouchers:
            if voucher.project_id == lp_project_id:
                voucher.project_name = lp_project_name
                num_updated += 1
        return [num_updated]

    def request(self, host, handler, request, verbose=None):
        """Call the corresponding XML-RPC method.

        The method name and arguments are extracted from `request`. The
        method on this class with the same name as the XML-RPC method is
        called, with the extracted arguments passed on to it.
        """
        args, method_name = xmlrpclib.loads(request)
        method = getattr(self, method_name)
        return method(*args)
