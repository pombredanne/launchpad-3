# Copyright 2007 Canonical Ltd.  All rights reserved.

__all__ = ['HARDCODED_COMPONENT_ORDER', 'ELIGIBLE_DOMINATION_STATES']

from canonical.launchpad.interfaces import PackagePublishingStatus

# XXX: if people actually start seriously using ComponentSelections this
# will need to be revisited. For instance, adding new components will
# break places which use this list. -- kiko, 2006-08-23
HARDCODED_COMPONENT_ORDER = [
    'main', 'restricted', 'universe', 'multiverse', 'partner']

# This list contains the states that are eligible for domination and death
# row processing.
ELIGIBLE_DOMINATION_STATES = [
    PackagePublishingStatus.SUPERSEDED,
    PackagePublishingStatus.DELETED,
    PackagePublishingStatus.OBSOLETE,
    ]
