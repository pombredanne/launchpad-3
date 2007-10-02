# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Badges are shown to indicate either content state or links.

Badges are shown in two main places:
 * listing views
 * main content pages.
"""

__metaclass__ = type
__all__ = [
    'Badge',
    'BadgeMethodDelegator',
    'HasBadgeBase',
    'IHasBadges',
    'STANDARD_BADGES',
    ]

from zope.interface import Interface, Attribute, implements


class Badge:
    """A badge renders to an HTML image tag of the appropriate size."""

    def __init__(self, icon_image, logo_image, alt='', title=''):
        self.icon_image = icon_image
        self.logo_image = logo_image
        self.alt = alt
        self.title = title

    def icon(self):
        return ('<img alt="%s" width="14" height="14" src="%s", title="%s"/>'
                % (self.alt, self.icon_image, self.title))

    def logo(self):
        return ('<img alt="%s" width="64" height="64" src="%s", title="%s"/>'
                % (self.alt, self.logo_image, self.title))


STANDARD_BADGES = {
    'bug': Badge('/@@/bug', '/@@bug-logo',
                 'bug', 'Linked to a bug'),
    'spec': Badge('/@@/blueprint', '/@@blueprint-logo',
                  'blueprint', 'Linked to a blueprint'),
    'branch': Badge('/@@/branch', '/@@branch-logo',
                    'branch', 'Linked to a branch'),
    'private': Badge('/@@/private', '/@@private-logo',
                    'private', 'Private'),
    }


class IHasBadges(Interface):
    """Badges should honour the visibility of the linked objects."""

    badges = Attribute('A list of badge names that could be visible.')

    def getVisibleBadges():
        """Return a list of `Badge` objects that the logged in user can see."""

    def isBadgeVisible(badge_name):
        """Is the badge_name badge visible for the logged in user?"""

    def getBadge(badge_name):
        """Return the badge instance for the name specified."""


class HasBadgeBase:
    """A base implementation"""
    implements(IHasBadges)

    def getVisibleBadges(self):
        """See `IHasBadges`."""
        result = []
        for badge_name in self.badges:
            if self.isBadgeVisible(badge_name):
                result.append(self.getBadge(badge_name))
        return result

    def isBadgeVisible(self, badge_name):
        """See `IHasBadges`."""
        return False

    def getBadge(self, badge_name):
        """See `IHasBadges`."""
        # Can be overridden to provide non-standard badges.
        return STANDARD_BADGES.get(badge_name)


class BadgeMethodDelegator(HasBadgeBase):
    """Delegates the visibility check of badges to specific methods."""

    def isBadgeVisible(self, badge_name):
        """Translate into a method name, and call that."""
        method_name = "is%sBadgeVisible" % badge_name.capitalize()
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        else:
            raise NotImplementedError(method_name)
