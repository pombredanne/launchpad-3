from bzrlib.commands import Command

class cmd_test(Command):
    def run(self):
        print 'foo'

class cmd_demo(Command):
    def run(self):
        print 'foo'

class cmd_update_image(Command):
    def run(self):
        print 'foo'
