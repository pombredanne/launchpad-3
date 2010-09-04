# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['HARDCODED_COMPONENT_ORDER', 'ELIGIBLE_DOMINATION_STATES']

from lp.soyuz.enums import PackagePublishingStatus

# XXX: kiko 2006-08-23: if people actually start seriously using
# ComponentSelections this will need to be revisited. For instance, adding
# new components will break places which use this list.
HARDCODED_COMPONENT_ORDER = [
    'main', 'restricted', 'universe', 'multiverse', 'partner']

# This list contains the states that are eligible for domination and death
# row processing.
ELIGIBLE_DOMINATION_STATES = [
    PackagePublishingStatus.SUPERSEDED,
    PackagePublishingStatus.DELETED,
    PackagePublishingStatus.OBSOLETE,
    ]
