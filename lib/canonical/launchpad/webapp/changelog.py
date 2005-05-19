import os, os.path
from canonical.lp import encoding

class ChangeLog(object):
    def __init__(self, context, request):

        self.context = context
        self.request = request

    def changelog(self):
        changelog_filename = os.path.join(
                os.path.dirname(__file__),
                os.pardir, os.pardir, os.pardir, os.pardir,
                'doc', 'changelog.txt',
                )
        # We don't need changelog.txt in the main development branch -
        # the only thing that cares is the dogfood branch so we can
        # add it there, avoiding maintaining this 3+MB file on dev
        # boxes.
        if not os.path.exists(changelog_filename):
            return u'%s does not exist' % changelog_filename
        lines = open(changelog_filename).readlines()
        lines = [l for l in lines if not l.startswith('#')]
        log = ''.join(lines)
        return encoding.guess(log)
    changelog = property(changelog)
