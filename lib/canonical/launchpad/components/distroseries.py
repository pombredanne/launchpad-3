# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters for DistroSeries."""

__metaclass__ = type
__all__ = [
    'distroseries_to_launchpadusage',
    ]

def distroseries_to_launchpadusage(distroseries):
    """Adapts IDistroSeries object to ILaunchpadUsage."""
    return distroseries.distribution
