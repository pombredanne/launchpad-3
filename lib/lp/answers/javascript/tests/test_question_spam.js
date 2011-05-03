YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.questions.question_spam',
           'node-event-simulate',
           function(Y) {

var suite = new Y.Test.Suite("lp.questions.question_spam Tests");

suite.add(new Y.Test.Case({
    name: 'Does marking a questionmessage as spam from the ui work.'

    setUp: function () {},

    tearDown: function() {},

    test_set_spam: function() {
        link_node = Y.one('mark-spam');
        Assert.areEqual(link_node, '<a href="#">Mark as Spam</a>', 'foo!');
        Y.Event.simulate(Y.Node.getDOMNode(link_node), 'click');
    },

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
    alert('Running!');
    Y.Test.Runner.run();
});
});
