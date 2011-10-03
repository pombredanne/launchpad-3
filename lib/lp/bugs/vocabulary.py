# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug domain vocabularies"""

__metaclass__ = type
__all__ = [
    'UsesBugsDistributionVocabulary',
    ]

from sqlobject import OR

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.vocabularies import DistributionVocabulary


class UsesBugsDistributionVocabulary(DistributionVocabulary):
    """Distributions that use Launchpad to track bugs.

    If the context is a distribution, it is always included in the
    vocabulary. Historic data is not invalidated if a distro stops
    using Launchpad to track bugs. This vocabulary offers the correct
    choices of distributions at this moment.
    """

    def __init__(self, context=None):
        super(UsesBugsDistributionVocabulary, self).__init__(context=context)
        self.distribution = IDistribution(self.context, None)

    @property
    def _filter(self):
        if self.distribution is None:
            distro_id = 0
        else:
            distro_id = self.distribution.id
        return OR(
            self._table.q.official_malone == True,
            self._table.id == distro_id)
