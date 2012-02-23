# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for access policy service."""


__metaclass__ = type

__all__ = [
    'IAccessPolicyService',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    export_read_operation,
    operation_for_version,
    )

from lp.app.interfaces.services import IService


class IAccessPolicyService(IService):

    export_as_webservice_entry(publish_web_link=False, as_of='beta')

    @export_read_operation()
    @operation_for_version('devel')
    def getAccessPolicies():
        """Return the access policy types."""
