# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Widgets related to `IPOTemplate`."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "POTemplateAdminSourcePackageNameWidget",
    "POTemplateEditSourcePackageNameWidget",
    ]

from lp.app.errors import UnexpectedFormData
from lp.app.widgets.popup import SourcePackageNameWidgetBase
from lp.registry.vocabularies import DistroSeriesVocabulary


class POTemplateEditSourcePackageNameWidget(SourcePackageNameWidgetBase):
    """A widget for associating a POTemplate with a SourcePackageName.

    This is suitable for use on POTemplate:+edit, where the distribution is
    fixed.
    """

    @property
    def distribution_name(self):
        distribution = self.getDistribution()
        if distribution is not None:
            return distribution.name
        else:
            return ''

    def getDistribution(self):
        """See `SourcePackageNameWidgetBase`."""
        return self.context.context.distribution


class POTemplateAdminSourcePackageNameWidget(SourcePackageNameWidgetBase):
    """A widget for associating a POTemplate with a SourcePackageName.

    This is suitable for use on POTemplate:+admin, where the distribution
    may be changed via the distroseries field.
    """

    @property
    def distroseries_id(self):
        return self._prefix + 'distroseries'

    def getDistribution(self):
        """See `SourcePackageNameWidgetBase`."""
        distroseries_token = self.request.form.get('field.distroseries')
        if distroseries_token is None:
            # Fall back to the POTemplate's current distribution.
            return self.context.context.distribution
        distroseries_vocab = DistroSeriesVocabulary()
        try:
            term = distroseries_vocab.getTermByToken(distroseries_token)
        except LookupError:
            raise UnexpectedFormData(
                "No such distribution series: %s" % distroseries_token)
        return term.value.distribution
