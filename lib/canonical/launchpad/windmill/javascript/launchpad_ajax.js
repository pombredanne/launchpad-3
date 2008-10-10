// Unit testing framework for the Launchpad AJAX test suite.

var client = new LaunchpadClient();

function test_no_such_url() {
    /* Ensure that requesting a non-existent object raises a 404.
     *
     */
    client.get("no-such-url", { 
           success: function (response) {
                jum.assertTrue("no-such-url should have 404.", False);
           },
           failure: function (response) { 
                jum.assertEquals(response.status, 404);
           }
       });
}

function test_relative_callback() {
    client.get("", {
            success: function (response) {
                jum.assertTrue(launchpad instanceof Launchpad);
                jum.assertTrue(
                    launchpad.people_collection_link.match(/people$/));
            },
            failure: function (response) {
                jum.assertTrue("failed to retrieve launchpad", False);
            }
       });
}

