# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = [
    'LinkCheckerAPI',
    ]

import simplejson

class LinkCheckerAPI:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):

        result = {}
        links_to_check_data = self.request.get('link_hrefs')
        links_to_check = simplejson.loads(links_to_check_data)
        invalid_links = []
        for link in links_to_check:
            if "foo" in link:
                invalid_links.append(link)
        result['invalid_links']=invalid_links
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(result)

