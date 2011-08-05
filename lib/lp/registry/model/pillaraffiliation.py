# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters to figure out affiliations between people and pillars/bugs etc.

When using a person in a given context, for example as a selection item in a
picker used to choose a bug task assignee, it is important to provide an
indication as to how that person may be affiliated with the context. Amongst
other reasons, this provides a visual cue that the correct person is being
selected for example.

The adapters herein are provided for various contexts so that for a given
person, the relevant affiliation details may be determined.

"""

__metaclass__ = type

__all__ = [
    'IHasAffiliation',
    ]

from collections import namedtuple

from zope.component import adapter
from zope.interface import (
    implements,
    Interface,
    )

from canonical.launchpad.interfaces.launchpad import IHasIcon
from lp.answers.interfaces.question import IQuestion
from lp.blueprints.interfaces.specification import ISpecification
from lp.bugs.interfaces.bugtask import IBugTask
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.productseries import IProductSeries


class IHasAffiliation(Interface):
    """The affiliation status of a person with a context."""

    def getAffiliationBadge(person):
        """Return the badge for the type of affiliation the person has.

        The return value is a tuple: (url, alt).

        If the person has no affiliation with this object, return None.
        """

BadgeDetails = namedtuple('BadgeDetails', ('url', 'alt_text'))


@adapter(Interface)
class PillarAffiliation(object):
    """Default affiliation adapter.

    Subclasses may need to override getPillar() in order to provide the pillar
    entity for which affiliation is to be determined. The default is just to
    use the context object directly.
    """

    implements(IHasAffiliation)

    def __init__(self, context):
        self.context = context

    def getPillar(self):
        return self.context

    def _getAffiliationDetails(self, person, pillar):
        """ Return the affiliation information for a person, if any.

        A person is affiliated with a pillar if they are in the list of
        drivers or are the maintainer.
        """
        if person.inTeam(pillar.owner):
            return pillar.displayname, 'maintainer'
        for driver in pillar.drivers:
            if person.inTeam(driver):
                return pillar.displayname, 'driver'
        return  None

    def getAffiliationBadge(self, person):
        """ Return the affiliation badge details for a person given a context.
        """
        pillar = self.getPillar()
        affiliation_details = self._getAffiliationDetails(person, pillar)
        if not affiliation_details:
            return None

        def getIconUrl(context, pillar, default_url):
            if IHasIcon.providedBy(context) and context.icon is not None:
                icon_url = context.icon.getURL()
                return icon_url
            if IHasIcon.providedBy(pillar) and pillar.icon is not None:
                icon_url = context.icon.getURL()
                return icon_url
            return default_url

        alt_text = "%s %s" % affiliation_details
        if IDistribution.providedBy(pillar):
            default_icon_url = "/@@/distribution-badge"
        else:
            default_icon_url = "/@@/product-badge"
        icon_url = getIconUrl(self.context, pillar, default_icon_url)
        return BadgeDetails(icon_url, alt_text)


@adapter(IBugTask)
class BugTaskPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for bug tasks."""
    def getPillar(self):
        return self.context.pillar

    def _getAffiliationDetails(self, person, pillar):
        """ A person is affiliated with a bugtask based on (in order):
        - owner of bugtask pillar
        - driver of bugtask pillar
        - bug supervisor of bugtask pillar
        - security contact of bugtask pillar
        """
        result = super(BugTaskPillarAffiliation, self)._getAffiliationDetails(
            person, pillar)
        if result is not None:
            return result
        if person.inTeam(pillar.bug_supervisor):
            return pillar.displayname, 'bug supervisor'
        if person.inTeam(pillar.security_contact):
            return pillar.displayname, 'security contact'


@adapter(IDistroSeries)
class DistroSeriesPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for distroseries."""
    def getPillar(self):
        return self.context.distribution


@adapter(IProductSeries)
class ProductSeriesPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for productseries."""
    def getPillar(self):
        return self.context.product


@adapter(ISpecification)
class SpecificationPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for blueprints."""
    def getPillar(self):
        return (self.context.target)


@adapter(IQuestion)
class QuestionPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for questions."""
    def getPillar(self):
        return self.context.product or self.context.distribution

    def _getAffiliationDetails(self, person, pillar):
        """ A person is affiliated with a question based on (in order):
        - answer contact for question target
        - owner of question target
        - driver of question target
        """
        target = self.context.target
        answer_contacts = target.answer_contacts
        for answer_contact in answer_contacts:
            if person.inTeam(answer_contact):
                return target.displayname, 'answer contact'
        return super(QuestionPillarAffiliation, self)._getAffiliationDetails(
            person, pillar)
