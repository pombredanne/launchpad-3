
from zope.interface import implements

from zope.schema.interfaces import IText
from zope.app.form.browser import TextAreaWidget, TextWidget

#
# WIDGETS
#

# TitleWidget
# A launchpad title widget... needs to be a little wider than a normal
# Textline
class TitleWidget(TextWidget):

    implements(IText)
    displayWidth = 60


# SummaryWidget
# A widget to capture a summary
class SummaryWidget(TextAreaWidget):

    implements(IText)
    width = 60
    height = 5


# DescriptionWidget
# A widget to capture a summary
class DescriptionWidget(TextAreaWidget):

    implements(IText)
    width = 60
    height = 10


