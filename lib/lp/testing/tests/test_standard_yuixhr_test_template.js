YUI({
    base: '/+icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
// TODO: Add other modules you want to test into the "use" list.
}).use('test', 'lp.testing.serverfixture',
       function(Y) {

// This is one-half of an example yuixhr test.  The other half of a
// test like this is a file of the same name but with a .py
// extension.  It holds the fixtures that this file uses for
// application setup and teardown.  It also helps the Launchpad
// testrunner know how to run these tests.  The actual tests are
// written here, in Javascript.

// These tests are expensive to run.  Keep them to a minimum,
// preferring pure JS unit tests and pure Python unit tests.

// TODO: Change this string to match what you are doing.
var suite = new Y.Test.Suite("lp.testing.yuixhr Tests");
var serverfixture = Y.lp.testing.serverfixture;


// TODO: change this explanation string.
/**
 * Test important things...
 */
suite.add(new Y.Test.Case({
    // TODO: change this name.
    name: 'Example tests',

    tearDown: function() {
        // Always do this.
        serverfixture.teardown(this);
    },

    // Your tests go here.
    test_example: function() {
        // In this example, we care about the return value of the setup.
        // Sometimes, you won't.
        var data = serverfixture.setup(this, 'example');
        // Now presumably you would test something, maybe like this.
        var response = Y.io(
            data.product.self_link,
            {sync: true}
            );
        Y.Assert.areEqual(200, response.status);
    }
}));

// The last line is necessary.  Include it.
serverfixture.run(suite);
});
