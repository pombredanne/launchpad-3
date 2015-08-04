# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Email notifications for code review comments."""


__metaclass__ = type
__all__ = [
    'build_inline_comments_section',
    'CodeReviewCommentMailer',
    ]

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import CodeReviewNotificationLevel
from lp.code.interfaces.branchmergeproposal import (
    ICodeReviewCommentEmailJobSource,
    )
from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineCommentSet,
    )
from lp.code.mail import patches
from lp.code.mail.branchmergeproposal import BMPMailer
from lp.services.mail.sendmail import (
    append_footer,
    format_address,
    )
from lp.services.webapp import canonical_url


def send(comment, event):
    """Send a copy of the code review comments to branch subscribers."""
    getUtility(ICodeReviewCommentEmailJobSource).create(comment)


class CodeReviewCommentMailer(BMPMailer):
    """Send email about creation of a CodeReviewComment."""

    def __init__(self, code_review_comment, recipients, message_id=None):
        """Constructor."""
        self.code_review_comment = code_review_comment
        self.message = code_review_comment.message
        from_person = self.message.owner
        from_address = format_address(
            from_person.displayname, from_person.preferredemail.email)
        merge_proposal = code_review_comment.branch_merge_proposal
        BMPMailer.__init__(
            self, self.message.subject, None, recipients, merge_proposal,
            from_address, message_id=message_id)
        self.attachments = []
        original_email = self.code_review_comment.getOriginalEmail()
        if original_email is not None:
            # The original_email here is wrapped in a zope security proxy,
            # which is not helpful as there is no interface defined for
            # emails, so strip it off here.
            original_email = removeSecurityProxy(original_email)
            # The attachments for the code review comment are actually
            # library file aliases.
            display_aliases, other_aliases = (
                self.code_review_comment.getAttachments())
            include_attachments = set()
            for alias in display_aliases:
                include_attachments.add((alias.filename, alias.mimetype))
            for part in original_email.walk():
                if part.is_multipart():
                    continue
                filename = part.get_filename() or 'unnamed'
                if part['content-type'] is None:
                    content_type = 'application/octet-stream'
                else:
                    content_type = part['content-type']
                if (filename, content_type) in include_attachments:
                    payload = part.get_payload(decode=True)
                    self.attachments.append(
                        (payload, filename, content_type))
        self._generateBodyBits()

    @classmethod
    def forCreation(klass, code_review_comment):
        """Return a mailer for CodeReviewComment creation."""
        merge_proposal = code_review_comment.branch_merge_proposal
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        return klass(
            code_review_comment, recipients,
            code_review_comment.message.rfc822msgid)

    def _getSubject(self, email, recipient):
        """Don't do any string template insertions on subjects."""
        return self.code_review_comment.message.subject

    def _generateBodyBits(self):
        """Pre-generate the bits of the body email that don't change."""
        if self.code_review_comment.vote is None:
            self.body_prefix = ''
        else:
            if self.code_review_comment.vote_tag is None:
                vote_tag = ''
            else:
                vote_tag = ' ' + self.code_review_comment.vote_tag
            self.body_prefix = 'Review: %s%s\n\n' % (
                self.code_review_comment.vote.title, vote_tag)
        self.body_main = self.message.text_contents

        # Append the Inline Comments section to the message body if there
        # are associated inline comments.
        inline_comment = getUtility(
            ICodeReviewInlineCommentSet).getByReviewComment(
                self.code_review_comment)
        if inline_comment is not None:
            self.body_main += build_inline_comments_section(
                inline_comment.comments, inline_comment.previewdiff.text)

        self.proposal_url = canonical_url(self.merge_proposal)

    def _getBody(self, email, recipient):
        """Return the complete body to use for this email.

        If there was a vote, we prefix "Review: " to the message.
        We always append information about why this message was sent.  If
        there is an existing footer, we append it to that.  Otherwise, we
        we insert a new footer.
        """
        # Include both the canonical_url for the proposal and the reason
        # in the footer to the email.
        reason, rationale = self._recipients.getReason(email)
        footer = "%(proposal_url)s\n%(reason)s\n" % {
            'proposal_url': self.proposal_url,
            'reason': reason.getReason()}
        return ''.join((
            self.body_prefix, append_footer(self.body_main, footer)))

    def _getHeaders(self, email):
        """Return the mail headers to use."""
        headers = BMPMailer._getHeaders(self, email)
        headers['Message-Id'] = self.message.rfc822msgid
        if self.message.parent is not None:
            headers['In-Reply-To'] = self.message.parent.rfc822msgid
        return headers

    def _getToAddresses(self, recipient, email):
        """Provide to addresses as if this were a mailing list.

        CodeReviewComments which are not replies shall list the merge proposer
        as their to address.  CodeReviewComments which are replies shall list
        the parent comment's author as their to address.
        """
        if self.message.parent is None:
            to_person = self.merge_proposal.registrant
        else:
            to_person = self.message.parent.owner
        if to_person.hide_email_addresses:
            return [self.merge_proposal.address]
        # Ensure the to header matches the envelope-to address.
        if to_person == recipient:
            to_email = email
        else:
            to_email = to_person.preferredemail.email
        to = [format_address(to_person.displayname, to_email)]
        return to

    def _addAttachments(self, ctrl, email):
        """Add the attachments from the original message."""
        # Only reattach the display_aliases.
        for content, filename, content_type in self.attachments:
            # Append directly to the controller's list.
            ctrl.addAttachment(
                content, content_type=content_type, filename=filename)


