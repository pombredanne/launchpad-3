YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.picker',
           'lp.bugs.subscribers',
           'event', 'node-event-simulate', 'dump', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscribers Tests");
var module = Y.lp.bugs.subscribers;


suite.add(new Y.Test.Case({
    name: 'BugSubscribersList constructor test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    setUpLoader: function() {
        this.root.appendChild(
            Y.Node.create('<div />').addClass('container'));
        var bug = { web_link: '/base', self_link: '/bug/1'};
        return new module.createBugSubscribersLoader({
            container_box: '.container',
            bug: bug,
            subscribers_details_view: '/+bug-portlet-subscribers-details'});
    },

    test_subscribers_list_instantiation: function() {
        this.setUpLoader();
    },

    test_addSubscriber: function() {
        // Check that the subscription list has been created with the expected
        // subscription levels for bugs. This can be done by adding a
        // subscriber to one of the expected levels and checking the results.
        var loader = this.setUpLoader(this.root);
        var node = loader.subscribers_list.addSubscriber(
            { name: 'user' }, 'Lifecycle');

        // Node is constructed using _createSubscriberNode.
        Y.Assert.isTrue(node.hasClass('subscriber'));
        // And the ID is set inside addSubscriber() method.
        Y.Assert.areEqual('subscriber-user', node.get('id'));

        // And it nested in the subscribers-list of a 'Level3' section.
        var list_node = node.ancestor('.subscribers-list');
        Y.Assert.isNotNull(list_node);
        var section_node = list_node.ancestor(
            '.subscribers-section-lifecycle');
        Y.Assert.isNotNull(section_node);
    }
}));

Y.lp.testing.Runner.run(suite);

});
