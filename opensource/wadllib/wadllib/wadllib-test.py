#!/usr/bin/python
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""
Doctest for the wadllib library.

We start by turning an XML WADL definition into a wadllib Application
object.

   >>> import os
   >>> import sys
   >>> testdata_path = os.path.join(os.path.split(sys.argv[0])[0],
   ...                              'testdata')
   >>> from wadllib import Application
   >>> wadl_path = os.path.join(testdata_path, "launchpad-wadl.xml")
   >>> wadl = Application("http://api.launchpad.dev/beta/", open(wadl_path))

   >>> print wadl.findResourceByPath('nosuchresource')
   None


== Link navigation ==

The preferred technique for finding a resource is to start at the root
resource and follow links.

   >>> service_root = wadl.findResourceByPath('')
   >>> service_root.url()
   'http://api.launchpad.dev/beta/'

The service root resource supports GET.

   >>> get_method = service_root.findMethod('get')
   >>> get_method.attrib['id']
   'service-root-get'

The service root resource also knows about representation parameters
like 'PersonSetCollectionAdapter_collection_link'. But until there's a
real JSON representation bound to the resource, there's no way of
knowing what value those parameters might have.

   >>> link_name = 'PersonSetCollectionAdapter_collection_link'
   >>> link_param = service_root.findParam(link_name)
   Traceback (most recent call last):
   ...
   ValueError: Resource is not bound to any representation.

The browser can use the description of the GET method to make an
actual GET request, and bind the resulting representation to the
WADL description of the resource:

   >>> def bind_to_testdata(resource, filename):
   ...     data = open(os.path.join(testdata_path,
   ...                 filename + '.json')).read()
   ...     return resource.bind(data, 'application/json')
   >>> bound_service_root = bind_to_testdata(service_root, 'root')

With the resource description and representation combined, we can find
real values for the parameters described in the WADL definition. We
can follow the 'PersonSetCollectionAdapter_collection_link' to a
resource of type 'XXX':

   >>> link_param = bound_service_root.findParam(link_name)
   >>> link_param.value()
   u'http://api.launchpad.dev/beta/people'
   >>> personset_resource = link_param.linked_resource()
   >>> personset_resource.url()
   u'http://api.launchpad.dev/beta/people'

The person set resource supports a standard GET as well as a named
GET and a named POST.

   >>> get_method = personset_resource.findMethod('get')

   >>> find_method = personset_resource.findMethod(
   ...     'get', fixed_params={'ws_op' : 'find'})
   >>> find_method.attrib['id']
   'PersonSetCollectionAdapter-get'

   >>> create_team_method = personset_resource.findMethod(
   ...     'post', fixed_params={'ws_op' : 'create_team'})
   >>> create_team_method.attrib['id']
   'PersonSetCollectionAdapter-create_team'

wadllib won't give you information about a nonexistent method.

   >>> no_such_method = personset_resource.findMethod(
   ...     'post', fixed_params={'ws_op' : 'nosuchmethod'})
   >>> print no_such_method
   None

Let's say the browser makes a GET request to the person set resource
and gets back a representation. We can bind that representation to our
description of the person set resource.

   >>> bound_personset = bind_to_testdata(personset_resource, 'personset')
   >>> bound_personset.findParam("start").value()
   0
   >>> bound_personset.findParam("total_size").value()
   63

We can keep following links indefinitely so long as we bind to a
representation each time to find the next link.

   >>> next_page_link = bound_personset.findParam("next_collection_link")
   >>> next_page_link.value()
   u'http://api.launchpad.dev/beta/people?ws.start=5&ws.size=5'
   >>> page_two = next_page_link.linked_resource()
   >>> bound_page_two = bind_to_testdata(page_two, 'personset-page2')
   >>> bound_page_two.url()
   u'http://api.launchpad.dev/beta/people?ws.start=5&ws.size=5'
   >>> bound_page_two.findParam("start").value()
   5
   >>> bound_page_two.findParam("next_collection_link").value()
   u'http://api.launchpad.dev/beta/people?ws.start=10&ws.size=5'


== Resource instantiation ==

If you happen to have the URL to an object lying around, and you know
its type, you can construct a Resource object directly instead of
by following links.

   >>> from wadllib import Resource
   >>> limi_person = Resource(wadl, "http://api.launchpad.dev/beta/~limi",
   ...     "http://api.launchpad.dev/beta/#PersonEntryAdapter")

   >>> bound_limi = bind_to_testdata(limi_person, 'person-limi')
   >>> languages_link = bound_limi.findParam("languages_collection_link")
   >>> languages_link.value()
   u'http://api.launchpad.dev/beta/~limi/languages'

"""

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
