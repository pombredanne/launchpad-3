# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""This module contains the Password Reset Application"""
__metaclass__ = type

from datetime import datetime

from canonical.zodb import zodbconnection

from smtplib import SMTP

class PasswordChangeApp(object):
    """ Change Password Application"""
    def __init__(self, name):
        ## Store the url password change code
        ## to be passed to the view class in
        ## a form input type hidden

        self.code = name


class SendPasswordChangeEmail(object):
    """ Send an Password change special link for a user """
    def __init__(self, code, toaddress):

        template = open('lib/canonical/auth/mailTemplate').read()
        fromaddress = "Ubuntu Webmaster <webmaster@ubuntulinux.org>"

        data = {'longstring': code,
                'toaddress': toaddress,
                'fromaddress': fromaddress,
                'date': datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
                }
        
        msg = template % data

        sender = SMTP("localhost")
        sender.sendmail(fromaddress,
                        toaddress,
                        msg)

class UbuntuLinuxSite(object):
    pass
    
