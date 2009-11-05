# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Display classes relating to diff objects of one sort or another."""

__metaclass__ = type
__all__ = [
    'PreviewDiffFormatterAPI',
    ]


from canonical.launchpad import _
from canonical.launchpad.webapp.tales import ObjectFormatterAPI


class PreviewDiffFormatterAPI(ObjectFormatterAPI):
    """Formatter for preview diffs."""

    def url(self, view_name=None, rootsite=None):
        """Use the url of the librarian file containing the diff.
        """
        librarian_alias = self._context.diff_text
        if librarian_alias is None:
            return None
        else:
            return librarian_alias.getURL()

    def link(self, view_name):
        """The link to the diff should show the line count.

        Stale diffs will have a stale-diff css class.
        Diffs with conflicts will have a conflict-diff css class.
        Diffs with neither will have clean-diff css class.

        The title of the diff will show the number of lines added or removed
        if available.

        :param view_name: If not None, the link will point to the page with
            that name on this object.
        """
        title_words = []
        if self._context.conflicts is not None:
            style = 'conflicts-diff'
            title_words.append(_('CONFLICTS'))
        else:
            style = 'clean-diff'
        # Stale style overrides conflicts or clean.
        if self._context.stale:
            style = 'stale-diff'
            title_words.append(_('Stale'))

        if self._context.added_lines_count:
            title_words.append(
                _("%s added") % self._context.added_lines_count)

        if self._context.removed_lines_count:
            title_words.append(
                _("%s removed") % self._context.removed_lines_count)

        args = {
            'line_count': _('%s lines') % self._context.diff_lines_count,
            'style': style,
            'title': ', '.join(title_words),
            'url': self.url(view_name),
            }
        # Under normal circumstances, there will be an associated file,
        # however if the diff is empty, then there is no alias to link to.
        if args['url'] is None:
            return (
                '<span title="%(title)s" class="%(style)s">'
                '%(line_count)s</span>' % args)
        else:
            return (
                '<a href="%(url)s" title="%(title)s" class="%(style)s">'
                '<img src="/@@/download"/>&nbsp;%(line_count)s</a>' % args)
