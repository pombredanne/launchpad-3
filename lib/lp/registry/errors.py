# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PrivatePersonLinkageError',
    'NameAlreadyTaken',
    ]

import httplib

class PrivatePersonLinkageError(ValueError):
    """An attempt was made to link a private person/team to something."""
    webservice_error(httplib.FORBIDDEN)

    
class NameAlreadyTaken(Exception):
    """The name given for a person is already in use by other person."""
    webservice_error(httplib.CONFLICT)


