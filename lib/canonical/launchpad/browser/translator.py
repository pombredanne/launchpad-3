# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.form.browser.editview import EditView

__all__ = ['TranslatorEditView']

class TranslatorEditView(EditView):

    def changed(self):
         self.request.response.redirect('../')

