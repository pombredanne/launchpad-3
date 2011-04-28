YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.bug_spam',
           'node-event-simulate',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.bug_spam Tests");
var module = Y.lp.bugs.bug_spam;

/**
 * Test is_notification_level_shown() for a given set of
 * conditions.
 */
suite.add(new Y.Test.Case({
    name: 'Does marking a bug as spam from the ui work.'

    setUp: function () {},

    tearDown: function() {},

    test_set_spam: function() {},

    test_set_not_spam: function() {},
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
