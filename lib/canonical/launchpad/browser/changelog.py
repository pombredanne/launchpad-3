import os, os.path

class ChangeLog(object):
    def __init__(self, context, request):

        self.context = context
        self.request = request

    def changelog(self):
        lines = open(os.path.join(
                os.path.dirname(__file__),
                os.pardir, os.pardir, os.pardir, os.pardir,
                'doc', 'changelog.txt',
                )).readlines()
        lines = [l for l in lines if not l.startswith('#')]
        return ''.join(lines)
    changelog = property(changelog)
