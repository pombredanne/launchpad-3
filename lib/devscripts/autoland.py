"""Land an approved merge proposal."""

from pprint import pprint
import os
import sys

from launchpadlib.launchpad import Launchpad
from lazr.uri import URI

# Given the merge proposal URL, get:
# - the reviewer
# - the UI reviewer
# - the DB reviewer
# - the release-critical reviewer
# - the commit message
# - the branch
# - the target branch
# - whether or not it has been approved
# - the branch owner

# Given a reviewer, get their IRC nick

# Given the branch owner, get their email

# If the commit message is not given, insist on one from the command line

# If the review has not been approved, warn.

# Given a merge proposal URL, get the object.

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
    if not bugs:
        return ''
    return '[bug=%s]' % ','.join(str(bug.id) for bug in bugs)


def get_reviews(mp):
    reviews = {}
    for vote in mp.votes:
        if vote.comment.vote != "Approve":
            continue
        reviewers = reviews.setdefault(vote.review_type, [])
        reviewers.append(vote.reviewer)
    return reviews


def get_bugs(mp):
    return mp.source_branch.linked_bugs


def get_lp_commit_message(mp, commit_message=None):
    if commit_message is None:
        commit_message = mp.commit_message
    pprint(commit_message)
    pprint(list(get_bugs(mp)))
    pprint(get_reviews(mp))


def main(argv):
    DEV_SERVICE_ROOT = 'https://api.launchpad.dev/beta/'
    lander = LaunchpadBranchLander.load(DEV_SERVICE_ROOT)
    mp = lander.load_merge_proposal(argv[1])
    get_lp_commit_message(mp)
    return 0


if __name__ == '__main__':
    os._exit(main(sys.argv))
