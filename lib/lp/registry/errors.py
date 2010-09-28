# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PrivatePersonLinkageError',
    ]

import httplib

class PrivatePersonLinkageError(ValueError):
    """An attempt was made to link a private person/team to something."""
    # HTTP 400 -- BAD REQUEST
    # HTTP 403 would be better, but as this excpetion is raised inside a
    # validator, it will default to 400 anyway.
    webservice_error(httplib.BAD_REQUEST)
