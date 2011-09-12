# Copyright 2011 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

#
# XXX: GavinPanella 2011-09-12 bug=846867: Temporary module until Storm is
# fixed to store JSON data in TEXT columns.
#

__metaclass__ = type
__all__ = [
    "JSON",
    ]


import json

import storm.properties
import storm.variables


class JSONVariable(storm.variables.EncodedValueVariable):

    __slots__ = ()

    def __init__(self, *args, **kwargs):
        assert json is not None, (
            "Neither the json nor the simplejson module was found.")
        super(JSONVariable, self).__init__(*args, **kwargs)

    def _loads(self, value):
        # simplejson.loads() does not always return unicode strings when the
        # input is not unicode. There are many simplejson bugs about this, see
        # http://code.google.com/p/simplejson/issues/detail?id=40 for one.
        if not isinstance(value, unicode):
            value = value.decode("utf-8")
        return json.loads(value)

    def _dumps(self, value):
        # http://www.ietf.org/rfc/rfc4627.txt states that JSON is text-based
        # and so we treat it as such here. In other words, this method returns
        # unicode and never str.
        dump = json.dumps(value, ensure_ascii=False)
        if not isinstance(dump, unicode):
            # json.dumps() does not always return unicode. See
            # http://code.google.com/p/simplejson/issues/detail?id=40 for one
            # of many discussions of str/unicode handling in simplejson.
            dump = dump.decode("utf-8")
        return dump


class JSON(storm.properties.SimpleProperty):
    variable_class = JSONVariable
