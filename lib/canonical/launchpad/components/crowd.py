# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import ICrowd, IPerson, ITeam


class CrowdOfOnePerson:
    implements(ICrowd)
    __used_for__ = IPerson

    def __init__(self, person):
        self.person = person

    def __contains__(self, person_or_team):
        return person_or_team.id == self.person.id

    def __add__(self, crowd):
        return CrowdsAddedTogether(crowd, self)


class CrowdOfOneTeam:
    implements(ICrowd)
    __used_for__ = ITeam

    def __init__(self, team):
        self.team = team

    def __contains__(self, person_or_team):
        if person_or_team.id == self.team.id:
            return True
        return person_or_team.inTeam(self.team)

    def __add__(self, crowd):
        return CrowdsAddedTogether(crowd, self)


class CrowdsAddedTogether:

    implements(ICrowd)

    def __init__(self, *crowds):
        self.crowds = crowds

    def __contains__(self, person_or_team):
        for crowd in self.crowds:
            if person_or_team in crowd:
                return True
        return False

    def __add__(self, crowd):
        return CrowdsAddedTogether(crowd, *self.crowds)


# XXX ddaa 2005-04-01: This shouldn't be in components
class AnyPersonCrowd:

    implements(ICrowd)

    def __contains__(self, person_or_team):
        return IPerson.providedBy(person_or_team)

    def __add__(self, crowd):
        return CrowdsAddedTogether(crowd, self)

# XXX ddaa 2005-04-01: This shouldn't be in components
class EmptyCrowd:

    implements(ICrowd)

    def __contains__(self, person_or_team):
        return False

    def __add__(self, crowd):
        return crowd


