/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'dom', 'lazr.overlay', 'lazr.activator',
                'lp.client', 'lp.app.multicheckbox', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("lp.app.multicheckbox Tests");

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        bb.get('parentNode').removeChild(bb);
    }
    // Kill the widget itself.
    widget.destroy();
}

suite.add(new Y.Test.Case({
    name: "lp.app.multicheckbox",

    setUp: function() {
      // Create a widget with some default data
      this.widget = Y.lp.app.multicheckbox.addMultiCheckboxPatcher(
        [{"token": "0", "style": "font-weight: normal;", "checked": true,
            "name": "Item 1", "value": "item1"},
        {"token": "1", "style": "font-weight: normal;", "checked": false,
            "name": "Item 2", "value": "item2"}],
        'A test',
        '/~fred/+recipe/a-recipe',
        'multicheckboxtest',
        'reference',
        'edit-test',
        {"header": ["Test multicheckbox widget:"], "empty_display_value": "None"})
    },

    tearDown: function() {
        cleanup_widget(this.widget);
    },

    test_widget_can_be_instantiated: function() {
        Assert.isInstanceOf(
            Y.lazr.PrettyOverlay, this.widget,
            "Widget failed to be instantiated");
    },

//    test_widget_header: function() {
//        // Check the header text value.
//        Y.Assert.areEqual(this.widget.get('headerContent', '<h2>Test multicheckbox widget:</h2>'));
//    },

    test_widget_has_correct_choices: function() {
        // Make sure the correct checkboxes are rendered.
        for( var x=0; x<2; x++ ) {
            var item = Y.one('input[id="field.multicheckboxtest.'+x+'][type=checkbox]');
            Y.Assert.areEqual(item.getAttribute('value'), x);
            Y.Assert.areEqual(item.get('checked'), x==0);
        }
    }

}));


// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
