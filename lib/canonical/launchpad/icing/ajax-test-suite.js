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
    report_test("Failure : " + error);
}

// Test the basic functionality of LaunchpadClient.
function ajax_test_suite() {
    // Test methods that operate on URIs.
    var client = new LaunchpadClient();

    function on_success(callback) {
        /* Generate a default set of callbacks. */
        return { success: callback, failure: default_errback };
    }

    // Make sure the error callback is called when there's an error.
    var on = { success: expect_404_callback,
               failure: expect_404_errback};
    client.get("no-such-url", on);

    function expect_404_callback(response) {
        report_test("Error callback called on 404", false);
    }

    function expect_404_errback(error) {
        report_test("Error callback called on 404", true);
    }

    // Make sure it's possible to load objects by URI.
    client.get("", on_success(relative_callback));

    function relative_callback(launchpad) {
        var success = (launchpad instanceof Launchpad
                       && launchpad.people_collection_link
                       == "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from relative URL", success);
    }

    client.get("", on_success(absolute_callback));

    function absolute_callback(launchpad) {
        var success = (launchpad instanceof Launchpad
                       && launchpad.people_collection_link
                       == "https://launchpad.dev/api/beta/people");
        report_test("Load a resource from absolute URL", success);
    }

    client.get("/people", on_success(uri_pagination_callback), 2, 1);

    function uri_pagination_callback(people) {
        var success = (people.start == 2 && people.entries.length == 1);
        report_test("Paginate when loading from URL", success);
    }

    // Make sure it's possible to invoke named operations on URIs.
    client.named_get("people/", "find", on_success(uri_named_get_callback),
                     {text:"salgado"});
    function uri_named_get_callback(collection) {
        var success = (collection instanceof Collection
                       && collection.total_size == 1);
        report_test("Invoking a named GET via URI", success);
    }

    // Invoke a named POT operation on a bugtask.
    var bugtask_uri = 'redfish/+bug/15';
    client.named_post(bugtask_uri, 'transitionToStatus',
                      on_success(uri_named_post_callback),
                      {status: 'Confirmed'});

    function uri_named_post_callback(nothing) {
        // Get the bugtask and make sure its status has changed.
        client.get(bugtask_uri,
                   on_success(uri_named_post_callback_check_bugtask));
    }

    function uri_named_post_callback_check_bugtask(bugtask) {
        var success = (bugtask.status == 'Confirmed');
        report_test("Invoking a named POST via URI", success);

        /// Set the bug status back for the next time the test is run.
        client.named_post(bugtask_uri, 'transitionToStatus',
                          on_success(function () {}), {status: 'New'});
    }

    // Test the Launchpad object.
    client.get("", on_success(service_root_callback));

    function service_root_callback(root_object) {
        var success = (root_object instanceof Launchpad &&
                       root_object.people_collection_link ==
                       "https://launchpad.dev/api/beta/people");
        report_test("Fetching root yields Launchpad object", success);

        //Now that we have the object, run some more tests.
        root_object.follow_link('people',
                                on_success(follow_link_callback));
        root_object.follow_link('me',
                                on_success(follow_link_through_redirect_callback));

    }

    function follow_link_callback(collection) {
        var success = (collection instanceof Collection
                       && collection.total_size == 4);
        report_test("Following link yields correct object", success);
    }

    function follow_link_through_redirect_callback(entry) {
        var success = (entry instanceof Entry
                       && entry.name == 'name16');
        report_test("Following link through redirect yields correct object",
                    success);
    }


    // Test an Entry object.
    client.get('~salgado', on_success(entry_callback));

    function entry_callback(entry) {
        var success = (entry instanceof Entry
                       && entry.name == "salgado");
        report_test("Fetching entry yields Entry object", success);

        // Now that we have the object, run some more tests.
        entry.display_name = "A new display name.";
        entry.lp_save(on_success(entry_save_callback));
    }

//         deferred = entry.follow_link('mugshot');
//         deferred.addCallback(nonexistent_hosted_file_callback);
//         deferred.addErrback(default_errback);
//     }

     function entry_save_callback(entry) {
         report_test("Entry object can be saved", true);
         client.get('~salgado', on_success(modified_entry_callback));
     }

     function modified_entry_callback(entry) {
         var success = (entry.display_name == "A new display name.");
         report_test("Modifications are stored persistently", success);

         // Change the display name back for the next time the test is
         // run.
         entry.display_name = "Reset display name.";
         entry.lp_save(on_success(function () {}));

     }

//     function nonexistent_hosted_file_callback(hosted_file) {
//         var success = (hosted_file instanceof HostedFile
//                        && hosted_file.uri.indexOf("~salgado/mugshot")
//                        != -1);
//         report_test("Following link to nonexistent hosted file yields " +
//                     "HostedFile object", success);
//     }

//     // Test hosted file objects.

//     // To test PUT to a hosted file we need to create a brand new
//     // file. Several problems combine to make this necessary. The
//     // first is that you can't send a binary file through XHR: it gets
//     // truncated at the first null character. So we can't just PUT to
//     // a mugshot or icon. There are some product release files in the
//     // preexisting dataset, but they don't have anything backing them
//     // in the librarian, so we can't get a proper handle on them. So
//     // we need to create a brand new file and then test PUT on it.

//     var bug_uri = 'bugs/15';
//     var deferred = client.named_post(bug_uri, 'addAttachment',
//                                      {comment: 'A new attachment',
//                                       content_type: 'text/plain',
//                                       data: 'Some data.',
//                                       filename: 'foo.txt'});
//     deferred.addCallback(new_attachment_callback);
//     deferred.addErrback(default_errback);

//     function new_attachment_callback(attachment) {
//         var hosted_file = attachment.get_hosted_file('data');
//         hosted_file.contents = "['Unit tester was here.']";
//         hosted_file.filename = "unittest.json";
//         hosted_file.content_type = "application/json";

//         var deferred = hosted_file.lp_save();
//         deferred.addCallback(modified_hosted_file_callback, hosted_file);
//         deferred.addErrback(default_errback);
//     }

//     function modified_hosted_file_callback(hosted_file, result) {
//         success = (result.status == 200);
//         report_test("Hosted file resource can be modified", success);

//         var deferred = hosted_file.lp_delete();
//         deferred.addCallback(deleted_hosted_file_callback);
//         deferred.addErrback(default_errback);
//     }

//     function deleted_hosted_file_callback(result) {
//         success = (result.status == 200);
//         report_test("Hosted file resource can be deleted", success);
//     }


     // Test a Collection object.
     client.get("people/", on_success(collection_callback));
     function collection_callback(collection) {
         var success = (collection instanceof Collection
                        && collection.total_size == 4);
         report_test("Fetching collection yields Collection object", success);

         // Now that we have the object, run some more tests.

         collection.lp_slice(on_success(collection_slice_callback), 2, 1);
         function collection_slice_callback(collection) {
             var success = (collection.start == 2
                            && collection.entries.length == 1);
             report_test("Slicing a collection", success);
         }

         collection.named_get('find',
                              on_success(collection_named_get_callback),
                              {text: 'salgado'});

         function collection_named_get_callback(collection) {
             var success = (collection instanceof Collection
                            && collection.total_size == 1);
             report_test("Invoking named GET on a resource", success);
         }

         collection.named_get('find',
                              on_success(paged_collection_named_get_callback),
                              {text: 'salgado'}, 10);

         function paged_collection_named_get_callback(collection) {
             var success = (collection instanceof Collection
                            && collection.entries.length == 0);
             report_test("Paging works with named GET on a collection",
                         success);
         }

//         // These aren't real unit tests, and the dataset isn't reset
//         // after they run. Generate a unique team name so that the
//         // team-creation test can be run multiple times.
//         name = "newteam" + (new Date()).getTime();
//         var deferred = collection.named_post('newTeam',
//                                              {display_name:
//                                               'My new team', name: name});
//         deferred.addCallback(collection_named_post_callback);
//         deferred.addErrback(default_errback);
     }




//     function collection_named_post_callback(new_entry) {
//         var success = (new_entry instanceof Entry
//                        && new_entry.display_name == "My new team"
//                        && new_entry.lp_original_uri.indexOf("/~newteam") != -1);
//         report_test("Named POST works and newborn entry is retrieved",
//                     success);
//     }
}
