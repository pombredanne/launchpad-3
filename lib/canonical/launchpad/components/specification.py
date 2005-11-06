# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Components related to specifications."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import ISpecificationDelta

class SpecificationDelta:
    """See canonical.launchpad.interfaces.ISpecificationDelta."""
    implements(ISpecificationDelta)
    def __init__(self, specification, user, title=None,
        summary=None, specurl=None, productseries=None, distrorelease=None,
        milestone=None, name=None, priority=None, status=None, target=None,
        bugs_linked=None, bugs_unlinked=None):
        self.specification = specification
        self.user = user
        self.title = title
        self.summary = summary
        self.specurl = specurl
        productseries = productseries
        distrorelease = distrorelease
        milestone = milestone
        self.name = name
        priority = priority
        status = status
        target = target
        bugs_linked = bugs_linked
        bugs_unlinked = bugs_unlinked

