# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug domain vocabularies"""

__metaclass__ = type
__all__ = []

from sqlobject import OR

from lp.registry.vocabularies import DistributionVocabulary


class UsesBugsDistributionVocabulary(DistributionVocabulary):
    """Distributions that use Launchpad to track bugs."""

    @property
    def _filter(self):
        if self.context is None:
            distro_id = 0
        else:
            distro_id = self.context.id
        return OR(
            self._table.q.official_malone == True,
            self._table.id == distro_id)
