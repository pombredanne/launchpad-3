/* Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * TimelineGraph widget.
 *
 * @module timeline
 */

YUI.add('registry.timeline', function(Y) {

var module = Y.namespace('registry.timeline');

second_mouse_button = 2;

// px spacing and sizes.
var margin = 80;
var y_spacing = 60;
var legend_indent= 90;
var legend_spacing = 20;
var legend_box_padding = 7;
var milestone_size = 8;
var release_size = 5;
// Defines angle of vertical timeline.
var angle_x_spacing = 0.3 * y_spacing;
// Font size in em's.
var font_size = 1;
// Colors.
var line_color = 'darkgreen';
var milestone_color = 'darkgray';
var release_color = 'black';
var anchor_fill_color = 'white';
var legend_box_color = 'black';
// Zoom level (increase/decrease 10%)
var zoom_jumps = 1.1;

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

Position.prototype = {
    copy: function() {
        return new Position(this.x, this.y);
    }
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
    this.series_label = this.timeline_graph.make_label(
        series.name, 'Series', this.series.uri);
    this.labels = {}
    for (var i in this.series.landmarks) {
        i = parseInt(i);
        var landmark = this.series.landmarks[i];
        this.labels[landmark.name] = this.timeline_graph.make_label(
            landmark.name, landmark.code_name, landmark.uri, landmark.date);
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
     * The main method which is called by the ProjectLine.draw()
     * method for each series in the project.
     *
     * @method draw
     */
    draw: function() {
        // Horizontal line.
        var context = this.timeline_graph.canvas_context;
        var stop = new Position(
            this.start.x + this.get_length(),
            this.start.y);

        if (this.series.is_development_focus === true) {
            // Draw a thick line as a rectangle.
            var thickness = 2;
            var offset = -1;
            context.fillStyle = line_color;
            context.fillRect(
                this.start.x,
                this.start.y + offset,
                stop.x - this.start.x,
                stop.y - this.start.y + thickness);
        }
        else {
            // We can't draw a 1 pixel wide rectangle reliably, so
            // we have to use the line drawing method.
            draw_line(context, [this.start, stop]);
        }

        // Starting point.
        this.timeline_graph.make_landmark(this.start, 'start');


        // Series label.
        var label_position = new Position(
            this.start.x + (this.get_length() / 2),
            this.start.y - release_size);
        this.timeline_graph.place_label(
            label_position, this.series_label, 'center', 'above');

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

            this.timeline_graph.make_landmark(
                landmark_position, landmark.type);
            // We use the release_size to space both the milestone and the
            // release labels, so that the labels line up.
            var label_position = new Position(
                landmark_position.x, landmark_position.y + release_size);
            this.timeline_graph.place_label(
                label_position, this.labels[landmark.name], 'center', 'below');
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

    var width = (this.timeline.length - 1) * angle_x_spacing;
    this.start = new Position(margin, this.timeline.length * y_spacing);
    this.stop = new Position(
        this.start.x + width,
        y_spacing);

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
                // Even a project with zero landmarks needs to have
                // its one empty series displayed.
                var text_beyond_last_landmark = 0;
            } else {
                var landmark = landmarks[landmarks.length-1];
                var label = this.series_lines[i].labels[landmark.name];
                var text_beyond_last_landmark = label.get('offsetWidth') / 2;
            }
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
     * @method get_height
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
            return this.start.y;
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
        var context = this.timeline_graph.canvas_context;
        draw_line(context, [this.start, this.stop]);
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
        var width = this.graph_scale * Math.max(
            this.project_line.get_width() + margin,
            this.get_legend_width());
        var height = this.graph_scale
                     * (this.project_line.get_height() + margin);
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
            var series_line = this.project_line.series_lines[i];
            max_label_width = Math.max(
                max_label_width, series_line.series_label.get('offsetWidth'));
            for (var j in series_line.labels) {
                var label = series_line.labels[j];
                // We have to set the font size here so that
                // offsetWidth will be correct.
                this.set_font_size(label);
                max_label_width = Math.max(
                    max_label_width, label.get('offsetWidth'));
            }
        }
        this.landmark_spacing = max_label_width + 5;
    },

    /**
     * Set the font size.
     *
     * @method set_font_size
     */
    set_font_size: function(label) {
        label.setStyle(
            'fontSize',
            (font_size * this.graph_scale) + 'em');
    },

    /**
     * This should show the most recent milestones or releases
     * on the development focus series.
     *
     * @method scroll_to_last_development_focus_landmark
     */
    scroll_to_last_development_focus_landmark: function(label) {
        var series_lines = this.project_line.series_lines;
        var series_line = series_lines[series_lines.length-1];
        var landmark = series_line.series.landmarks[0];
        if (landmark) {
            var label = series_line.labels[landmark.name];
            var scroll_x = label.get('offsetLeft') + label.get('offsetWidth')
                          - window.getViewportDimensions().w;
            // scrollBy is relative, so adjust it by
            // the current scroll position.
            scroll_x -= window.scrollX;
            window.scrollBy(scroll_x, 0);
        }
    },

    /**
     * Draw items that do not get recreated for each zoom level.
     *
     * @method renderUI
     */
    renderUI: function() {
        this.zoom_in_button = Y.Node.create(
            '<a id="in" class="bg-image"  ' +
            '   style="background-image: url(/@@/zoom-in);' +
            '          height: 14px"></a>');
        this.zoom_out_button = Y.Node.create(
            '<a id="out" class="bg-image" ' +
            '   style="background-image: url(/@@/zoom-out);' +
            '          height: 14px"></a>');
        var zoom_box = Y.Node.create(
            '<div id="box" style="border: 1px solid black; ' +
            'background-color: white; position: fixed; ' +
            'top: 0px; left: 0px; padding-left: 2px; ' +
            'cursor: pointer; z-index: 100"/>');
        zoom_box.appendChild(this.zoom_in_button);
        zoom_box.appendChild(this.zoom_out_button);
        var contentBox = this.get('contentBox');
        contentBox.appendChild(zoom_box);
        this.project_line = new ProjectLine(this, this.get('timeline'));
        this.make_legend_labels();
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
        contentBox.insertBefore(
            this.canvas, contentBox.get('children').item(0));
        var dom_canvas = Y.Node.getDOMNode(this.canvas);
        this.canvas_context = dom_canvas.getContext('2d');

        // Zoom in or out.
        this.canvas_context.scale(this.graph_scale, this.graph_scale);

        this.canvas_context.strokeStyle = line_color;

        this.project_line.draw();

        this.draw_legend();
    },

    /**
     * Make the labels to be placed in the legend.
     *
     * @method make_legend_labels
     */
    make_legend_labels: function() {
        this.milestone_legend = this.make_label('Milestone:');
        this.release_legend = this.make_label('Release:');
        this.start_legend = this.make_label('Starting Point:');
    },

    /**
     * Precalculate the legend width for resizing the canvas.
     *
     * @method get_legend_width
     */
    get_legend_width: function() {
        this.set_font_size(this.milestone_legend);
        this.set_font_size(this.release_legend);
        this.set_font_size(this.start_legend);

        var text_width = (
            this.milestone_legend.get('offsetWidth')
            + this.release_legend.get('offsetWidth')
            + this.start_legend.get('offsetWidth')) / this.graph_scale;
        return 2 * legend_spacing + 6 * release_size
               + legend_indent / this.graph_scale
               + 2 * legend_box_padding + text_width;
    },

    /**
     * Draw the legend box and landmark symbols, and place the
     * legend labels.
     *
     * @method draw_legend
     */
    draw_legend: function() {
        var line_height =
            this.milestone_legend.get('offsetHeight') / this.graph_scale;
        var fixed_indent = legend_indent / this.graph_scale;
        var legend_position = new Position(
            fixed_indent,
            line_height + 5);
        var rectangle_start = legend_position.copy();
        var landmark_position = new Position(
            release_size + legend_position.x +
            this.milestone_legend.get('offsetWidth') / this.graph_scale,
            legend_position.y - line_height / 2);

        // Milestone.
        this.place_label(
            legend_position, this.milestone_legend, 'right', 'above');
        this.make_landmark(landmark_position, 'milestone');

        // Release.
        legend_position.x =
            legend_spacing + release_size + landmark_position.x;
        this.place_label(
            legend_position, this.release_legend, 'right', 'above');
        landmark_position.x =
            1.5 * release_size + legend_position.x
            + this.release_legend.get('offsetWidth') / this.graph_scale;
        this.make_landmark(landmark_position, 'release');

        // Starting point.
        legend_position.x =
            legend_spacing + release_size + landmark_position.x;
        this.place_label(
            legend_position, this.start_legend, 'right', 'above');
        landmark_position.x =
            1.5 * release_size + legend_position.x
            + this.start_legend.get('offsetWidth') / this.graph_scale;
        this.make_landmark(landmark_position, 'start');

        // Legend box.
        rectangle_start.x -= legend_box_padding;
        rectangle_start.y += 2;
        var rectangle_stop = new Position(
            landmark_position.x + release_size + legend_box_padding,
            rectangle_start.y + line_height + 4);
        this.canvas_context.strokeStyle = legend_box_color;
        this.canvas_context.strokeRect(
            rectangle_start.x,
            rectangle_start.y,
            rectangle_stop.x - rectangle_start.x,
            rectangle_start.y - rectangle_stop.y);
        // Double line.
        this.canvas_context.strokeRect(
            rectangle_start.x - 1,
            rectangle_start.y - 1,
            rectangle_stop.x - rectangle_start.x + 2,
            rectangle_start.y - rectangle_stop.y + 2);
    },

    /**
     * Create the label for each landmark, but don't place them yet,
     * since we need to calculate the spacing between landmarks based
     * on the width of the longest label text.
     *
     * @method make_label
     */
    make_label: function(text, tooltip, uri, second_line) {
        var label = Y.Node.create(
            '<div style="text-align: center"/>');
        if (uri) {
            var link = Y.Node.create('<a>' + text + '</a>');
            link.on('click', function(e) {
                // Safari also fires the click event for the 2nd mouse button,
                // and we don't want to prevent that default action.
                if (e.which != second_mouse_button) {
                    parent.location.href = uri;
                    e.preventDefault();
                }
            });
            // Middle-clicking to open a new tab still works if
            // the href is set.
            link.set('href', uri);
            label.appendChild(link);
        } else {
            label.appendChild(
                Y.Node.create('<span>' + text + '</span>'));
        }
        label.setStyle('position', 'absolute');
        if (tooltip) {
            label.set('title', tooltip);
        } else {
            label.set('title', 'No code name');
        }
        if (second_line) {
            label.appendChild(
                Y.Node.create(
                    '<div style="color: #aaaaaa; font-size: 70%">' +
                    second_line + '</div>'));
        }
        this.get('contentBox').appendChild(label);
        return label;
    },

    /**
     * After this.landmark_spacing has been calculated,
     * we can place the label.
     *
     * @method place_label
     */
    place_label: function(position, label, x_align, y_align) {
        var graph_scale = this.graph_scale;
        var dom_canvas = Y.Node.getDOMNode(this.canvas);

        // Set the size here also, for any labels that are not
        // for landmarks, which are already set through
        // calculate_landmark_spacing.
        this.set_font_size(label);

        // Find where the canvas is placed on the page, and
        // center the text under the landmark.
        var label_height = label.get('offsetHeight');
        var y_align_offset;
        if (y_align == 'above') {
            y_align_offset = -label_height;
        } else if (y_align == 'below') {
            y_align_offset = 0;
        } else {
            throw "Invalid y_align argument: " + y_align;
        }

        var x_align_offset;
        if (x_align == 'left') {
            x_align_offset = -label.get('offsetWidth');
        } else if (x_align == 'center') {
            x_align_offset = -(label.get('offsetWidth') / 2);
        } else if (x_align == 'right') {
            x_align_offset = 0;
        } else {
            throw "Invalid x_align argument: " + x_align;
        }

        var scaled_position = new Position(
            position.x * graph_scale
            + dom_canvas.offsetLeft + x_align_offset,
            position.y * graph_scale
            + dom_canvas.offsetTop + y_align_offset);

        label.setStyle('left', scaled_position.x + "px");
        label.setStyle('top', scaled_position.y + "px");
    },

    /**
     * Draw a square for milestones and a circle for releases
     * on the series line. Also, place the name label
     * underneath the landmark.
     *
     * @method make_landmark
     */
    make_landmark: function(position, type) {
        var context = this.canvas_context;
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
        } else if (type == 'start') {
            context.fillStyle = anchor_fill_color;
            context.beginPath();
            context.arc(
                position.x, position.y, release_size, 0,
                (Math.PI*2), true);
            context.fill();
            context.stroke();
        }
        else {
            throw "Unknown landmark type: " + type;
        }
    },

});

}, '0.1', {requires: ['oop', 'node', 'widget']});
