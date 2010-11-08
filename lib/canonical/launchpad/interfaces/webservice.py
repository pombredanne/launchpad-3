# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice."""

__metaclass__ = type
__all__ = [
    'IEmailAddress',
    'IMessage',
    'ITemporaryBlobStorage',
    'ITemporaryStorageManager',
    'IWebServiceApplication',
    ]

from canonical.launchpad.interfaces.launchpad import IWebServiceApplication

from canonical.launchpad.interfaces.emailaddress import IEmailAddress
from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.interfaces.temporaryblogstorage import (
    ITemporaryBlobStorage,
    ITemporaryStorageManager,
    )
