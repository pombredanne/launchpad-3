# Copyright 2004 Canonical Ltd

# lp imports
from canonical.lp.dbschema import SSHKeyType

# interface import
from canonical.launchpad.interfaces import ISSHKeySet
from canonical.launchpad.interfaces import ILaunchBag

# zope imports
from zope.component import getUtility


class SSHKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "\n".join([key.keytext for key in self.context.sshkeys])


class SSHKeyEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def form_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return ''

        action = self.request.form.get('action')
        if action == 'add':
            return self.add_action()
        elif action == 'remove':
            return self.remove_action()

    def add_action(self):
        sshkey = self.request.form.get('sshkey')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            return 'Invalid public key'
        
        if kind == 'ssh-rsa':
            keytype = int(SSHKeyType.RSA)
        elif kind == 'ssh-dss':
            keytype = int(SSHKeyType.DSA)
        else:
            return 'Invalid public key'
        
        getUtility(ISSHKeySet).new(self.user.id, keytype, keytext, comment)
        return 'SSH public key added.'

    def remove_action(self):
        try:
            id = self.request.form.get('key')
        except ValueError:
            return "Can't remove key that doesn't exist"

        sshkey = getUtility(ISSHKeySet).get(id)
        if sshkey is None:
            return "Can't remove key that doesn't exist"

        if sshkey.person != self.user:
            return "Cannot remove someone else's key"

        comment = sshkey.comment
        sshkey.destroySelf()
        return 'Key "%s" removed' % comment

