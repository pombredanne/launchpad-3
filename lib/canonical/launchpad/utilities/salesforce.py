# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for accessing the external Salesforce proxy."""

__metaclass__ = type
__all__ = ['SalesforceVoucherProxy',
           'SalesforceVoucherProxyException',
           'Voucher']


import xmlrpclib
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    IProductSet, ISalesforceVoucherProxy)


class SalesforceVoucherProxyException(Exception):
    """Exception raised on failed call to the SalesforceVoucherProxy."""
    def __init__(self, errors):
        self.message = ", ".join(errors)

    def __str__(self):
        return repr(self.message)


class Voucher:
    """A Commercial Subscription voucher."""
    def __init__(self, values):
        """Initialize using the values as returned from the SF proxy.
        :param values['voucher']: voucher id.
        :param values['status']: string representing the redemption status.
        :param values['term']: integer representing number of months of
            subscription the voucher enables.
        :param values['project_id']: integer id for the project this voucher
            has been redeemed  against.  If unredeemed this entry is absent.
        """
        self.id = values.get('voucher')
        self.status = values.get('status')
        self.term = values.get('term')
        project_id = values.get('project_id')
        if project_id is not None:
            self.project = getUtility(IProductSet).get(project_id)
        else:
            self.project = None

    def __str__(self):
        if self.project is None:
            project_name = "unassigned"
        else:
            project_name = self.project.displayname
        return "%s,%s,%s,%s" % (self.id,
                                self.status,
                                self.term,
                                project_name)


class SalesforceVoucherProxy:

    implements(ISalesforceVoucherProxy)

    def __init__(self):
        self.xmlrpc_transport = xmlrpclib.Transport

    @cachedproperty
    def url(self):
        """Get the proxy URL with port."""
        return "%s:%d" % (config.commercial.voucher_proxy_url,
                          config.commercial.voucher_proxy_port)
    @property
    def server_proxy(self):
        """See `ISalesforceVoucherProxy`."""
        # This is not a cachedproperty as each use needs a new proxy.
        return xmlrpclib.ServerProxy(self.url,
                                     transport=self.xmlrpc_transport)

    def parseResponse(self, response):
        success = response.get('success')
        results = response.get('results', [])
        errors = response.get('errors', [])
        if not success:
            raise SalesforceVoucherProxyException, errors
        return results

    def getUnredeemedVouchers(self, user):
        """See `ISalesforceVoucherProxy`."""
        server = self.server_proxy
        response = server.getUnredeemedVouchers(user.openid_identifier)
        results = self.parseResponse(response)
        return [Voucher(voucher) for voucher in results]

    def getAllVouchers(self, user):
        """See `ISalesforceVoucherProxy`."""
        server = self.server_proxy
        response = server.getAllVouchers(user.openid_identifier)
        results = self.parseResponse(response)
        return [Voucher(voucher) for voucher in results]

    def getServerStatus(self):
        """See `ISalesforceVoucherProxy`."""
        response = self.server_proxy.getServerStatus()
        return self.parseResponse(response)

    def getVoucher(self, voucher_id):
        """See `ISalesforceVoucherProxy`."""
        response = self.server_proxy.getVoucher(voucher_id)
        voucher = self.parseResponse(response)
        if voucher is not None:
            voucher = Voucher(voucher)
        return voucher

    def redeemVoucher(self, voucher_id, user, project):
        """See `ISalesforceVoucherProxy`."""
        response = self.server_proxy.redeemVoucher(
            voucher_id,
            user.openid_identifier,
            project.id,
            project.displayname)
        self.parseResponse(response)
        return True

    def updateProjectName(self, project):
        """See `ISalesforceVoucherProxy`."""
        response = self.server_proxy.updateProjectName(
            project.id,
            project.displayname)
        return self.parseResponse(response)
