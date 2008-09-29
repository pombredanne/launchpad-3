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

    client = new LaunchpadClient();
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

    function expect_404_callback(response) {
        report_test("Error callback called on 404", false);
    }

    function expect_404_errback(error) {
        report_test("Error callback called on 404", true);
    }

    client.get("no-such-url", expect_404_callback, expect_404_errback);

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
                   && collection.total_size == 22);
        report_test("Fetching collection yields Collection object", success);
    }
    client.get('projects/', collection_callback, default_errback);
}