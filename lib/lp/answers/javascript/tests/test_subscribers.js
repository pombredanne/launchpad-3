YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.picker',
           'lp.answers.subscribers',
           'event', 'node-event-simulate', 'dump', function(Y) {

var suite = new Y.Test.Suite("lp.answers.subscribers Tests");
var module = Y.lp.answers.subscribers;


suite.add(new Y.Test.Case({
    name: 'QuestionSubscribersList constructor test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
        window.LP = {
            links: {},
            cache: { context: { web_link: "/~link" }}
        };
    },

    tearDown: function() {
        this.root.remove();
        delete window.LP;
    },

    setUpLoader: function() {
        this.root.appendChild(
            Y.Node.create('<div />').addClass('container'));
        var question = { web_link: '/base', self_link: '/question/1'};
        return new module.createQuestionSubscribersLoader({
            container_box: '.container',
            question: question,
            subscribers_details_view: '/+portlet-subscribers-details'});
    },

    test_subscribers_list_instantiation: function() {
        this.setUpLoader();
    },

    test_addSubscriber: function() {
        // Check that the subscription list has been created with the expected
        // subscription levels for questions. This can be done by adding a
        // subscriber to one of the expected levels and checking the results.
        var loader = this.setUpLoader(this.root);
        var node = loader.subscribers_list.addSubscriber(
            { name: 'user' }, 'Direct');

        // Node is constructed using _createSubscriberNode.
        Y.Assert.isTrue(node.hasClass('subscriber'));
        // And the ID is set inside addSubscriber() method.
        Y.Assert.areEqual('subscriber-user', node.get('id'));

        // And it nested in the subscribers-list of a 'Direct' section.
        var list_node = node.ancestor('.subscribers-list');
        Y.Assert.isNotNull(list_node);
        var section_node = list_node.ancestor(
            '.subscribers-section-direct');
        Y.Assert.isNotNull(section_node);
    }
}));

Y.lp.testing.Runner.run(suite);

});
