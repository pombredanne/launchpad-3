# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for accessing the external Salesforce proxy."""

__metaclass__ = type

__all__ = [
    'SalesforceVoucherProxy',
    'SalesforceVoucherProxyException',
    'Voucher',
    ]


from xmlrpclib import Fault, ServerProxy, SafeTransport

from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.salesforce import (
    ISalesforceVoucher, ISalesforceVoucherProxy)


class SalesforceVoucherProxyException(Exception):
    """Exception raised on failed call to the SalesforceVoucherProxy."""


class SFDCError(SalesforceVoucherProxyException):
    """An exception was reported by salesforce.com."""


class SVPNotFoundException(SalesforceVoucherProxyException):
    """A named object was not found."""


class SVPAlreadyRedeemedException(SalesforceVoucherProxyException):
    """The voucher has already been redeemed."""


class SVPNotAllowedException(SalesforceVoucherProxyException):
    """The operation is not allowed by the current user."""


def fault_mapper(func):
    """Decorator to catch Faults and map them to our exceptions."""

    errorcode_map = dict(SFDCError=SFDCError,
                         NotFound=SVPNotFoundException,
                         AlreadyRedeemed=SVPAlreadyRedeemedException,
                         NotAllowed=SVPNotAllowedException)

    def decorator(voucher, *args, **kwargs):
        try:
            results = func(voucher, *args, **kwargs)
        except Fault, fault:
            exception = errorcode_map.get(fault.faultCode,
                                          SalesforceVoucherProxyException)
            raise exception(fault.faultString)
        return results
    return decorator


class Voucher:
    """A Commercial Subscription voucher."""

    implements(ISalesforceVoucher)

    def __init__(self, values):
        """Initialize using the values as returned from the SF proxy.
        :param values['voucher_id']: voucher id.
        :param values['status']: string representing the redemption status.
        :param values['term']: integer representing number of months of
            subscription the voucher enables.
        :param values['project_id']: integer id for the project this voucher
            has been redeemed  against.  If unredeemed this entry is absent.
        """
        self.voucher_id = values.get('voucher_id')
        self.status = values.get('status')
        self.term_months = values.get('term_months')
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
        return "%s,%s,%s,%s" % (self.voucher_id,
                                self.status,
                                self.term_months,
                                project_name)


class SalesforceVoucherProxy:

    implements(ISalesforceVoucherProxy)

    def __init__(self):
        self.xmlrpc_transport = SafeTransport()

    @cachedproperty
    def url(self):
        """Get the proxy URL with port."""
        return "%s:%d" % (config.commercial.voucher_proxy_url,
                          config.commercial.voucher_proxy_port)
    @property
    def server(self):
        """See `ISalesforceVoucherProxy`."""
        # This is not a cachedproperty as each use needs a new proxy.
        return ServerProxy(self.url,
                           transport=self.xmlrpc_transport,
                           allow_none=True)

    @fault_mapper
    def getUnredeemedVouchers(self, user):
        """See `ISalesforceVoucherProxy`."""
        vouchers = self.server.getUnredeemedVouchers(
            user.openid_identifier)
        return [Voucher(voucher) for voucher in vouchers]

    @fault_mapper
    def getAllVouchers(self, user):
        """See `ISalesforceVoucherProxy`."""
        vouchers = self.server.getAllVouchers(user.openid_identifier)
        return [Voucher(voucher) for voucher in vouchers]

    @fault_mapper
    def getServerStatus(self):
        """See `ISalesforceVoucherProxy`."""
        status = self.server.getServerStatus()
        return status

    @fault_mapper
    def getVoucher(self, voucher_id):
        """See `ISalesforceVoucherProxy`."""
        voucher = self.server.getVoucher(voucher_id)
        if voucher is not None:
            voucher = Voucher(voucher)
        return voucher

    @fault_mapper
    def redeemVoucher(self, voucher_id, user, project):
        """See `ISalesforceVoucherProxy`."""
        status = self.server.redeemVoucher(voucher_id,
                                           user.openid_identifier,
                                           project.id,
                                           project.displayname)
        return status

    @fault_mapper
    def updateProjectName(self, project):
        """See `ISalesforceVoucherProxy`."""
        num_updated = self.server.updateProjectName(project.id,
                                                    project.displayname)
        return num_updated
