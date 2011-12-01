/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.large_indicator.test', function (Y) {

var large_indicator = Y.namespace('lp.large_indicator.test');
var suite = new Y.Test.Suite('Indicator Tests');
var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'large_indicator_tests',

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
        delete this.div;
    },

    /**
     * Verify that the indicator correctly stores the target they're assigned
     * to
     */
    test_target_attribute: function () {
        var test_node = Y.one('#' + this.div_id);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            constrain: test_node,
        });

        indicator.render(test_node);

        Assert.areEqual(
            test_node.getStyle('top'),
            indicator.get('constrain').getStyle('top'));
        Assert.areEqual(
            test_node.getStyle('left'),
            indicator.get('constrain').getStyle('left'));
    },

    /**
     * The indicator widget should add the img for the spinner when rendered
     */
    test_indicator_has_loading_icon: function () {
        // The indicator should have a loading image added
        // to the contentBox.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            constrain: this.div
        });
        indicator.render(this.div);
        var content = indicator.get('boundingBox');
        var test = content.getContent();
        var img = content.one('img');
        Assert.areEqual('file:///@@/spinner-big', img.get('src'));
    },

    /**
     * The indicator widget should be the same size as the target it overlays
     */
    test_size_matches_target: function() {
        var expected_width = 800;
        var expected_height = 600;

        this.div.set('offsetWidth', expected_width);
        this.div.set('offsetHeight', expected_height);

        var indicator = new Y.lp.indicator.OverlayIndicator({
            constrain: this.div
        });
        indicator.render(this.div);

        var box = indicator.get('boundingBox');
        Assert.areEqual(expected_width + "px", box.getStyle('width'));
        Assert.areEqual(expected_height + "px", box.getStyle('height'));
    },

    /**
     * The X/Y position of the indicator overlay should match the target X/Y
     */
    test_position_matches_target: function() {
        // The X and Y position of the widget should match
        // what it covers.
        var expected_left = 200;
        var expected_top = 400;
        this.div.setStyle('position', 'absolute');
        this.div.setStyle('left', expected_left);
        this.div.setStyle('top', expected_top);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            constrain: this.div
        });
        indicator.render(this.div);
        var box = indicator.get('boundingBox');
        Assert.areEqual(expected_left, box.getX());
        Assert.areEqual(expected_top, box.getY());
    },

    /**
     * When first rendered, the indicator widget should be disabled so you
     * don't see it. This is passed through to the widget part of the
     * indicator.
     */
    test_indiciator_disabled: function () {
        var indicator = new Y.lp.indicator.OverlayIndicator({
            constrain: Y.one('#test-div'),
            disabled: true
        });

        Assert.isTrue(indicator.get('disabled'));
    },

    /**
     * The indicator comes with a YUI Plugin to use on Node instances
     *
     * Test that we can attach it to the node, and then use the interface for
     * show/hide through it
     */
    test_indicator_plugin: function () {
        var node = this.div;

        node.plug(Y.lp.indicator.IndicatorPlugin);
        Assert.isTrue(!Y.Lang.isNull(node.indicator));

        // make sure .hide() will mark it disabled
        node.indicator.hide();
        Assert.isFalse(node.indicator.get('visible'));

        // and showing again
        node.indicator.show();
        Assert.isTrue(node.indicator.get('visible'));
    }

}));

large_indicator.suite = suite;

}, '0.1', {'requires': ['test', 'lp.indicator']});
