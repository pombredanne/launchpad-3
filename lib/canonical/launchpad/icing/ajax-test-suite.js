// Unit testing framework for the Launchpad AJAX test suite.

function report_test(name, conditional) {
    list = document.getElementById("test-results");
    element = document.createElement("li");
    textNode = document.createTextNode(
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
    client = new LaunchpadClient();

    // Make sure the error callback is called when there's an error.
    function expect_404_callback(response) {
        report_test("Error callback called on 404", false);
    }
    function expect_404_errback(error) {
        report_test("Error callback called on 404", true);
    }
    client.get("no-such-url", expect_404_callback, expect_404_errback);

    // Make sure it's possible to load objects by URI.
    function relative_callback(launchpad) {
        success = (launchpad.people_collection_link
                   == "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from relative URL", success);
    }
    client.get("", relative_callback, default_errback);

    function absolute_callback(launchpad) {
        success = (launchpad.people_collection_link ==
                   "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from absolute URL", success);
    }
    client.get("https://launchpad.dev/api/beta/", absolute_callback,
               default_errback);

    // Make sure it's possible to invoke named operations on URIs.
    function uri_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 1);
        report_test("Invoking a named operation via URI", success);
    }
    client.named_get('people/', 'find', {text:'salgado'},
                     uri_named_get_callback, default_errback);


    // Test the Launchpad object.
    function service_root_callback(root_object) {
        success = (root_object instanceof Launchpad &&
                   root_object.people_collection_link ==
                   "https://launchpad.dev/api/beta/people");
        report_test("Fetching root yields Launchpad object", success);
    }
    client.get('', service_root_callback, default_errback);


    // Test an Entry object.
    function entry_callback(entry) {
        success = (entry instanceof Entry
                   && entry.name == "bzr");
        report_test("Fetching entry yields Entry object", success);

        //Modify the entry.
        entry.description = "A new description.";
        entry.lp_save(entry_save_callback, default_errback);
    }

    function entry_save_callback(entry) {
        report_test("Entry object can be saved", true);
        client.get('bzr', modified_entry_callback, default_errback);
    }

    function modified_entry_callback(entry) {
        success = (entry.description == "A new description.");
        report_test("Modifications are stored persistently", success);
    }

    client.get('bzr', entry_callback, default_errback);


    // Test a Collection object.
    function collection_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 4);
        report_test("Fetching collection yields Collection object", success);
        collection.named_get('find', {text:'salgado'},
                             collection_named_get_callback, default_errback);
        collection.named_get('find', {text:'salgado'},
                             paged_collection_named_get_callback,
                             default_errback, 10);
        name = "newteam" + (new Date()).getTime();
        collection.named_post('newTeam',
                              {display_name: 'My new team', name: name},
                              collection_named_post_callback, default_errback);
    }
    client.get('people/', collection_callback, default_errback);

    function collection_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.total_size == 1);
        report_test("Invoking a named GET operation on a collection", success);
    }

    function paged_collection_named_get_callback(collection) {
        success = (collection instanceof Collection
                   && collection.entries.length == 0);
        report_test("Paging works with named GET on a collection", success);
    }

    function collection_named_post_callback(new_entry) {
        success = (new_entry instanceof Entry
                   && entry.display_name == "My new team");
        report_test("Named POST works and newborn entry is retrieved",
                    success);
    }
}
