YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.picker',
          'lp.workitems.expanders',
          'event', 'node-event-simulate', 'dump', function(Y) {

var suite = new Y.Test.Suite("lp.workitems.expanders Tests");
var module = Y.lp.workitems.expanders;

suite.add(new Y.Test.Case({
    name: 'setUpWorkItemExpanders test',

    test_setUpWorkItemExpanders: function() {
        module.setUpWorkItemExpanders();
        /*
            TODO: Fake expander
                Just need to have something that records that it got an expand/collapse/render call

                -- Search was to see if one exists!
         */
    }
}));

Y.lp.testing.Runner.run(suite);

});
