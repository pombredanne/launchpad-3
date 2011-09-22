# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug domain vocabularies"""

__metaclass__ = type
__all__ = []

from sqlobject import OR

from lp.registry.vocabularies import DistributionVocabulary


class UsesBugsDistributionVocabulary(DistributionVocabulary):
    """Active distributions that use Launchpad to track bugs."""
