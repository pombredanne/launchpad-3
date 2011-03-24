/* Copyright (c) 2011, Canonical Ltd. All rights reserved.
 *
 * Display an accordion in a lazr.formoverlay.
 *
 * @module lp.app.accordionoverlay
 */
YUI.add('lp.app.accordionoverlay', function(Y) {

    var namespace = Y.namespace('lp.app.accordionoverlay');

    function AccordionOverlay(config) {
	AccordionOverlay.superclass.constructor.apply(this, arguments);
    }

    AccordionOverlay.NAME = "lp-accordionoverlay";

    Y.extend(AccordionOverlay, Y.lazr.FormOverlay, {
	initializer: function() {
	    // Do nothing.
	},
	destructor: function() {
	    // Do nothing.
	},
	bindUI: function() {
	    // Set up model.
	    var accordion = Y.Accordion({
		srcNode: "",
		}
	    )
	},
	renderUI: function() {
	    // Insert into DOM.
	},
	syncUI: function() {
	    // Update DOM.
	},

    });

    namespace.AccordionOverlay = AccordionOverlay;

}, "0.1", {"skinnable": true, "requires": ["lazr.formoverlay", "widget", "widget-parent"]});
