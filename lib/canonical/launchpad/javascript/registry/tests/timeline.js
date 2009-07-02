/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('yuitest', 'console', 'registry.timeline', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("TimelineGraph Tests");

var MINIMAL_CONFIG = {
    timeline: [{
        name: 'trunk',
        uri: 'file:///firefox/trunk',
        is_development_focus: true,
        landmarks: []
    }]
};

var MEDIUM_CONFIG = {
    timeline: [
        {
            'name': 'testing',
            'uri': 'file:///firefox/1.0',
            'is_development_focus': true,
            'landmarks': [
                {
                    'code_name': 'warthog',
                    'date': '2056-10-16',
                    'name': 'alpha',
                    'type': 'milestone',
                    'uri': 'file:///firefox/+milestone/alpha'
                },
                {
                    'code_name': 'One (secure) Tree Hill',
                    'date': '2004-10-15',
                    'name': 'beta',
                    'type': 'release',
                    'uri': 'file:///firefox/trunk/beta'
                }
            ]
        }
    ]
};

suite.add(new Y.Test.Case({

    name: 'minimal-config',

    setUp: function() {
        this.timeline_graph = new Y.registry.timeline.TimelineGraph(
            MINIMAL_CONFIG);
        this.timeline_graph.render();
        this.content_box = this.timeline_graph.get('contentBox');
    },

    tearDown: function() {
        var bounding_box = this.timeline_graph.get('boundingBox')
        bounding_box.get('parentNode').removeChild(bounding_box);
        this.timeline_graph.destroy();
    },

    test_canvas_creation: function() {
        Assert.isInstanceOf(
            Y.registry.timeline.TimelineGraph,
            this.timeline_graph,
            "TimelineGraph was not created.");

        Assert.isNotNull(
            this.content_box.query('canvas'),
            "A canvas should have been created.");
    },

    test_zoom_buttons: function() {
        var zoom_in = this.content_box.query('a#in');
        Assert.isNotNull(
            zoom_in,
            'zoom_in link not found.');

        var zoom_out = this.content_box.query('a#out');
        Assert.isNotNull(
            zoom_in,
            'zoom_out link not found.');
    },

    test_series_label: function() {
        var label = this.content_box.query('div#trunk');
        Assert.isNotNull(
            label,
            "Series label not found.");
        Assert.areEqual(
            'Development Focus Series',
            label.get('title'),
            "Unexpected series label title.");

        var link = label.query('a');
        Assert.isNotNull(
            link,
            "Series label does not contain a link.");
        Assert.areEqual(
            '<b>trunk</b>',
            link.get('innerHTML'),
            "Unexpected series link text.");
        Assert.areEqual(
            'file:///firefox/trunk',
            link.get('href'),
            "Unexpected series link href.");
    },

}));

suite.add(new Y.Test.Case({

    name: 'medium-config',

    setUp: function() {
        this.timeline_graph = new Y.registry.timeline.TimelineGraph(
            MEDIUM_CONFIG);
        this.timeline_graph.render();
        this.content_box = this.timeline_graph.get('contentBox');
    },

    tearDown: function() {
        var bounding_box = this.timeline_graph.get('boundingBox')
        bounding_box.get('parentNode').removeChild(bounding_box);
        this.timeline_graph.destroy();
    },

    test_milestone_label: function() {
        var label = this.content_box.query('div#alpha');
        Assert.isNotNull(
            label,
            "Milestone label not found.");
        Assert.areEqual(
            'warthog',
            label.get('title'),
            "Unexpected milestone label title.");

        var link = label.query('a');
        Assert.isNotNull(
            link,
            "Milestone label does not contain a link.");

        Assert.areEqual(
            'alpha',
            link.get('innerHTML'),
            "Unexpected milestone link text.");
        Assert.areEqual(
            'file:///firefox/+milestone/alpha',
            link.get('href'),
            "Unexpected milestone link href.");

        var second_line = label.query('div');
        Assert.areEqual(
            '2056-10-16',
            second_line.get('innerHTML'),
            "Unexpected milestone date.");
    },
}));


Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
