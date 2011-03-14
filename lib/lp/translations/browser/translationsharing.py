# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views and mixins to use for translation sharing."""

__metaclass__ = type

__all__ = [
    'TranslationSharingDetailsMixin',
    ]


from canonical.launchpad.webapp import canonical_url


class TranslationSharingDetailsMixin:
    """Mixin for views that need to display translation details link.

    View using this need to implement is_sharing, can_edit_sharing_details
    and getTranslationTarget().
    """

    def is_sharing(self):
        """Whether this object is sharing translations or not."""
        raise NotImplementedError

    def can_edit_sharing_details(self):
        """If the current user can edit sharing details."""
        raise NotImplementedError

    def getTranslationTarget(self):
        """Return either a productseries or a sourcepackage."""
        raise NotImplementedError

    def sharing_details(self):
        """Construct the link to the sharing details page."""
        tag_template = (
            '<a class="sprite %(icon)s" id="sharing-details"'
            ' href="%(href)s/+sharing-details">%(text)s</a>')

        if self.can_edit_sharing_details():
            icon = 'edit'
            if self.is_sharing():
                text = "Edit sharing details"
            else:
                text = "Set up sharing"
        else:
            if self.is_sharing():
                icon = 'info'
                text = "View sharing details"
            else:
                return ""
        href = canonical_url(
            self.getTranslationTarget(),
            rootsite='translations',
            )
        return tag_template % dict(icon=icon, text=text, href=href)
