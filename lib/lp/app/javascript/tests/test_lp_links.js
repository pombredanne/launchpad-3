YUI().use('lp.testing.runner', 'test', 'console', 
    'lp.app.links', 'lp.testing.mockio', 'lp.client', 
    function(Y) {

    var links = Y.lp.app.links;
    var suite = new Y.Test.Suite("lp.app.links Tests");
    var mock_io = new Y.lp.testing.mockio.MockIo();

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'test_bugs',

        test_hide: function () {
            links.check_valid_lp_links(mock_io);
            mock_io.success({
                responseText: '{"bug_links": {"valid": {"/bugs/14": "jokosher exposes personal details in its actions portlet"}, "invalid": {"/bugs/200": "Bug 200 cannot be found"}}, "branch_links": {"invalid": {"/+branch/invalid": "No such product: \'foobar\'."}}}',
                responseHeaders: {'Content-type': 'application/json'}
            });
            Y.Assert.areSame(0,1);
            },
        }));

    Y.lp.testing.Runner.run(suite);
});

