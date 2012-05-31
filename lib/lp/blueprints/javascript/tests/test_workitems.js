YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.picker',
          'lp.workitems.expanders',
          'event', 'node-event-simulate', 'dump', function(Y) {

var suite = new Y.Test.Suite("lp.workitems.expanders Tests");
var module = Y.lp.workitems.expanders;

suite.add(new Y.Test.Case({
    name: 'setUpWorkItemExpanders test',

    setUp: function() {
    },

    tearDown: function() {
    },

    test_setUpWorkItemExpanders: function() {
        Y.all('.collapsible-body').each(function(e) {
            Y.Assert.isFalse(e.hasClass('lazr-closed'));
        });

        Y.all('[class=expandable]').each(function(e) {
            module._add_expanders(e);
        });

        Y.all('.collapsible-body').each(function(e) {
            Y.Assert.isTrue(e.hasClass('lazr-closed'));
        });
    },

    test_attach_expandall_handler: function() {

        Y.all('.expandall_link').on("click", function(event){
            module.attach_expandall_handler(event);
        });

    }
}));

Y.lp.testing.Runner.run(suite);

});
