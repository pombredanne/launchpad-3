function check_links() {
    alert("Hello World from check links")
}
registerLaunchpadFunction(check_links);

YUI().add('lp.app.linkchecker', function(Y) {

    var namespace = Y.namespace('lp.app.linkchecker');

    var lp_client;          // The LP client

    namespace.hello = function(arg) {
        alert("Hello hello " + arg)
    }

}, "0.1", {"requires": ["base", "lp.client.plugins"]});