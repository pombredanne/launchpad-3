// Unit testing framework for the Launchpad AJAX test suite.
var client = new LP.client.Launchpad();

windmill.jsTest.require('login.js');

// Test that retrieving a non-existent resource uses the failure handler.
var test_no_such_url = new SynchronizedTest('test_no_such_url', [
    function (test) {
        client.get("no-such-url", {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('failure', test.result.callback);
    }
                                                                 ], true);


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


// Check the invocation of a named POST operation.
test_logged_in_as_foo_bar.test_named_post = new SynchronizedTest(
    'test_named_post', [
    function (test) {
        test.bugtask_uri = '/redfish/+bug/15';
        var on = test.create_yui_sync_on();
        client.named_post(
                          test.bugtask_uri, 'transitionToStatus',
                          {on: on,
                           parameters: {status: 'Confirmed'}});
    },
    'wait_action',
    function (test) {
        test.add_cleanups([
            function (test) {
                client.named_post(
                    test.bugtask_uri, 'transitionToStatus',
                    {on: test.create_yui_sync_on(),
                     parameters: {'status': 'New'}});
            },
            'wait_action']);
        jum.assertEquals('success', test.result.callback);
        test.clear();
        // Get the bugtask and make sure its status has changed.
        client.get(test.bugtask_uri, {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function(test) {
        jum.assertEquals('success', test.result.callback);
        var bugtask = test.result.args[0];
        jum.assertEquals(bugtask.status, 'Confirmed');
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
        test.clear();
        var root_object = test.result.args[0];
        root_object.follow_link('people', {on: test.create_yui_sync_on()});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        test.clear();
        var people = test.result.args[0];
        jum.assertTrue(people instanceof LP.client.Collection);
        jum.assertEquals(4, people.total_size);
    }
    ]);
test_follow_link.debug = true;

//Test that follow_link follows through redirect.
// Retrieve the launchpad root and check the people
test_logged_in_as_foo_bar.test_follow_link_through_redirect = 
    new SynchronizedTest(
        'test_follow_link_through_redirect', [
        function (test) {
            client.get("", test.create_yui_sync_on());
        },
        'wait_action',
        function (test) {
            jum.assertEquals('success', test.result.callback);
            test.clear();
            var root_object = test.result.args[0];
            root_object.follow_link('me', {on: test.create_yui_sync_on()});
        },
        'wait_action',
        function (test) {
            jum.assertEquals('success', test.result.callback);
            test.clear();
            var me = test.result.args[0];
            jum.assertTrue(me instanceof LP.client.Entry);
            jum.assertEquals('name16', me.name);
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
        jum.assertEquals(salgado.name, "salgado");
    }
    ]);


//Test that modifying an entry and then calling lp_save() saves the
//entry on the server.
test_logged_in_as_foo_bar.test_entry_lp_save = new SynchronizedTest(
    'test_entry_lp_save', [
    function (test) {
        client.get('~salgado', test.create_yui_sync_on());
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        test.clear();
        var salgado = test.result.args[0];
        test.original_display_name = salgado.display_name;
        salgado.display_name = 'A new display name';
        salgado.lp_save(test.create_yui_sync_on());
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        test.clear();
        test.add_cleanups([
            function (test) {
                test.clear();
                client.get('~salgado', test.create_yui_sync_on());
            },
            'wait_action',
            function (test) {
                jum.assertEquals('success', test.result.callback);
                test.clear();
                var salgado = test.result.args[0];
                salgado.display_name = test.original_display_name;
                salgado.lp_save(test.create_yui_sync_on());
            },
            'wait_action']);
        client.get('~salgado', test.create_yui_sync_on());
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var salgado = test.result.args[0];
        jum.assertEquals('A new display name', salgado.display_name);
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
        test.clear();
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
        test.clear();
        var collection = test.result.args[0];
        collection.named_get(
            'find', test.create_yui_sync_on(), {text: 'salgado'});
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(1, collection.total_size);
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
        test.clear();
        var collection = test.result.args[0];
        collection.named_get(
            'find', test.create_yui_sync_on(), {text: 'salgado'}, 10);
    },
    'wait_action',
    function (test) {
        jum.assertEquals('success', test.result.callback);
        test.clear();
        var collection = test.result.args[0];
        jum.assertTrue(collection instanceof LP.client.Collection);
        jum.assertEquals(1, collection.total_size);
        jum.assertEquals(0, collection.entries.length);
    }
    ]);
