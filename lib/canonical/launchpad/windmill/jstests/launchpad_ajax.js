// Unit testing framework for the Launchpad AJAX test suite.
var client = new LP.client.Launchpad();

windmill.jsTest.require('login.js');


// Test access to prepopulated data.
test_prepopulated_data_anonymous = new SynchronizedTest(
    'test_prepopulated_data_anonymous', [
    {"params": {"url": "/firefox/+bug/1"}, "method": "open"},
    {"params": {}, "method": "waits.forPageLoad"},
    // Wait until one of the last element on the page is available.
    {"params": {"xpath": "//div[@id='globalfooter']"},
     "method": "waits.forElement"},
    function (test) {
        jum.assertUndefined(LP.client.links.me);
        jum.assertUndefined(LP.client.cache.context);
    }
    ]);

test_logged_in_as_foo_bar.test_prepopulated_data = new SynchronizedTest(
    'test_prepopulated_data', [
    {"params": {"url": "/firefox/+bug/1"}, "method": "open"},
    {"params": {}, "method": "waits.forPageLoad"},
    // Wait until one of the last element on the page is available.
    {"params": {"xpath": "//div[@id='globalfooter']"},
     "method": "waits.forElement"},
    function (test) {
        // If the user is logged in, the link to their user account
        // will be in the link cache.
        jum.assertEquals(LP.client.links.me, '/~name16');

        // If the view has a context, the context will be in the object
        // cache.
        jum.assertNotUndefined(LP.client.cache.context);
        var context = LP.client.cache.context;
        jum.assertNotEquals(context.self_link.indexOf(
                            "/api/devel/firefox/+bug/1"), -1);
        jum.assertNotEquals(context.resource_type_link.indexOf(
                            "/api/devel/#bug_task"), -1);
        jum.assertNotEquals(context.owner_link.indexOf(
                            "/api/devel/~name12"), -1);
        jum.assertNotEquals(context.related_tasks_collection_link.indexOf(
                            "/api/devel/firefox/+bug/1/related_tasks"), -1);

        // Specific views may add additional objects to the object cache
        // or links to the link cache.
        var bug = LP.client.cache.bug;
        jum.assertNotUndefined(LP.client.cache.bug);
        jum.assertNotEquals(bug.self_link.indexOf("/api/devel/bugs/1"), -1);
    }
    ]);

// Test that making a web service call doesn't modify the callback
// methods you pass in.
var test_callback_safety = function() {
    var success_callback = function() {};
    var config = {on: {success: success_callback}};

    // Test a GET.
    client.get("/people", config);
    jum.assertTrue(success_callback === config.on.success);

    // Test a named POST.
    name = "callback-safety-test" + new Date().getTime();
    config.parameters = {display_name: 'My new team', name: name};
    client.named_post("/people", "newTeam", config);
    jum.assertTrue(success_callback === config.on.success);
};


var test_normalize_uri = function() {
    var normalize = LP.client.normalize_uri;
    jum.assertEquals(normalize("http://www.example.com/api/devel/foo"),
                     "/api/devel/foo");
    jum.assertEquals(normalize("http://www.example.com/foo/bar"), "/foo/bar");
    jum.assertEquals(normalize("/foo/bar"), "/api/devel/foo/bar");
    jum.assertEquals(normalize("/api/devel/foo/bar"), "/api/devel/foo/bar");
    jum.assertEquals(normalize("foo/bar"), "/api/devel/foo/bar");
    jum.assertEquals(normalize("api/devel/foo/bar"), "/api/devel/foo/bar");
};

var test_append_qs = function() {
    var qs = "";
    qs = LP.client.append_qs(qs, "Pöllä", "Perelló");
    jum.assertEquals("P%C3%B6ll%C3%A4=Perell%C3%B3", qs);
};

var test_field_uri = function() {
    jum.assertEquals(LP.client.get_field_uri("http://www.example.com/api/devel/foo", "field"),
                     "/api/devel/foo/field");
    jum.assertEquals(LP.client.get_field_uri("/no/slash", "field"),
                     "/api/devel/no/slash/field");
    jum.assertEquals(LP.client.get_field_uri("/has/slash/", "field"),
                     "/api/devel/has/slash/field");
};

