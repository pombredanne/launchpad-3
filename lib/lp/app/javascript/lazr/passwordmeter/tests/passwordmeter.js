/* Copyright (c) 2008, Canonical Ltd. All rights reserved. */

YUI().use('lazr.passwordmeter', 'lazr.testing.runner', 'node',
          'event', 'console', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        if (bb.get('parentNode')) {
            bb.get('parentNode').removeChild(bb);
        }
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("LAZR Password Meter Tests");

function setUp() {
    Y.log("top of setUp");
    // add the in-page HTML
    var markup = Y.Node.create([
        '<div id="all">',
        '<input type="password" id="password"/>',
        '<div id="meter"></div>',
        '</div>'].join(''));
    Y.log(markup);
    Y.one("body").appendChild(markup);
    this.config = this.make_config();
    this.passwordMeter = new Y.PasswordMeter(this.config);
    this.passwordMeter.render();
}

function tearDown() {
    if (this.passwordMeter) {
        cleanup_widget(this.passwordMeter);
    }
    var all = Y.one("document").one("#all");
    if (all) {
        all.get("parentNode").removeChild(all);
    }
}

var strengthFunc = function(password){
	var strength = password.length * 10;
	var text = "";
	if (strength > 100)
		strength = 100;
	switch (strength) {
		case 10:
		case 20:
			color = '#8b0000';
			text = "Weak";
			break;
		case 30:
		case 40:
		case 50:
			color = '#f99300';
			text = "Average";
			break;
		case 60:
		case 70:
			color = '#f003ff';
			text = "Better";
			break;
		case 80:
		case 90:
		case 100:
			color = '#00FF00';
			text = "Strong";
			break;
		default:
			color = '#FF0000';
			text = "Weak";
	}
	return {
		"color": color,
		"text": text
	};
}

function simulatePasswordUpdate(key, value) {
    element = document.getElementById("password");
    element.value = value;
    Y.Event.simulate(element, 'keyup', { keyCode: key });
}

suite.add(new Y.Test.Case({

    name: 'password_meter_tests',

    setUp: setUp,

    tearDown: tearDown,

    make_config: function() {
        return {
            meter:       '#meter',
            input:       '#password',
            func: strengthFunc
        };
    },

    test_for_correct_color: function() {
        simulatePasswordUpdate(65, 'A');
        simulatePasswordUpdate(65, '');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(255, 0, 0)');
        simulatePasswordUpdate(65, 'A');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(139, 0, 0)');
        simulatePasswordUpdate(66, 'AB');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(139, 0, 0)');
        simulatePasswordUpdate(67, 'ABC');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(249, 147, 0)');
        simulatePasswordUpdate(68, 'ABCD');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(249, 147, 0)');
        simulatePasswordUpdate(69, 'ABCDE');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(249, 147, 0)');
        simulatePasswordUpdate(70, 'ABCDEF');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(240, 3, 255)');
        simulatePasswordUpdate(71, 'ABCDEFG');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(240, 3, 255)');
        simulatePasswordUpdate(72, 'ABCDEFGH');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(0, 255, 0)');
        simulatePasswordUpdate(73, 'ABCDEFGHI');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'),'rgb(0, 255, 0)');
        simulatePasswordUpdate(74, 'ABCDEFGHIJ');
        Assert.areEqual(this.passwordMeter.get('contentBox').getStyle('color'), 'rgb(0, 255, 0)');
    },

    test_for_correct_text: function() {
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), '');
        simulatePasswordUpdate(65, 'A');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Weak');
        simulatePasswordUpdate(66, 'AB');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Weak');
        simulatePasswordUpdate(67, 'ABC');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Average');
        simulatePasswordUpdate(68, 'ABCD');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Average');
        simulatePasswordUpdate(69, 'ABCDE');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Average');
        simulatePasswordUpdate(70, 'ABCDEF');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Better');
        simulatePasswordUpdate(71, 'ABCDEFG');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Better');
        simulatePasswordUpdate(72, 'ABCDEFGH');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Strong');
        simulatePasswordUpdate(73, 'ABCDEFGHI');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Strong');
        simulatePasswordUpdate(74, 'ABCDEFGHIJ');
        Assert.areEqual(this.passwordMeter.get('contentBox').get('innerHTML'), 'Strong');
    }

}));

Y.lazr.testing.Runner.add(suite);
Y.lazr.testing.Runner.run();

});
