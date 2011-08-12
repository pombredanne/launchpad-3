YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.picker',
           'lp.answers.answercontacts',
           'event', 'node-event-simulate', 'dump', function(Y) {

var suite = new Y.Test.Suite("lp.answers.answercontacts Tests");
var module = Y.lp.answers.subscribers;


suite.add(new Y.Test.Case({
    name: 'QuestionAnswerContactsList constructor test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
        window.LP = {
            links: {},
            cache: { context: { web_link: "/~link", self_link: "/~link" }}
        };
    },

    tearDown: function() {
        this.root.remove();
        delete window.LP;
    },

    setUpLoader: function() {
        this.root.appendChild(
            Y.Node.create('<div />').addClass('container'));
        return new module.createQuestionSubscribersLoader({
            container_box: '.container'});
    },

    test_contacts_list_instantiation: function() {
        this.setUpLoader();
    },

    test_addContact: function() {
        // Check that the contact list has been created and can accept
        // new contacts. Answer contacts do not use subscription levels so
        // pass in '' and check this works as expected.
        var loader = this.setUpLoader(this.root);
        var node = loader.subscribers_list.addSubscriber(
            { name: 'user' }, '');

        // Node is constructed using _createSubscriberNode.
        Y.Assert.isTrue(node.hasClass('subscriber'));
        // And the ID is set inside addSubscriber() method.
        Y.Assert.areEqual('subscriber-user', node.get('id'));

        // And it nested in the subscribers-list of a 'Direct' section.
        var list_node = node.ancestor('.subscribers-list');
        Y.Assert.isNotNull(list_node);
        var section_node = list_node.ancestor(
            '.subscribers-section-default');
        Y.Assert.isNotNull(section_node);
    }
}));

Y.lp.testing.Runner.run(suite);

});
