/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: true // DO NOT CHECK IN.
    }).use('test', 'console', 'lp.app.accordionoverlay', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

/* Helper function to cleanup and destroy a form wizard instance */
function cleanup_widget(ao) {
    if (ao.get('rendered')) {
        var bb = ao.get('boundingBox');
        if (Y.Node.getDOMNode(bb)){
            bb.get('parentNode').removeChild(bb);
        }
    }
    // Kill the widget itself.
    ao.destroy();
}

//var module = Y.lp.app.accordionoverlay;
var suite = new Y.Test.Suite("AccordionOverlay Tests");

suite.add(new Y.Test.Case({
    name: 'basics',
    test_can_be_instantiated: function() {
	var ao = new Y.lp.app.accordionoverlay.AccordionOverlay({
	});
	Assert.isInstanceOf(
	    Y.lp.app.accordionoverlay.AccordionOverlay,
	    ao,
	    "AccordionOverlay could not be instantiated");
	cleanup_widget(ao);
    }
}));

// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.get('body').appendChild(status_node);
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
