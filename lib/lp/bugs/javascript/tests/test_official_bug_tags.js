YUI().use('lp.testing.runner', 'base', 'test', 'console',
          'node', 'lp.bugs.official_bug_tags', function(Y) {

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
    }
}));

Y.lp.testing.Runner.run(suite);
});
