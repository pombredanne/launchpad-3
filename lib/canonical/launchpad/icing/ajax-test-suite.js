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
    var client = new LP.client.Launchpad();

    function on_success(callback) {
        /* Generate a default set of callbacks. */
        return { success: callback, failure: default_errback };
    }

     function hosted_file_callback(hosted_file) {
         var success = (hosted_file instanceof LP.client.HostedFile
                        && hosted_file.uri.indexOf("~salgado/mugshot")
                        != -1);
         report_test("Following link to nonexistent hosted file yields " +
                     "HostedFile object", success);

        hosted_file.lp_delete(on_success(deleted_hosted_file_callback));
     }

     // Test hosted file objects.

     // To test PUT to a hosted file we need to create a brand new
     // file. Several problems combine to make this necessary. The
     // first is that you can't send a binary file through XHR: it gets
     // truncated at the first null character. So we can't just PUT to
     // a mugshot or icon. There are some product release files in the
     // preexisting dataset, but they don't have anything backing them
     // in the librarian, so we can't get a proper handle on them. So
     // we need to create a brand new file and then test PUT on it.

     var bug_uri = 'bugs/15';
     client.named_post(bug_uri, 'addAttachment',
                       {on: on_success(new_attachment_callback),
                               parameters: {comment: 'A new attachment',
                                   content_type: 'text/plain',
                                   data: 'Some data.',
                                   filename: 'foo.txt'}});

     function new_attachment_callback(attachment) {
         report_test("Hosted file created via named POST", true);
         attachment.follow_link('data',
                                on_success(edit_hosted_file_callback));
     }

     function edit_hosted_file_callback(hosted_file) {
         hosted_file.contents = "['Unit tester was here.']";
         hosted_file.filename = "unittest.json";
         hosted_file.content_type = "application/json";
         hosted_file.lp_save(on_success(modified_hosted_file_callback));
     }

     function modified_hosted_file_callback(object, result, hosted_file) {
         var success = (result.status == 200);
         report_test("Hosted file resource can be modified", success);

         // XXX The request will be sent, but will fail with 500
         // because a bug attachment can't actually be deleted.
         var callback = { success: deleted_hosted_file_callback,
                          failure: function() {
                 default_errback("Can't DELETE a bug attachment--" +
                                 "but this is expected behavior");
             }
         };
         hosted_file.lp_delete(callback);
     }

     function deleted_hosted_file_callback(object, result, hosted_file) {
         success = (result.status == 200);
         report_test("Hosted file resource can be deleted", success);
     }


     // Test a Collection object.
     client.get("people/", {on: on_success(collection_callback)});
     function collection_callback(collection) {
        // These aren't real unit tests, and the dataset isn't reset
        // after they run. Generate a unique team name so that the
        // team-creation test can be run multiple times.
        name = "newteam" + new Date().getTime();
        collection.named_post('newTeam',
                              {on: on_success(collection_named_post_callback),
                                      parameters: {display_name: 'My new team',
                                          name: name}});
     }


     function collection_named_post_callback(new_entry) {
         var success = (new_entry instanceof LP.client.Entry
                        && new_entry.display_name == "My new team"
                        && new_entry.lp_original_uri.indexOf("/~newteam")
                        != -1);
         report_test("Named POST works and newborn entry is retrieved",
                     success);
     }
}