// Test that retrieving a non-existent resource uses the failure handler.
var test_no_such_url = new SynchronizedTest('test_no_such_url', [
    function (test) {
        client.get("no-such-url", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('failure', test.result.callback);
    }
    ]);


//Check that retrieving the root by relative URL returns the root entry.
var test_relative_url = new SynchronizedTest('test_relative_url', [
    function (test) {
        client.get("", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var launchpad = test.result.args[0];
        jum.assertTrue(launchpad instanceof LP.client.Root);
        jum.assertNotNull(
            launchpad.people_collection_link.match(/people$/));
    }
    ]);


//Check that retrieving the root by absolute URL returns the root entry.
var test_absolute_url = new SynchronizedTest('test_absolute_url', [
    function (test) {
        client.get("", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var launchpad = test.result.args[0];
        jum.assertTrue(launchpad instanceof LP.client.Root);
        jum.assertNotNull(
            launchpad.people_collection_link.match(/people$/));
    }
    ]);


// Check that collection resources are paginated.
var test_pagination_collection = new SynchronizedTest(
    'test_pagination_collection', [
    function (test) {
        client.get("/people", {on: test.create_yui_sync_on(),
                               start: 2, size: 1});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var people = test.result.args[0];
        jum.assertEquals(2, people.start);
        jum.assertEquals(1, people.entries.length);
    }
    ]);


// Check invoking a read-only name operation on a resource URI.
// Make sure it's possible to invoke named operations on URIs.
var test_named_get = new SynchronizedTest('test_named_get', [
    function (test) {
        client.named_get(
            "people/", "find", {on: test.create_yui_sync_on(),
                                parameters: {text:"salgado"}});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(1, collection.total_size);
    }
    ]);



var test_named_get_returning_json = new SynchronizedTest(
    'test_named_get_returning_json', [
    // Make sure a named GET that returns a JSON data structure works.
    function (test) {
        client.named_get("ubuntu/+archive/primary", "getBuildCounters",
                         {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var structure = test.result.args[0];
        jum.assertEquals(structure.failed, 5);
    }
    ]);


// Check the invocation of a named POST operation.
test_logged_in_as_foo_bar.test_named_post = new SynchronizedTest(
    'test_named_post', [
    function (test) {
        test.bugtask_uri = '/redfish/+bug/15';
        client.named_post(
                          test.bugtask_uri, 'transitionToStatus',
                          {on: test.create_yui_sync_on(),
                           parameters: {status: 'Confirmed'}});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        test.add_cleanups([
            function (test) {
                client.named_post(
                    test.bugtask_uri, 'transitionToStatus',
                    {on: test.create_yui_sync_on(),
                     parameters: {'status': 'New'}});
            },
            'wait_action']);
        // Get the bugtask and make sure its status has changed.
        client.get(test.bugtask_uri, {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function(test) {
        jum.assertEquals('success', test.result.callback);
        var bugtask = test.result.args[0];
        jum.assertEquals(bugtask.get('status'), 'Confirmed');
    }
    ]);

//Test that follow_link return the resource at the end of the link.
// Retrieve the launchpad root and check the people link is a collection.
var test_follow_link = new SynchronizedTest('test_follow_link', [
    function (test) {
        client.get("", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var root_object = test.result.args[0];
        root_object.follow_link('people', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var people = test.result.args[0];
        jum.assertTrue(people instanceof LP.client.Collection);
        jum.assertEquals(4, people.total_size);
    }
    ]);

//Test that follow_link follows through redirect.
// Retrieve the launchpad root and check the people
test_logged_in_as_foo_bar.test_follow_link_through_redirect =
    new SynchronizedTest(
        'test_follow_link_through_redirect', [
        function (test) {
            client.get("", {on: test.create_yui_sync_on()});
        },
        'wait_action',
        function (test) {
            jum.assertEquals('success', test.result.callback);
            var root_object = test.result.args[0];
            root_object.follow_link('me', {on: test.create_yui_sync_on()});
        },
        'wait_action',
        function (test) {
            jum.assertEquals('success', test.result.callback);
            var me = test.result.args[0];
            jum.assertTrue(me instanceof LP.client.Entry);
            jum.assertEquals('name16', me.get('name'));
        }
        ]);


//Test that retrieving an entry resource yield an Entry object.
var test_entry_get = new SynchronizedTest('test_entry_get', [
    function (test) {
        client.get('~salgado', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        jum.assertTrue(salgado instanceof LP.client.Entry);
        jum.assertEquals("salgado", salgado.get('name'));
    }
    ]);

// Test that retrieving an HTML representation of an entry yields an
// HTML snippet.
var test_entry_html_get = new SynchronizedTest('test_entry_html_get', [
    function (test) {
        client.get('~salgado', {on: test.create_yui_sync_on(),
                                accept: LP.client.XHTML});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado_html = test.result.args[0];
        jum.assertNotEquals(salgado_html.indexOf("<dl"), -1);
     }
     ]);


// Test that it's possible to request an HTML representation of
// an object when updating it.
test_logged_in_as_foo_bar.test_html_entry_lp_save = new SynchronizedTest(
    'test_entry_lp_save', [
    function (test) {
        client.get('~salgado', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        salgado.lp_save({on: test.create_yui_sync_on(),
                         accept: LP.client.XHTML});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado_html = test.result.args[0];
        jum.assertNotEquals(salgado_html.indexOf("<dl"), -1);

        // Now test the patch() method directly.
        client.patch('~salgado', {},
                     {on: test.create_yui_sync_on(),
                      accept: LP.client.XHTML});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado_html = test.result.args[0];
        jum.assertNotEquals(salgado_html.indexOf("<dl"), -1);

         // Now test the patch() method on a field resource.
         var field_uri = LP.client.get_field_uri('~salgado', 'display_name');
         client.patch(field_uri, 'Guilherme Salgado 2',
                      {on: test.create_yui_sync_on(),
                       accept: LP.client.XHTML});
     },
     'wait_action',
     function (test) {
         var field_uri = LP.client.get_field_uri('~salgado', 'display_name');
         jum.assertEquals('success', test.result.callback);
         var salgado_name_html = test.result.args[0];
         jum.assertEquals(salgado_name_html, "Guilherme Salgado 2");

         // Now make sure patch() on a field resource works when we
         // request a JSON representation in return.
         field_uri = LP.client.get_field_uri('~salgado', 'display_name');
         client.patch(field_uri, 'Guilherme Salgado',
                      {on: test.create_yui_sync_on()});
     },
     'wait_action',
     function (test) {
         var field_uri = LP.client.get_field_uri('~salgado', 'display_name');
         jum.assertEquals('success', test.result.callback);
         var salgado_name_html = test.result.args[0];
         jum.assertEquals(salgado_name_html, "Guilherme Salgado");
     }
]);

//Test that modifying an entry and then calling lp_save() saves the
//entry on the server.
test_logged_in_as_foo_bar.test_entry_lp_save = new SynchronizedTest(
    'test_entry_lp_save', [
    function (test) {
        client.get('~salgado', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        test.original_display_name = salgado.get('display_name');
        salgado.set('display_name', '<b>A new display name</b>');
        salgado.lp_save({on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        // Make sure that the save operation returned a new version of
        // the object.
        var new_salgado = test.result.args[0];
        jum.assertEquals(new_salgado.get('display_name'),
                         '<b>A new display name</b>');

        test.add_cleanups([
            function (test) {
                client.get('~salgado', {on: test.create_yui_sync_on()});
            },
            'wait_action',
            function (test) {
                jum.assertEquals('success', test.result.callback);
                var salgado = test.result.args[0];
                salgado.set('display_name', test.original_display_name);
                salgado.lp_save({on: test.create_yui_sync_on()});
                jum.assertEquals(salgado.dirty_attributes.length, 0);
            },
            'wait_action']);
        client.get('~salgado', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        jum.assertEquals('<b>A new display name</b>',
                         salgado.get('display_name'));

        // As long as we've got bad HTML in the display name, let's
        // get an HTML representation and see whether the bad HTML was
        // escaped.
        client.get('~salgado', {on: test.create_yui_sync_on(),
                                accept: LP.client.XHTML});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);

        var salgado_html = test.result.args[0];
        jum.assertNotEquals(salgado_html.indexOf("<dl"), -1);
        jum.assertNotEquals(salgado_html.indexOf("&lt;b&gt;A new"), -1);

        // Now test the patch() method directly.
        client.patch('~salgado', {'display_name': 'A patched display name'},
                     {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        client.get('~salgado', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        jum.assertEquals('A patched display name', salgado.get('display_name'));

        // Test that a mismatched ETag results in a failed save.
        salgado.set('http_etag', "Non-matching ETag.");
        salgado.set('display_name', "This display name will not be set.");
        salgado.lp_save({on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('failure', test.result.callback);
        var xhr = test.result.args[1];
        jum.assertEquals(xhr.status, 412);
    }
    ]);


//Test retrieving a collection object.
var test_collection = new SynchronizedTest('test_collection', [
    function (test) {
        client.get("people", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(4, collection.total_size);
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
	var entries = test.result.args[0].entries,
	    length = test.result.args[0].total_size,
	    index;
	for (index = 0 ; index < length ; index++) {
            jum.assertTrue(entries[index] instanceof LP.client.Entry);
	}
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
	var entry = test.result.args[0].entries[0];
	jum.assertEquals('test', entry.display_name);
	entry.set('display_name', "Set Display Name");
	entry.lp_save({on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
	client.get('people', { on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
	var entry = test.result.args[0].entries[0];
	jum.assertEquals('Set Display Name', entry.display_name);
    }
    ]);


//Test the lp_slice() method on a collection.
var test_collection_lp_slice = new SynchronizedTest(
    'test_collection_lp_slice', [
    function (test) {
        client.get("people", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        collection.lp_slice(test.create_yui_sync_on(), 2, 1);
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var slice = test.result.args[0];
        jum.assertEquals(2, slice.start);
        jum.assertEquals(1, slice.entries.length);
    }
    ]);


//Test invoking a named GET on a collection.
var test_collection_named_get = new SynchronizedTest(
    'test_collection_named_get', [
    function (test) {
        client.get("people", {on: test.create_yui_sync_on() });
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        collection.named_get(
          'find', {on: test.create_yui_sync_on(),
                  parameters: {text: 'salgado'}});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(1, collection.total_size);
    }
    ]);


//Test named POST on a collection, and object creation.
test_logged_in_as_foo_bar.test_collection_named_post = new SynchronizedTest(
    'test_collection_named_post', [
    function(test) {
        client.get("/people/", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function(test) {
        // Generate a unique team name so that the team-creation test
        // can be run multiple times without resetting the dataset.
        name = "newteam" + new Date().getTime();
        var collection = test.result.args[0];
        collection.named_post('newTeam',
                              {on: test.create_yui_sync_on(),
                               parameters: {display_name: 'My new team',
                                            name: name}});
    },
    'wait_action',
    function(test) {
        var new_entry = test.result.args[0];
        jum.assertEquals("success", test.result.callback);
        jum.assertTrue(new_entry instanceof LP.client.Entry);
        jum.assertEquals(new_entry.get("display_name"), "My new team");
        jum.assertNotEquals(new_entry.lp_original_uri.indexOf("/~newteam"),
                            -1);
    }
    ]);

//Test paging on a named collection.
var test_collection_paged_named_get = new SynchronizedTest(
    'test_collection_paged_named_get', [
    function (test) {
        client.get("people", {on: test.create_yui_sync_on() });
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        collection.named_get(
                             'find', {on: test.create_yui_sync_on(),
                                      parameters: {text: 'salgado'},
                                      start: 10});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(1, collection.total_size);
    }
    ]);

// Test hosted file objects.

// To test PUT to a hosted file we need to create a brand new
// file. Several problems combine to make this necessary. The
// first is that you can't send a binary file through XHR: it gets
// truncated at the first null character. So we can't just PUT to
// a mugshot or icon. There are some product release files in the
// preexisting dataset, but they don't have anything backing them
// in the librarian, so we can't get a proper handle on them. So
// we need to create a brand new file and then test PUT on it.

// Unfortunately, currently there are no files you can create with
// PUT, so we can't test this.

test_logged_in_as_foo_bar.test_hosted_files = new SynchronizedTest(

    'test_hosted_files', [
    function(test) {
        var bug_uri = '/bugs/15';
        client.named_post(bug_uri, 'addAttachment',
            {on: test.create_yui_sync_on(),
             parameters: {comment: 'A new attachment',
                          content_type: 'text/plain',
                          data: 'Some data.',
                          filename: 'foo.txt'}});
    },
    'wait_action',
    function(test) {
        jum.assertEquals('success', test.result.callback);
        var attachment = test.result.args[0];
        attachment.follow_link('data',
                               {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function(test) {
        jum.assertEquals('success', test.result.callback);
        var hosted_file = test.result.args[0];

// Unfortunately, there's no hosted file that can be edited through
// the web service, so we can't test PUT.
//         hosted_file.contents = "['Unit tester was here.']";
//         hosted_file.filename = "unittest.json";
//         hosted_file.content_type = "application/json";
//         hosted_file.lp_save({on: test.create_yui_sync_on()});
//     },
//     'wait_action',
//     function(test) {
//         jum.assertEquals('success', test.result.callback);
//         var hosted_file = test.result.args[2];
         hosted_file.lp_delete({on: test.create_yui_sync_on()});
     },
     'wait_action',
     function(test) {
         jum.assertEquals('failure', test.result.callback);
         // XXX flacoste 2008/12/12 bug=307539
         // This code works right now, but when testing a hosted file
         // that can be edited through the web service, it will fail.
         var request = test.result.args[1];
         jum.assertEquals(405, request.status);
     }
     ]
 );
