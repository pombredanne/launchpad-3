# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Error logging facilities."""

__metaclass__ = type

from zope.app.errorservice import RootErrorReportingService
from zope.app.errorservice.interfaces import ILocalErrorReportingService

from zope.security.checker import ProxyFactory, NamesChecker
from zope.security.proxy import removeSecurityProxy


class ErrorReportingService(RootErrorReportingService):
    """Error reporting service that copies tracebacks to the log by default.
    """
    copy_to_zlog = True


globalErrorService = ErrorReportingService()

globalErrorUtility = ProxyFactory(
    removeSecurityProxy(globalErrorService),
    NamesChecker(ILocalErrorReportingService.names())
    )