def format_comment(comment):
    """Returns a list of correctly formatted comment(s)."""
    comment_lines = []
    if comment is not None:
        comment_lines.append('')
        comment_lines.extend(comment.splitlines())
        comment_lines.append('')
    return comment_lines


def build_inline_comments_section(comments, diff_text):
    """Return a formatted text section with contextualized comments.

    Hunks without comments are skipped to limit verbosity.
    Comments can be rendered after patch headers, hunk context lines,
    and hunk lines.
    """
    diff_lines = diff_text.splitlines(True)

    diff_patches = patches.parse_patches(
        diff_lines, allow_dirty=True, keep_dirty=True)
    result_lines = []
    line_count = 0  # track lines in original diff

    for patch in diff_patches:
        patch_lines = []
        dirty_head = []
        dirty_comment = False
        patch_comment = False

        if isinstance(patch, dict) and 'dirty_head' in patch:
            for line in patch['dirty_head']:
                dirty_head.append(u'> %s' % line.rstrip('\n'))
                line_count += 1  # inc for dirty headers
                comment = comments.get(str(line_count))
                if comment:
                    dirty_head.extend(format_comment(comment))
                    dirty_comment = True
            patch = patch['patch']

        # call type here as patch is an instance of both Patch and BinaryPatch
        if type(patch) is patches.BinaryPatch:
            if dirty_comment:
                result_lines.extend(dirty_head)
                result_lines.append(u'> %s' % str(patch).rstrip('\n'))
            line_count += 1
            comment = comments.get(str(line_count))
            if comment:
                result_lines.extend(format_comment(comment))
            continue

        for ph in patch.get_header().splitlines():
            line_count += 1  # inc patch headers
            comment = comments.get(str(line_count))

            patch_lines.append('> {0}'.format(ph))
            if comment:
                patch_lines.extend(format_comment(comment))
                patch_comment = True

        keep_hunks = []  # preserve hunks with comments
        for hunk in patch.hunks:
            hunk_lines = []
            hunk_comment = False

            # add context line (hunk header)
            line_count += 1  # inc hunk context line
            hunk_lines.append(u'> %s' % hunk.get_header().rstrip('\n'))

            # comment for context line (hunk header)
            comment = comments.get(str(line_count))
            if comment:
                hunk_lines.extend(format_comment(comment))
                hunk_comment = True

            for hunk_line in hunk.lines:
                # A single HunkLine can actually represent multiple
                # lines in the "No newline at end of file" case.
                hunk_line = str(hunk_line)
                for line in hunk_line.splitlines():
                    line_count += 1  # inc hunk lines
                    hunk_lines.append(u'> %s' % line.rstrip('\n').decode(
                        'utf-8', 'replace'))
                    comment = comments.get(str(line_count))
                    if comment:
                        hunk_lines.extend(format_comment(comment))
                        hunk_comment = True

            # preserve hunks for context if comment in patch header
            if patch_comment or hunk_comment:
                keep_hunks.extend(hunk_lines)

        # Add entire patch and hunks to result if comment found
        if patch_comment or keep_hunks:
            result_lines.extend(dirty_head)
            result_lines.extend(patch_lines)
            result_lines.extend(keep_hunks)
        elif dirty_comment:
            result_lines.extend(dirty_head)

    result_text = '\n'.join(result_lines)
    return '\n\nDiff comments:\n\n%s\n\n' % result_text
