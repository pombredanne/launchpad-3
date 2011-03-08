YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: true
    }).use('test', 'console', function(Y) {
    var suite = new Y.Test.Suite("mynamespace Tests");

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'setup',

        test_something: function() {
            Y.AssertTrue(false);
            },
        }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
