/* Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * TimelineGraph widget.
 *
 * @module timeline
 */

YUI.add('registry.timeline', function(Y) {

var module = Y.namespace('registry.timeline');

// px spacing and sizes.
var margin = 20;
var y_spacing = 50;
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
var line_color = 'darkgreen';
var development_focus_color = 'red';
var milestone_color = 'darkgray';
var release_color = 'black';
// Zoom level (increase/decrease 30%)
var zoom_jumps = 1.3;

/**
 * Draw lines between a list of points.
 *
 * @method draw_line
 * @protected
 */
var draw_line = function(canvas_context, points) {
    canvas_context.beginPath();
    for (i in points) {
        if (i == 0) {
            // Starting the line.
            canvas_context.moveTo(points[i].x, points[i].y);
        } else {
            // Specify points.
            canvas_context.lineTo(points[i].x, points[i].y);
        }
    }
    // Draw!
    canvas_context.stroke();
}

/**
 * A single x and y coordinate.
 *
 * @class Position
 * @constructor
 */
Position = function(x, y) {
    this.x = x;
    this.y = y;
};

/**
 * These objects draw a horizontal line for the series
 * and place the text for each milestone and release on
 * the line.
 *
 * @class SeriesLine
 * @constructor
 */
SeriesLine = function(timeline_graph, series, start) {
    this.timeline_graph = timeline_graph;
    this.series = series;
    this.start = start;
    this.series_label = this.make_label(
        series.name, 'Series', this.series.uri);
    this.labels = {}
    for (var i in this.series.landmarks) {
        i = parseInt(i);
        var landmark = this.series.landmarks[i];
        this.labels[landmark.name] = this.make_label(
            landmark.name, landmark.code_name, landmark.uri);
    }
}

SeriesLine.prototype = {

    /**
     * Calculate the length of the horizontal line.
     *
     * @method get_length
     */
    get_length: function() {
        // Display a line stub for series without any landmarks.
        if (this.series.landmarks.length == 0) {
            return this.timeline_graph.landmark_spacing;
        } else {
            return this.series.landmarks.length
                * this.timeline_graph.landmark_spacing;
        }
    },

    /**
     * Draw a square for milestones and a circle for releases
     * on the series line. Also, place the name label
     * underneath the landmark.
     *
     * @method make_landmark
     */
    make_landmark: function(position, label, type) {
        var context = this.timeline_graph.canvas_context;
        // We use the release_size to space both the milestone and the
        // release labels, so that the labels line up.
        var label_position = new Position(
            position.x, position.y + release_size);
        this.place_label(label_position, label);
        if (type == 'milestone') {
            var width = milestone_size;
            var height = width;
            context.fillStyle = milestone_color;
            context.fillRect(
                position.x - width / 2,
                position.y - height / 2,
                width,
                height);
        } else if (type == 'release') {
            context.fillStyle = release_color;
            context.beginPath();
            context.arc(
                position.x, position.y, release_size, 0,
                (Math.PI*2), true);
            context.fill();
        }
    },

    /**
     * Create the label for each landmark, but don't place them yet,
     * since we need to calculate the spacing between landmarks based
     * on the width of the longest label text.
     *
     * @method make_label
     */
    make_label: function(text, tooltip, uri) {
        var id = Y.guid('timeline-label');
        label = Y.Node.create(
            '<a id="' + id + '" href="' + uri + '">' + text + '</a>');
        label.setStyle('position', 'absolute');
        if (tooltip) {
            label.set('title', tooltip);
        } else {
            label.set('title', 'No code name');
        }
        // Set the font size here so that we can calculate the
        // needed spacing between landmarks.
        label.setStyle(
            'fontSize',
            (font_size * this.timeline_graph.graph_scale) + 'em');
        this.timeline_graph.get('contentBox').appendChild(label);
        return label;
    },

    /**
     * After the timeline_graph.landmark_spacing has been calculated,
     * we can place the label.
     *
     * @method place_label
     */
    place_label: function(position, label) {
        var graph_scale = this.timeline_graph.graph_scale;
        var dom_canvas = Y.Node.getDOMNode(this.timeline_graph.canvas);

        label.setStyle('fontSize', (font_size * graph_scale) + 'em');
        // Find where the canvas is placed on the page, and
        // center the text under the landmark.
        var center_offset = label.get('offsetWidth') / 2;
        var scaled_position = new Position(
            position.x * graph_scale + dom_canvas.offsetLeft - center_offset,
            position.y * graph_scale + dom_canvas.offsetTop);
        label.setStyle('left', scaled_position.x + "px");
        label.setStyle('top', scaled_position.y + "px");
    },

    /**
     * The main method which is called by the ProjectLine.draw()
     * method for each series in the project.
     *
     * @method draw
     */
    draw: function() {
        // Horizontal line.
        var stop = new Position(
            this.start.x + this.get_length(),
            this.start.y);

        var context = this.timeline_graph.canvas_context;
        if (this.series.is_development_focus === true) {
            context.strokeStyle = development_focus_color;
        }
        draw_line(
            this.timeline_graph.canvas_context, [this.start, stop]);
        context.strokeStyle = line_color;

        // Series label.
        var label_height = this.series_label.get('offsetHeight');
        var label_position = new Position(
            this.start.x + (this.get_length() / 2),
            this.start.y - release_size - label_height);
        this.place_label(label_position, this.series_label);

        // Landmark labels.
        for (var i in this.series.landmarks) {
            i = parseInt(i);
            var landmark = this.series.landmarks[i];
            // The newest milestones are at the beginning, and
            // they need to be placed at the end of the horizontal
            // line.
            var position_index = this.series.landmarks.length - i;
            var landmark_position = new Position(
                this.start.x
                + (position_index * this.timeline_graph.landmark_spacing),
                this.start.y);

            this.make_landmark(
                landmark_position, this.labels[landmark.name], landmark.type);
        }
    }
};

/**
 * Class which draws the slanted vertical line representing
 * the project timeline and which instantiates the SeriesLine
 * objects which draw the horizontal lines.
 *
 * @class ProjectLine
 * @constructor
 */
ProjectLine = function(timeline_graph, timeline) {
    this.timeline_graph = timeline_graph;
    this.timeline = timeline;

    var width = this.timeline.length * angle_x_spacing;
    this.start = new Position(margin, this.timeline.length * y_spacing);
    this.stop = new Position(
        this.start.x + width,
        0);

    this.series_lines = [];
    this.initSeries();
}

ProjectLine.prototype = {

    /**
     * Instantiate each SeriesLine object and place it at the
     * correct point on the slanted vertical line. The series aren't
     * actuall drawn yet, since we need to loop through these objects
     * to calculate the landmark_spacing.
     *
     * @method initSeries
     */
    initSeries: function() {
        for (var i in this.timeline) {
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

    /**
     * Calculate the width based on the number of landmarks
     * and half the length of the label for the last landmark
     * on the right.
     *
     * @method get_width
     */
    get_width: function() {
        var max_x = 0;
        for (var i in this.series_lines) {
            var landmarks = this.series_lines[i].series.landmarks;
            if (landmarks.length == 0) {
                continue;
            }
            var landmark = landmarks[landmarks.length-1];
            var label = this.series_lines[i].labels[landmark.name];
            var text_beyond_last_landmark = label.get('offsetWidth') / 2;
            var series_width =
                this.series_lines[i].start.x
                + this.series_lines[i].get_length()
                + text_beyond_last_landmark;
            max_x = Math.max(max_x, series_width);
        }
        return max_x;
    },

    /**
     * Calculate the height based on the start.y value, which
     * is based on the number of series. It also adds the
     * distance for the labels below the bottom series line.
     *
     * @method get_width
     */
    get_height: function() {
        // Grab any landmark label to get its height.
        var label;
        for (var i in this.series_lines) {
            for (var key in this.series_lines[i].labels) {
                label = this.series_lines[i].labels[key];
                break;
            }
            if (label !== undefined) {
                break;
            }
        }
        if (label === undefined) {
            return 0;
        } else {
            return this.start.y + label.get('offsetHeight') + release_size;
        }
    },

    /**
     * Draw the project line and have each SeriesLine object draw itself.
     *
     * @method draw
     */
    draw: function() {
        draw_line(
            this.timeline_graph.canvas_context, [this.start, this.stop]);
        for (var i in this.series_lines) {
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
        if (cfg === undefined || cfg.timeline === undefined) {
            throw new Error(
                "Missing timeline config argument for TimelineGraph.");
        }
        this.graph_scale = 1;
    },

    /**
     * Increase the graph scale and redraw.
     *
     * @method zoom_in
     */
    zoom_in: function() {
        this.graph_scale *= zoom_jumps;
        this.syncUI();
    },

    /**
     * Decrease the graph scale and redraw.
     *
     * @method zoom_out
     */
    zoom_out: function() {
        this.graph_scale /= zoom_jumps;
        this.syncUI();
    },

    /**
     * The canvas has to be recreated each time with the new size, since
     * WebKit browsers do not handle resizing the canvas well.
     *
     * @method create_canvas
     */
    create_canvas: function() {
        var width =
            this.project_line.get_width() * this.graph_scale + margin;
        var height =
            this.project_line.get_height() * this.graph_scale + margin;
        return Y.Node.create(
            '<canvas width="' + width + '" height="' + height + '"/>');
    },

    /**
     * Set the timeline_graph.landmark_spacing attribute, which is
     * used by the SeriesLine objects and is based on the width
     * of the longest landmark label.
     *
     * @method calculate_landmark_spacing
     */
    calculate_landmark_spacing: function() {
        var max_label_width = 0;
        for (var i in this.project_line.series_lines) {
            var labels = this.project_line.series_lines[i].labels;
            for (var j in labels) {
                label = labels[j];
                max_label_width = Math.max(
                    max_label_width, label.get('offsetWidth'));
            }
        }
        this.landmark_spacing = max_label_width + 5;
    },

    /**
     * Draw items that do not get recreated for each zoom level.
     *
     * @method renderUI
     */
    renderUI: function() {
        this.zoom_in_button = Y.Node.create(
                '<a class="bg-image" href="javascript:void(0)" ' +
                '   style="background-image: url(/@@/zoom-in);' +
                '          position: absolute; height: 14px;' +
                '          top: 0px; left: 5px"/>');
        this.zoom_out_button = Y.Node.create(
                '<a class="bg-image" href="javascript:void(0)" ' +
                '   style="background-image: url(/@@/zoom-out);' +
                '          position: absolute; height: 14px;' +
                '          top: 0px; left: 20px"/>');
        var contentBox = this.get('contentBox');
        contentBox.appendChild(this.zoom_in_button);
        contentBox.appendChild(this.zoom_out_button);
        this.project_line = new ProjectLine(this, this.get('timeline'));
    },

    /**
     * Hook up UI events.
     *
     * @method bindUI
     */
    bindUI: function() {
        this.zoom_in_button.on('click', function() {
            this.zoom_in();
        }, this);
        this.zoom_out_button.on('click', function() {
            this.zoom_out();
        }, this);
    },

    /**
     * Redraw everything that changes at each zoom level.
     *
     * @method syncUI
     */
    syncUI: function() {
        // Resizing the canvas requires destroying the old canvas and
        // creating a new one due to rendering issues in WebKit.
        this.calculate_landmark_spacing();
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

        this.canvas_context.strokeStyle = line_color;

        this.project_line.draw();
    }
});

}, '0.1', {requires: ['oop', 'node', 'widget']});
