# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.interfaces import IPerson

@block_implicit_flushes
def notify_bug_modified(bug, event):
    """Handle bug change events.
    
    Subscribe the security contacts for a bug when it
    becomes security-related.
    """
    if (event.object.security_related and
        not event.object_before_modification.security_related):
        # The bug turned to be security-related, 
        # subscribe the security contact.
        for pillar in bug.affected_pillars:
            if pillar.security_contact is not None:
                bug.subscribe(pillar.security_contact, IPerson(event.user))

