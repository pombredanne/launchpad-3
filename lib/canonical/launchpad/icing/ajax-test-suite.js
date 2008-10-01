// Unit testing framework for the Launchpad AJAX test suite.

function report_test(name, conditional) {
    var list = document.getElementById("test-results");
    var element = document.createElement("li");
    var textNode = document.createTextNode(
        name + ": " + (conditional ? "Success" : "Failure"));
    element.appendChild(textNode);
    list.appendChild(element);
}

function default_errback(error) {
    report_test("Failure: " + error);
}

// Test the basic functionality of LaunchpadClient.
function ajax_test_suite() {
    // Test methods that operate on URIs.
    var client = new LaunchpadClient();

    // Make sure the error callback is called when there's an error.
    client.get("no-such-url", expect_404_callback, expect_404_errback);

    function expect_404_callback(response) {
        report_test("Error callback called on 404", false);
    }

    function expect_404_errback(error) {
        report_test("Error callback called on 404", true);
    }

    // Make sure it's possible to load objects by URI.
    client.get("", relative_callback, default_errback);

    function relative_callback(launchpad) {
        success = (launchpad.people_collection_link
                   == "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from relative URL", success);
    }

    client.get("https://launchpad.dev/api/beta/", absolute_callback,
               default_errback);

    function absolute_callback(launchpad) {
        success = (launchpad.people_collection_link ==
                   "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from absolute URL", success);
    }

    client.get("/people", uri_pagination_callback, default_errback,
               2, 1);

    function uri_pagination_callback(people) {
        success = (people.start == 2 && people.entries.length == 1);
        report_test("Paginate when loading from URL", success);
    }

    // Make sure it's possible to invoke named operations on URIs.
    client.named_get('people/', 'find', {text:'salgado'},
                     uri_named_get_callback, default_errback);
    function uri_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 1);
        report_test("Invoking a named GET via URI", success);
    }

    var bugtask_uri = 'redfish/+bug/15';
    var deferred = client.named_post(bugtask_uri, 'transitionToStatus',
                                     {status: 'Confirmed'});
    deferred.addCallback(uri_named_post_callback);
    deferred.addErrback(default_errback);

    function uri_named_post_callback(nothing) {
        // Get the bug and make sure its status has changed.
        client.get(bugtask_uri, uri_named_post_callback_check_bugtask,
                   default_errback);
    }

    function uri_named_post_callback_check_bugtask(bugtask) {
        success = (bugtask.status == 'Confirmed');
        report_test("Invoking a named POST via URI", success);

        /// Set the bug status back for the next time the test is run.
        var deferred = client.named_post(bugtask_uri, 'transitionToStatus',
                                         {status: 'New'});
        deferred.addCallback(noop);
        deferred.addErrback(default_errback);
    }

    // Test the Launchpad object.
    client.get('', service_root_callback, default_errback);
    function service_root_callback(root_object) {
        success = (root_object instanceof Launchpad &&
                   root_object.people_collection_link ==
                   "https://launchpad.dev/api/beta/people");
        report_test("Fetching root yields Launchpad object", success);
    }


    // Test an Entry object.
    client.get('bzr', entry_callback, default_errback);

    function entry_callback(entry) {
        success = (entry instanceof Entry
                   && entry.name == "bzr");
        report_test("Fetching entry yields Entry object", success);

        // Now that we have the object, run some more tests.
        entry.description = "A new description.";
        var deferred = entry.lp_save();
        deferred.addCallback(entry_save_callback);
        deferred.addErrback(default_errback);
    }

    function entry_save_callback(entry) {
        report_test("Entry object can be saved", true);
        client.get('bzr', modified_entry_callback, default_errback);
    }

    function modified_entry_callback(entry) {
        success = (entry.description == "A new description.");
        report_test("Modifications are stored persistently", success);
    }


    // Test a Collection object.
    client.get('people/', collection_callback, default_errback);

    function collection_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 4);
        report_test("Fetching collection yields Collection object", success);

        // Now that we have the object, run some more tests.
        collection.lp_slice(collection_slice_callback, default_errback,
                            2, 1);
        collection.named_get('find', {text:'salgado'},
                             collection_named_get_callback, default_errback);
        collection.named_get('find', {text:'salgado'},
                             paged_collection_named_get_callback,
                             default_errback, 10);

        // These aren't real unit tests, and the dataset isn't reset
        // after they run. Generate a unique team name so that the
        // team-creation test can be run multiple times.
        name = "newteam" + (new Date()).getTime();
        var deferred = collection.named_post('newTeam',
                                             {display_name:
                                              'My new team', name: name});
        deferred.addCallback(collection_named_post_callback);
        deferred.addErrback(default_errback);
    }

    function collection_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 1);
        report_test("Invoking a named GET operation on a collection", success);
    }

    function collection_slice_callback(collection) {
        success = (collection.start == 2 && collection.entries.length == 1);
        report_test("Slicing a collection", success);
    }

    function paged_collection_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.entries.length == 0);
        report_test("Paging works with named GET on a collection", success);
    }

    function collection_named_post_callback(new_entry) {
        success = (new_entry instanceof Entry
                   && new_entry.display_name == "My new team"
                   && new_entry.lp_original_uri.indexOf("/~newteam") != -1);
        report_test("Named POST works and newborn entry is retrieved",
                    success);
    }
}
