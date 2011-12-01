/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.large_indicator.test', function (Y) {

var large_indicator = Y.namespace('lp.large_indicator.test');
var suite = new Y.Test.Suite('Indicator Tests');
var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'indicator_tests',

    setUp: function () {
        this.div = Y.Node.create('<div></div>');

        // generate an id so we can keep these around as we work
        this.div.generateID();

        // some default styles to help visualize our indicator
        this.div.setStyles({
            'width': '50px',
            'height': '50px',
            'background-color': "#FFFCCC"
        });

        // we want to store this for the testing of the target, after that we
        // can just use this.div
        this.div_id = this.div.get('id');

        Y.one('body').appendChild(this.div);
    },

    tearDown: function () {
        // delete the reference to this.div so we can recreate new ones for
        // each test without worry
        // note that we leave the divs around for visual seeing what's going
        // on during testing and development
        this.div.remove();
        delete this.div;

        // destroy any left over indicator instances we didn't get
        Y.all('.yui3-overlay-indicator').each(function (node) {
            var ind = Y.Widget.getByNode(node);
            ind.destroy();
        });
    },

    test_target_attribute: function () {
        // constrain attribute should be set from passing in target.
        var test_node = Y.one('#' + this.div_id);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: test_node
        });
        indicator.render();
        Assert.areEqual(test_node, indicator.get('target'));
    },

    test_indicator_appended_to_parent: function() {
        // indicator node is appended to target's parent, rather
        // than target or body.
        var child_div = Y.Node.create('<div></div>');
        // We need to create some nesting to really ensure
        // the test is good.
        this.div.appendChild(child_div);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: child_div
        });
        indicator.render();
        // this.div is actually the parentNode now.
        Assert.areEqual(
            this.div,
            indicator.get('boundingBox').get('parentNode'));
    },

    test_indicator_has_loading_icon: function () {
        // The indicator should have a loading image added
        // to the contentBox.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        var content = indicator.get('boundingBox');
        var test = content.getContent();
        var img = content.one('img');
        Assert.areEqual('file:///@@/spinner-big', img.get('src'));
    },

    test_indiciator_starts_invisible: function () {
        // indicator widgets should start hidden.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        Assert.isFalse(indicator.get('visible'), 'visible is not set');
        Assert.isTrue(indicator.get('boundingBox').hasClass(
            'yui3-overlay-indicator-hidden'), 'class does not exist');
    },

    test_set_busy_shows_overlay: function() {
        // setBusy should show the overlay.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        indicator.setBusy();
        Assert.isTrue(indicator.get('visible'), 'visible is not set');
        Assert.isFalse(indicator.get('boundingBox').hasClass(
            'yui3-overlay-indicator-hidden'), 'class does not exist');
    },

    test_size_matches_on_set_busy: function() {
        // indicator should always resize when target changes size.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        // Mess with the size of target div.
        var expected_width = 800;
        var expected_height = 600;
        this.div.set('offsetWidth', expected_width);
        this.div.set('offsetHeight', expected_height);
        Assert.areNotEqual(
            expected_width,
            indicator.get('boundingBox').get('offsetWidth'));
        Assert.areNotEqual(
            expected_height,
            indicator.get('boundingBox').get('offsetHeight'));
        indicator.setBusy();
        Assert.areEqual(
            expected_width,
            indicator.get('boundingBox').get('offsetWidth'));
        Assert.areEqual(
            expected_height,
            indicator.get('boundingBox').get('offsetHeight'));
    },

    test_position_matches_on_set_busy: function() {
        // indicator should always reposition itself before setBusy.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        // Mess with the position of target div.
        var expected_xy = [100, 300];
        this.div.setXY(expected_xy);
        var actual_xy = indicator.get('boundingBox').getXY();
        Assert.areNotEqual(expected_xy[0], actual_xy[0]);
        Assert.areNotEqual(expected_xy[1], actual_xy[1]);
        indicator.setBusy();
        var final_xy = indicator.get('boundingBox').getXY();
        Assert.areEqual(expected_xy[0], final_xy[0]);
        Assert.areEqual(expected_xy[1], final_xy[1]);

    },

    test_success_hides_overlay: function() {
        // Calling success should hide the overlay.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        indicator.setBusy();
        indicator.success();
        Assert.isFalse(indicator.get('visible'), 'visible is not set');
        Assert.isTrue(indicator.get('boundingBox').hasClass(
            'yui3-overlay-indicator-hidden'), 'class does not exist');
    },

    test_success_callback: function() {
        // We should be able to pass in a callback as success_action.
        var called = false;
        var callback = function() {
            called = true;
        };
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div,
            success_action: callback
        });
        indicator.render();
        indicator.success();
        Assert.isTrue(called);
    },

    test_focus_target_scrolls_success: function () {
        // Provided function scroll_to_target should scroll to target.
        var viewport = Y.DOM.viewportRegion();
        this.div.set('offsetWidth', viewport.right + 1000);
        this.div.set('offsetHeight', viewport.bottom + 1000);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div,
            success_action: Y.lp.indicator.actions.scroll_to_target
        });
        indicator.render();
        window.scrollTo(1000, 1000);

        Assert.areEqual(1000, Y.DOM.docScrollX());
        Assert.areEqual(1000, Y.DOM.docScrollY());

        indicator.setBusy();
        indicator.success();

        var expected_xy = indicator.get('target').getXY();
        Assert.areEqual(expected_xy[0], Y.DOM.docScrollX(), 'expected x');
        Assert.areEqual(expected_xy[1], Y.DOM.docScrollY(), 'expected y');
    },

    test_error_hides_overlay: function () {
        // Calling error should hide the overlay.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        indicator.setBusy();
        indicator.error();
        Assert.isFalse(indicator.get('visible'), 'visible is not set');
        Assert.isTrue(indicator.get('boundingBox').hasClass(
            'yui3-overlay-indicator-hidden'), 'class does not exist');
    },

    test_error_callback: function() {
        // We should be able to pass in a callback as error_action.
        var called = false;
        var callback = function() {
            called = true;
        };
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div,
            error_action: callback
        });
        indicator.render();
        indicator.error();
        Assert.isTrue(called);
    }
}));

large_indicator.suite = suite;

}, '0.1', {'requires': ['test', 'lp.indicator']});
