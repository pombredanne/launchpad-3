
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.database import Person
from canonical.lp import dbschema

# Bug Reports
class BugsAssignedReportView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        # default to showing bugs assigned to the logged in user.
        username = self.form.get('name', None)
        if username: self.context.user = Person.selectBy(name=username)[0]
        else:
            try: self.context.user = IPerson(self.request.principal)
            except TypeError: pass
        # default to showing even wishlist bugs
        self.context.minseverity = int(self.form.get('minseverity', 0))
        self.context.minpriority = int(self.form.get('minpriority', 0))
        if self.form.get('showclosed', None)=='yes':
            self.context.showclosed = True


    # TODO: replace this with a smart vocabulary and widget
    def userSelector(self):
        html = '<select name="name">\n'
        for person in self.allPeople():
            html = html + '<option value="'+person.name+'"'
            if person==self.context.user:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + person.browsername() + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def severitySelector(self):
        html = '<select name="minseverity">\n'
        for item in dbschema.BugSeverity.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.context.minseverity:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def prioritySelector(self):
        html = '<select name="minpriority">\n'
        for item in dbschema.BugPriority.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.context.minpriority:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    def showClosedSelector(self):
        html = '<input type="checkbox" id="showclosed" name="showclosed" value="yes"'
        if self.context.showclosed:
            html = html + ' checked="yes"'
        html = html + ' />'
        return html

    def allPeople(self):
        return Person.select('password IS NOT NULL')


