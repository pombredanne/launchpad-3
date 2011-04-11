YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.subscription', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscription Tests");
var module = Y.lp.bugs.subscription;

/*
 * Test selection of the string by the number.
 * We expect to receive a plural string for all numbers
 * not equal to 1, and a singular string otherwise.
 */
suite.add(new Y.Test.Case({
    name: 'Choose string by number',

    test_singular: function() {
        Y.Assert.areEqual(
            'SINGULAR',
            module._choose_string_by_number(1, 'SINGULAR', 'PLURAL'));
    },

    test_plural: function() {
        Y.Assert.areEqual(
            'PLURAL',
            module._choose_string_by_number(5, 'SINGULAR', 'PLURAL'));
    },

    test_zero: function() {
        Y.Assert.areEqual(
            'PLURAL',
            module._choose_string_by_number(0, 'SINGULAR', 'PLURAL'));
    }
}));


var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});

