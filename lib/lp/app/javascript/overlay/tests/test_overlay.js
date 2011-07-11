/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.overlay',
           'event', 'event-simulate', 'widget-stack', function(Y) {

// KeyCode for escape
var ESCAPE = 27;

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
    if (!widget) {
        return;
    }
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        bb.get('parentNode').removeChild(bb);
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("LAZR Pretty Overlay Tests");

suite.add(new Y.Test.Case({

    name: 'pretty_overlay_basics',

    setUp: function() {
        this.overlay = null;
    },

    tearDown: function() {
        cleanup_widget(this.overlay);
    },

    hitEscape: function() {
        simulate(this.overlay.get('boundingBox'),
                 '.close .close-button',
                 'keydown', { keyCode: ESCAPE });
    },

    test_picker_can_be_instantiated: function() {
        this.overlay = new Y.lazr.PrettyOverlay();
        Assert.isInstanceOf(
            Y.lazr.PrettyOverlay, this.overlay, "Overlay not instantiated.");
    },

    test_overlay_has_elements: function() {
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();
        var bb = this.overlay.get('boundingBox');
        Assert.isNotNull(
            bb.one('.close'),
            "Missing close button div.");
        Assert.isNotNull(
            bb.one('.close .close-button'),
            "Missing close button.");
    },

    test_overlay_can_show_progressbar: function() {
        this.overlay = new Y.lazr.PrettyOverlay({'headerContent': 'bu bu bu'});
        var bb = this.overlay.get('boundingBox');
        this.overlay.render();
        Assert.isNotNull(
            bb.one('.steps'),
            "Progress bar is not present.");
    },

    test_overlay_can_hide_progressbar: function() {
        this.overlay = new Y.lazr.PrettyOverlay({progressbar: false});
        this.overlay.render();
        var bb = this.overlay.get('boundingBox');
        bb.set('headerContent', 'ALL HAIL DISCORDIA!');
        Assert.isNull(
            bb.one('.steps'),
            "Progress bar is present when it shouldn't be.");
    },

    test_overlay_can_show_steptitle: function() {
        this.overlay = new Y.lazr.PrettyOverlay({
            'headerContent': 'Fnord',
            'steptitle': 'No wife, no horse and no moustache'});
        var bb = this.overlay.get('boundingBox');
        this.overlay.render();
        Assert.isNotNull(
            bb.one('.contains-steptitle h2'),
            "Step title is not present.");
    },

    test_overlay_can_hide_steptitle: function() {
        this.overlay = new Y.lazr.PrettyOverlay({progressbar: false});
        this.overlay.render();
        var bb = this.overlay.get('boundingBox');
        bb.set('headerContent', 'ALL HAIL DISCORDIA!');
        Assert.isNull(
            bb.one('.contains-steptitle h2'),
            "Step title is present when it shouldn't be.");
    },

    test_click_cancel_hides_the_widget: function() {
        /* Test that clicking the cancel button hides the widget. */
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();

        simulate(this.overlay.get('boundingBox'), '.close .close-button', 'click');
        Assert.isFalse(this.overlay.get('visible'), "The widget wasn't hidden");
    },

    test_click_cancel_fires_cancel_event: function() {
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();

        var event_was_fired = false;
        this.overlay.subscribe('cancel', function() {
                event_was_fired = true;
        }, this);
        simulate(this.overlay.get('boundingBox'), '.close .close-button','click');
        Assert.isTrue(event_was_fired, "cancel event wasn't fired");
    },

    test_stroke_escape_hides_the_widget: function() {
        /* Test that stroking the escape button hides the widget. */
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();

        Assert.isTrue(this.overlay.get('visible'), "The widget wasn't visible");
        this.hitEscape();
        Assert.isFalse(this.overlay.get('visible'), "The widget wasn't hidden");
    },

    test_stroke_escape_fires_cancel_event: function() {
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();

        var event_was_fired = false;
        this.overlay.subscribe('cancel', function() {
            event_was_fired = true;
        }, this);
        this.hitEscape();
        Assert.isTrue(event_was_fired, "cancel event wasn't fired");
    },

    test_show_again_re_hooks_events: function() {
        /* Test that hiding the overlay and showing it again
         * preserves the event handlers.
         */
        this.overlay = new Y.lazr.PrettyOverlay();
        this.overlay.render();

        this.hitEscape();
        Assert.isFalse(this.overlay.get('visible'), "The widget wasn't hidden");
        this.overlay.show();
        Assert.isTrue(this.overlay.get('visible'), "The widget wasn't shown again");
        this.hitEscape();
        Assert.isFalse(this.overlay.get('visible'), "The widget wasn't hidden");
    },

    test_pretty_overlay_without_header: function() {
        this.overlay = new Y.lazr.PrettyOverlay();
        function PrettyOverlaySubclass(config) {
            PrettyOverlaySubclass.superclass.constructor.apply(this, arguments);
        }
        PrettyOverlaySubclass.NAME = 'lazr-overlaysubclass';
        Y.extend(PrettyOverlaySubclass, Y.lazr.PrettyOverlay);

        var overlay = new PrettyOverlaySubclass({bodyContent: "Hi"});
        // This shouldn't raise an error if the header content is not
        // supplied and progressbar is set to `true`.
        overlay.render();
        cleanup_widget(overlay);
    },

    test_overlay_bodyContent_has_size_1: function() {
        this.overlay = new Y.Overlay({
            headerContent: 'Form for testing',
            bodyContent: '<input type="text" name="field1" />'
        });
        this.overlay.render();
        Assert.areEqual(
            1,
            this.overlay.get("bodyContent").size(),
            "The bodContent should contain only one node.");
    },

    test_set_progress: function() {
        // test that the progress bar is settable
        this.overlay = new Y.lazr.PrettyOverlay({
            'headerContent': 'Fnord',
            'steptitle': 'No wife, no horse and no moustache'});
        this.overlay.render();
        this.overlay.set('progress', 23);
        Assert.areEqual(
            '23%',
            this.overlay.get('boundingBox').one('.steps .step-on').getStyle('width')
        );
    }

}));

Y.lp.testing.Runner.run(suite);

});
