//function check_links() {
//    alert("Hello World from check links")
//}
//registerLaunchpadFunction(check_links);

YUI().add('lp.app.linkchecker', function(Y) {

    var namespace = Y.namespace('lp.app.linkchecker');

    namespace.checklinks = function() {
        Y.io('+check-links', {
            on: {
                success: function(id, response) {
                    alert("Success: " +  + id + ", " + response.responseText)
                },
                failure: function(id, response) {
                    alert('Error: ' + id + ", " + response.responseText);
                }
            }
        });
    }

}, "0.1", {"requires": ["base", "lp.client.plugins"]});

