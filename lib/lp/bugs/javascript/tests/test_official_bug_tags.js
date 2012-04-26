YUI().use('lp.testing.runner', 'base', 'test', 'console', 'node',
           'node-event-simulate', 'lp.bugs.official_bug_tags', function(Y) {

var suite = new Y.Test.Suite("Official Bug Tags Tests");
var module = Y.lp.bugs.official_bug_tags;


suite.add(new Y.Test.Case({
    name: 'Official Bug Tags',

    setUp: function() {
        this.fixture = Y.one('#fixture');
        var tags_form = Y.Node.create(
            Y.one('#form-template').getContent());
        this.fixture.appendChild(tags_form);
    },

    tearDown: function() {
        if (this.fixture !== null) {
            this.fixture.empty();
        }
        delete this.fixture;
    },

    test_setup_bug_tags_table: function() {
        // The bug tags table is visible and the html form is not.
        module.setup_official_bug_tag_management();
        html_form = Y.one('[name=launchpadform]');
        tags_table = Y.one('#layout-table');
        Y.Assert.areEqual('none', html_form.getStyle('display'));
        Y.Assert.areEqual('block', tags_table.getStyle('display'));
    },

    test_on_new_tag_add_display_error: function() {
        // Adding a tag with an invalid name displays a message.
        module.setup_official_bug_tag_management();
        Y.one('#new-tag-text').set('value', 'me!');
        var new_tag_button = Y.one('#new-tag-add');
        new_tag_button.set('disabled', false);
        new_tag_button.simulate('click');
        var message_overlay = Y.one('.official-tag-error-message');
        Y.Assert.isNotNull(message_overlay);
        var tag = message_overlay.one(".official-tag-error-message-value");
        Y.Assert.isTrue(message_overlay.get('text').indexOf('me!') !== -1);
    }
}));

Y.lp.testing.Runner.run(suite);
});
