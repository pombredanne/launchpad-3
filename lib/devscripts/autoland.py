"""Land an approved merge proposal."""

import os
import sys

from launchpadlib.launchpad import (
    Launchpad, EDGE_SERVICE_ROOT, STAGING_SERVICE_ROOT)
from lazr.uri import URI

DEV_SERVICE_ROOT = 'https://api.launchpad.dev/beta/'
LPNET_SERVICE_ROOT = 'https://api.launchpad.net/beta/'

# Given the merge proposal URL, get:
# - [DONE] the reviewer
# - [DONE] the UI reviewer
# - [DONE] the DB reviewer
# - the release-critical reviewer
# - [DONE] the commit message
# - the branch
# - the target branch
# - whether or not it has been approved
# - the branch owner

# Given the branch owner, get their email

# If the commit message is not given, insist on one from the command line

# If the review has not been approved, warn.

# Given all of this, assemble the ec2test command line.

# XXX: How do you do TDD of a launchpadlib program?


class LaunchpadBranchLander:

    name = 'launchpad-branch-lander'
    cache_dir = '~/.launchpadlib/cache'

    def __init__(self, launchpad):
        self._launchpad = launchpad

    @classmethod
    def load(cls, service_root):
        cache_dir = os.path.expanduser(cls.cache_dir)
        # XXX: If cached data invalid, hard to delete & try again.
        launchpad = Launchpad.login_with(cls.name, service_root, cache_dir)
        return cls(launchpad)

    def load_merge_proposal(self, mp_url):
        """Get the merge proposal object for the 'mp_url'."""
        web_mp_uri = URI(mp_url)
        api_mp_uri = self._launchpad._root_uri.append(
            web_mp_uri.path.lstrip('/'))
        return self._launchpad.load(str(api_mp_uri))

    def get_codehosting_url(self, branch):
        self._launchpad._root_uri.replace(
            path=branch.unique_name,
            scheme='bzr+ssh')


def get_bugs_clause(bugs):
    """Return the bugs clause of a commit message.

    :param bugs: A collection of `IBug` objects.
    :return: A string of the form "[bug=A,B,C]".
    """
    if not bugs:
        return ''
    return '[bug=%s]' % ','.join(str(bug.id) for bug in bugs)


def get_reviews(mp):
    """Return a dictionary of all Approved reviewes on 'mp'.

    Used to determine who has actually approved a branch for landing. The key
    of the dictionary is the type of review, and the value is the list of
    people who have voted Approve with that type.

    Common types include 'code', 'db', 'ui' and of course `None`.
    """
    reviews = {}
    for vote in mp.votes:
        comment = vote.comment
        if comment is None or comment.vote != "Approve":
            continue
        reviewers = reviews.setdefault(vote.review_type, [])
        reviewers.append(vote.reviewer)
    return reviews


def get_reviewer_handle(reviewer):
    """Get the handle for 'reviewer'.

    The handles of reviewers are included in the commit message for Launchpad
    changes. Historically, these handles have been the IRC nicks. Thus, if
    'reviewer' has an IRC nickname for Freenode, we use that. Otherwise we use
    their Launchpad username.

    :param reviewer: A launchpadlib `IPerson` object.
    :return: unicode text.
    """
    irc_handles = reviewer.irc_nicknames
    for handle in irc_handles:
        if handle.network == 'irc.freenode.net':
            return handle.nickname
    return reviewer.name


def get_bugs(mp):
    return mp.source_branch.linked_bugs


def get_reviewer_clause(reviewers):
    """Get the reviewer section of a commit message, given the reviewers.

    :param reviewers: A dict mapping review types to lists of reviewers, as
        returned by 'get_reviews'.
    :return: A string like u'[r=foo,bar][ui=plop]'.
    """
    code_reviewers = reviewers.get(None, [])
    code_reviewers.extend(reviewers.get('code', []))
    code_reviewers.extend(reviewers.get('db', []))
    ui_reviewers = reviewers.get('ui', [])
    if ui_reviewers:
        ui_clause = ','.join(reviewer.name for reviewer in ui_reviewers)
    else:
        ui_clause = 'none'
    return '[r=%s][ui=%s]' % (
        ','.join(reviewer.name for reviewer in code_reviewers),
        ui_clause)


def get_lp_commit_message(mp):
    """Get the Launchpad-style commit message for a merge proposal."""
    # XXX: Point to docs describing the rules for this.
    reviews = get_reviews(mp)
    bugs = get_bugs(mp)
    return '%s%s %s' % (
        get_reviewer_clause(reviews),
        get_bugs_clause(bugs),
        mp.commit_message)


def get_bazaar_host(api_root):
    """Get the Bazaar service for the given API root."""
    # XXX: This is only needed because Launchpad doesn't expose the push URL
    # for branches.
    if api_root == EDGE_SERVICE_ROOT:
        return 'bazaar.launchpad.net'
    elif api_root == DEV_SERVICE_ROOT:
        return 'bazaar.launchpad.dev'
    elif api_root == STAGING_SERVICE_ROOT:
        return 'bazaar.staging.launchpad.net'
    elif api_root == LPNET_SERVICE_ROOT:
        return 'bazaar.launchpad.net'
    else:
        raise ValueError(
            'Cannot determine Bazaar host. "%s" not a recognized Launchpad '
            'API root.' % (api_root,))


def main(argv):
    lander = LaunchpadBranchLander.load(DEV_SERVICE_ROOT)
    mp = lander.load_merge_proposal(argv[1])
    print get_lp_commit_message(mp)
    return 0


if __name__ == '__main__':
    os._exit(main(sys.argv))
