/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.large_indicator.test', function(Y) {

var large_indicator = Y.namespace('lp.large_indicator.test');

var suite = new Y.Test.Suite('Indicator Tests');

var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'large_indicator_tests',

    setUp: function() {
        this.div = Y.Node.create('<div></div>');
        this.div.generateID();
        this.div_id = this.div.get('id');
        Y.one('body').appendChild(this.div);
    },

    tearDown: function() {
        // delete the reference to this.div so we can recreate new ones for
        // each test without worry
        delete this.div;

    },

    test_target_attribute: function() {
        // Indicators should store a reference to the target
        // indicator is used for.
        var test_node = Y.one('#' + this.div_id);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: test_node
        });

        indicator.render();
        Assert.areEqual(test_node, indicator.get('target'));
    },

    test_indicator_has_loading_icon: function() {
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

    test_size_matches_target: function() {
        // The width and height of the indicator matches target
        // which it covers.
        var expected_width = 800;
        var expected_height = 600;
        this.div.set('offsetWidth', expected_width);
        this.div.set('offsetHeight', expected_height);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        var box = indicator.get('boundingBox');
        Assert.areEqual(expected_width, box.get('offsetWidth'));
        Assert.areEqual(expected_height, box.get('offsetHeight'));
    },

    test_position_matches_target: function() {
        // The X and Y position of the widget should match
        // what it covers.
        var expected_left = 200;
        var expected_top = 400;
        this.div.setStyle('position', 'absolute');
        this.div.setStyle('left', expected_left);
        this.div.setStyle('top', expected_top);
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div
        });
        indicator.render();
        var box = indicator.get('boundingBox');
        Assert.areEqual(expected_left, box.get('offsetLeft'));
        Assert.areEqual(expected_top, box.get('offsetTop'));
    },

    test_indiciator_disabled: function () {
        // verify that the disabled flag passed in is set
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: Y.one('#test-div'),
            disabled: true
        });

        Assert.isTrue(indicator.get('disabled'));

    },

    test_indicator_show: function() {
        // indicator.show() should provide an overlay
        // to cover the target it's meant to cover.
        var indicator = new Y.lp.indicator.OverlayIndicator({
            target: this.div,
            disabled: true
        });

        indicator.render();

        var box = indicator.get('boundingBox');
    },

    // test_size_matches_when_show: function() {
    //     // We should resize on show in case page
    //     // state has changed. call syncUI on show

    // },

    // test_position_matches_when_show: function() {
    //     // We should reposition on show in case page
    //     // state has changed. call syncUI on show

    // },

    // test_indicator_success_notification: function() {
    //     // Test what happens after clearing show
    //     // on success

    // },

    // test_indicator_failure_notification: function() {
    //     // test what happens after clearinging show
    //     // on error
    // }

}));

large_indicator.suite = suite;

}, '0.1', {'requires': ['test', 'lp.indicator']});
