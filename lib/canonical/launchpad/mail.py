"""mail.py -- The One True Way to send mail from the Launchpad
application."""

import smtplib

def sendmail(from_addr, to_addrs, subject, body):
    """Send a mail from from_addr to to_addrs with the subject and
    body specified."""
    server = smtplib.SMTP('localhost')
    msg = """\
From: %s
To: %s
Subject: %s

%s""" % (from_addr, ", ".join(to_addrs), subject, body)
    server.sendmail(from_addr, to_addrs, msg)
    server.quit()
