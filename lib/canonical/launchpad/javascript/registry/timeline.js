/* Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * TimelineGraph widget.
 *
 * @module timeline
 */

YUI.add('registry.timeline', function(Y) {

var module = Y.namespace('registry.timeline');

// px spacing and sizes.
var margin = 50;
var x_spacing = 50;
var y_spacing = 40;
var milestone_size = 8;
var release_size = 5;
// Defines angle of vertical timeline.
var angle_x_spacing = 0.3 * y_spacing;
// Font size in em's.
var font_size = 1;
// Guesstimates for sizing the canvas.
var font_px_height = 10;
var font_px_width = 10;
// Colors.
var line_color = 'blue';
var milestone_color = 'darkgray';
var release_color = 'black';
// External ref counter, should probably use unique IDs from json
var counter = 0;
// Zoom level (increase/decrease 30%)
var zoom_jumps = 1.3;

var draw_line = function(canvas_context, nodes) {
    canvas_context.beginPath();
    for(i in nodes) {
        if(i == 0) {
            // Starting the line.
            canvas_context.moveTo(nodes[i].x, nodes[i].y);
        } else {
            // Specify nodes.
            canvas_context.lineTo(nodes[i].x, nodes[i].y);
        }
    }
    // Draw!
    canvas_context.stroke();
}

Position = function(x, y) {
    this.x = x;
    this.y = y;
};

SeriesLine = function(timeline_graph, series, start) {
    this.timeline_graph = timeline_graph;
    this.series = series;
    this.start = start;
    this.stop = new Position(
        this.start.x + (series.landmarks.length * x_spacing),
        this.start.y);
}

SeriesLine.prototype = {

    make_landmark: function(x_pos, y_pos, type, label) {
        var context = this.timeline_graph.canvas_context;
        if(type == 'milestone') {
            var center_pos = (milestone_size / 2);
            context.fillStyle = milestone_color;
            context.fillRect (
                x_pos - center_pos, y_pos - center_pos, milestone_size,
                milestone_size);
            // We use the release_size for the milestone, so that the
            // text for milestones and releases are on the same line.
            this.make_label(x_pos, y_pos + release_size, label);
        } else if(type == 'release') {
            context.fillStyle = release_color;
            context.beginPath();
            context.arc(
                x_pos, y_pos, release_size, 0,
                (Math.PI*2), true);
            context.fill();
            this.make_label(x_pos, y_pos + release_size, label);
        }
    },

    make_label: function(x_pos, y_pos, label) {
        var graph_scale = this.timeline_graph.graph_scale;
        var dom_canvas = Y.Node.getDOMNode(this.timeline_graph.canvas);
        x_pos *= graph_scale;
        y_pos *= graph_scale;

        // If the element already exists, we just want to move it
        var id = this.timeline_graph.id + '-' + counter;
        var text_container = Y.Node.get('#' + id);
        if(text_container === null) {
            text_container = Y.Node.create(
                '<span id="' + id + '">' + label + '</span>');
            text_container.setStyle('position', 'absolute');
            this.timeline_graph.get('contentBox').appendChild(text_container);
        }

        text_container.setStyle('fontSize', (font_size * graph_scale) + 'em');
        // Find where the canvas es placed on the page, and lower the
        var offset_y = dom_canvas.offsetTop;
        // Center the text under the landmark.
        var offset_x =
            dom_canvas.offsetLeft - text_container.get('offsetWidth') / 2;
        text_container.setStyle('top', (y_pos + offset_y) + "px");
        text_container.setStyle('left', (x_pos + offset_x) + "px");

        counter += 1;
    },

    draw: function() {
        // Horizontal line.
        draw_line(
            this.timeline_graph.canvas_context, [this.start, this.stop]);

        for (var i in this.series.landmarks) {
            i = parseInt(i);
            var landmark = this.series.landmarks[i];
            var x_landmark = this.start.x + ((i + 1) * x_spacing);

            this.make_landmark(
                x_landmark, this.start.y,
                landmark.type, landmark.name);
        }
    }
};

ProjectLine = function(timeline_graph, timeline) {
    this.timeline_graph = timeline_graph;
    this.timeline = timeline;
    this.start = new Position(x_spacing, this.timeline.length * y_spacing);
    this.stop = new Position(
        this.start.x + (this.timeline.length * angle_x_spacing),
        0);

    this.series_lines = [];
    this.initSeries();
}

ProjectLine.prototype = {

    initSeries: function() {
        for(var i in this.timeline) {
            // Convert index to an actual integer so it can
            // used in calculations.
            i = parseInt(i);
            var series = this.timeline[i];

            var series_position = new Position(
                this.start.x + (i * angle_x_spacing),
                this.start.y - (i * y_spacing));

            var series_line = new SeriesLine(
                this.timeline_graph, series, series_position);
            this.series_lines.push(series_line);
        }
    },

    get_width: function() {
        var max_x = 0;
        for(var i in this.series_lines) {
            max_x = Math.max(max_x, this.series_lines[i].stop.x);
        }
        return max_x;
    },

    draw: function() {
        draw_line(
            this.timeline_graph.canvas_context, [this.start, this.stop]);
        for(var i in this.series_lines) {
            this.series_lines[i].draw();
        }
    }
};

/**
 * The TimlineGraph widget will display an HTML5 canvas of a
 * project's series, milestones, and releases.
 *
 * @class TimelineGraph
 * @constructor
 * @extends Widget
 */
module.TimelineGraph = function() {
    module.TimelineGraph.superclass.constructor.apply(this, arguments);
}

module.TimelineGraph.NAME = 'TimelineGraph';
module.TimelineGraph.ATTRS = {
    /**
     * JSON data describing the timeline of series, milestones, and releases.
     *
     * @attribute timeline
     * @type Array
     */
    timeline: { value: [] },
};

Y.extend(module.TimelineGraph, Y.Widget, {

    /**
     * Initialize the widget.
     *
     * @method initializer
     * @protected
     */
    initializer: function(cfg) {
        if(cfg === undefined || cfg.timeline === undefined) {
            throw new Error(
                "Missing timeline config argument for TimelineGraph.");
        }
        this.graph_scale = 1;
        this.project_line = new ProjectLine(this, this.get('timeline'));
    },

    zoom_in: function() {
        this.graph_scale *= zoom_jumps;
        this.syncUI();
    },

    zoom_out: function() {
        this.graph_scale /= zoom_jumps;
        this.syncUI();
    },

    create_canvas: function() {
        var max_y = Math.max(
            this.project_line.start.y,
            this.project_line.stop.y);
        var width =
            this.project_line.get_width() * this.graph_scale + margin;
        var height = 
            ((max_y + font_px_height) * this.graph_scale)
            + margin;
        return Y.Node.create(
            '<canvas width="' + width + '" height="' + height + '"/>');
    },

    renderUI: function() {
        this.zoom_in_button = Y.Node.create(
                '<a class="bg-image" href="javascript:void(0)" ' +
                '   style="background-image: url(/@@/zoom-in);' +
                '          position: absolute; height: 14px;' +
                '          top: 30px; left: 5px"/>');
        this.zoom_out_button = Y.Node.create(
                '<a class="bg-image" href="javascript:void(0)" ' +
                '   style="background-image: url(/@@/zoom-out);' +
                '          position: absolute; height: 14px;' +
                '          top: 30px; left: 20px"/>');
        var contentBox = this.get('contentBox');
        contentBox.appendChild(this.zoom_in_button);
        contentBox.appendChild(this.zoom_out_button);
    },

    bindUI: function() {
        this.zoom_in_button.on('click', function() {
            this.zoom_in();
        }, this);
        this.zoom_out_button.on('click', function() {
            this.zoom_out();
        }, this);
    },

    syncUI: function() {
        // Resizing the canvas requires destroying the old canvas and
        // creating a new one due to rendering issues in WebKit.
        var contentBox = this.get('contentBox');
        if (this.canvas) {
            contentBox.removeChild(this.canvas);
        }
        this.canvas = this.create_canvas();
        //contentBox.insertBefore(
         //   this.canvas, contentBox.get('children').item(0));
        contentBox.appendChild(this.canvas);
        var dom_canvas = Y.Node.getDOMNode(this.canvas);
        this.canvas_context = dom_canvas.getContext('2d');

        // Zoom in or out.
        this.canvas_context.scale(this.graph_scale, this.graph_scale);

        // Reset the counter for landmark label ids.
        counter = 0;

        this.canvas_context.strokeStyle = line_color;

        this.project_line.draw();
    }
});

}, '0.1', {requires: ['oop', 'node', 'widget']});
