# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Badges are shown to indicate either content state or links.

Badges are shown in two main places:
 * listing views
 * main content pages.
"""

__metaclass__ = type
__all__ = [
    'Badge',
    'HasBadgeBase',
    'IHasBadges',
    'STANDARD_BADGES',
    ]

from zope.interface import Attribute, implements, Interface


class Badge:
    """A is badge is used to represent a link between two objects.

    This link is then rendered as small icons on the object listing
    views, and as larger images on the object content pages.
    """

    def __init__(self, icon_image=None, heading_image=None,
                 alt='', title='', id=''):
        self.small_image = icon_image
        self.large_image = heading_image
        self.alt = alt
        self.title = title
        self.id = id

    def renderIconImage(self):
        """Render the small image as an HTML img tag."""
        if self.small_image:
            return ('<img alt="%s" width="14" height="14" src="%s"'
                    ' title="%s"/>' % (self.alt, self.small_image, self.title))
        else:
            return ''

    def renderHeadingImage(self):
        """Render the large image as an HTML img tag."""
        if self.large_image:
            if self.id:
                id_attribute = 'id="%s"' % self.id
            else:
                id_attribute = ''
            return ('<img alt="%s" width="32" height="32" src="%s"'
                    ' title="%s" %s/>' % (
                    self.alt, self.large_image, self.title, id_attribute))
        else:
            return ''


STANDARD_BADGES = {
    'bug': Badge('/@@/bug', '/@@/bug-large',
                 'bug', 'Linked to a bug', 'bugbadge'),
    # XXX: TimPenhey 2007-10-10
    # No big blueprint exists, see bug 151171
    'blueprint': Badge('/@@/blueprint', None,
                       'blueprint', 'Linked to a blueprint'),
    'branch': Badge('/@@/branch', '/@@/branch-large',
                    'branch', 'Linked to a branch', 'branchbadge'),
    'private': Badge('/@@/private', '/@@/private-large',
                     'private', 'Private', 'privatebadge'),
    }


class IHasBadges(Interface):
    """A method to determine visible badges.

    Badges are used to show connections between different content objects, for
    example a BugBranch is a link between a bug and a branch.  To represent
    this link a bug has a branch badge, and the branch has a bug badge.

    Badges should honour the visibility of the linked objects.
    """

    def getVisibleBadges():
        """Return a list of `Badge` objects that the logged in user can see."""


class HasBadgeBase:
    """The standard base implementation for badge visibility.

    Derived classes need to provide a sequence of badge names that
    could be visible available through the attribute `badges`.

    The visibility of these badges are checked by calling a method like
    `isFooBadgeVisible` where Foo is the capitalised name of the badge.
    """
    implements(IHasBadges)

    badges = None

    def getVisibleBadges(self):
        """See `IHasBadges`."""
        result = []
        for badge_name in self.badges:
            if self._isBadgeVisible(badge_name):
                badge = self.getBadge(badge_name)
                if badge:
                    result.append(badge)
        return result

    def _isBadgeVisible(self, badge_name):
        """Is the badge_name badge visible for the logged in user?

        Delegate the determination to a method based on the name
        of the badge.
        """
        method_name = "is%sBadgeVisible" % badge_name.capitalize()
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        else:
            raise NotImplementedError(method_name)

    def getBadge(self, badge_name):
        """Return the badge instance for the name specified."""
        # Can be overridden to provide non-standard badges.
        return STANDARD_BADGES.get(badge_name)
