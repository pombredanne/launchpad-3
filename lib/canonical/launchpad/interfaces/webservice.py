# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="canonical.launchpad.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

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
from lp.services.messages.interfaces.message import IMessage
from canonical.launchpad.interfaces.temporaryblobstorage import (
    ITemporaryBlobStorage,
    ITemporaryStorageManager,
    )
# XXX: JonathanLange 2010-11-09 bug=673083: Legacy work-around for circular
# import bugs.  Break this up into a per-package thing.
from canonical.launchpad.interfaces import _schema_circular_imports
_schema_circular_imports
