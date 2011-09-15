YUI().use('lp.testing.runner', 'test', 'console',
    'lp.app.links', 'lp.testing.mockio', 'lp.client',
    'node',
    function(Y) {

    var links = Y.lp.app.links;
    var suite = new Y.Test.Suite("lp.app.links Tests");
    var mock_io = new Y.lp.testing.mockio.MockIo();

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'test_bugs',

        setUp: function() {
            links.check_valid_lp_links(mock_io);
            var response_json = ['{"bug_links": {"valid": {"/bugs/14"',
            ': "jokosher exposes personal details in its actions portlet"}',
            ', "invalid": {"/bugs/200": "Bug 200 cannot be found"}}, ',
            '"branch_links": {"invalid": {"/+branch/invalid": "No such',
            ' product: \'foobar\'."}}}'].join('');
            mock_io.success({
                responseText: response_json,
                responseHeaders: {'Content-type': 'application/json'}
            });
        },

        test_bugs: function () {
            var validbug = Y.one('#valid-bug');
            var invalidbug = Y.one('#invalid-bug');
            Y.Assert.isTrue(validbug.hasClass('bug-link'));
            Y.Assert.isTrue(invalidbug.hasClass('invalid-link'));
            Y.Assert.areSame(
            'jokosher exposes personal details in its actions portlet',
            validbug.get('title'));
        },
        test_branch: function () {
            var validbranch = Y.one('#valid-branch');
            var invalidbranch = Y.one('#invalid-branch');
            Y.Assert.isTrue(validbranch.hasClass('branch-short-link'));
            Y.Assert.isTrue(invalidbranch.hasClass('invalid-link'));
        }
    }));

    Y.lp.testing.Runner.run(suite);
});

