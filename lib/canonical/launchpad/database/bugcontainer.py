
from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from canonical.launchpad.interfaces import IBugContainer

class BugContainerBase(object):
    implements(IBugContainer, IAddFormCustomization)
    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'


