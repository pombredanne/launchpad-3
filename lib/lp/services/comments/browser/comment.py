# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['download_body']

from lp.services.webapp.publisher import DataDownloadView


class CommentBodyDownloadView(DataDownloadView):
    """Download the body text of a comment."""

    content_type = 'text/plain'

    @property
    def filename(self):
        return 'comment-%d.txt' % self.context.index

    def getBody(self):
        return self.context.body_text


def download_body(comment, request):
    """Respond to a request with the full message body as a download."""
    return CommentBodyDownloadView(comment, request)()
