/* Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * TimelineGraph widget.
 *
 * @module timeline
 */

YUI.add('registry.timeline', function(Y) {

var module = Y.namespace('registry.timeline');

// px spacing and sizes.
var margin = 30;
var x_spacing = 40;
var y_spacing = 80;
var label_spacing= 10;
var milestone_size = 8;
var release_size = 5;
// Defines angle of vertical timeline.
var angle_x_spacing = 0.3 * y_spacing;
// Font size in em's.
var font_size = 1;
// Colors.
var line_color = 'blue';
var milestone_color = 'darkgray';
var release_color = 'black';
// External ref counter, should probably use unique IDs from json
var counter = 0;
// Zoom level (increase/decrease 30%)
var zoom_jumps = 1.3;
// Zoom level for fonts (increas/decrease 10%)
var zoom_jumps_font = 1.1;

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
            context.fillStyle = milestone_color;
            center_pos = (milestone_size / 2);
            context.fillRect (
                x_pos - center_pos, y_pos - center_pos, milestone_size,
                milestone_size);
            this.make_label(x_pos, y_pos + label_spacing, label);
        } else if(type == 'release') {
            context.fillStyle = release_color;
            context.beginPath();
            context.arc(
                x_pos, y_pos, release_size, 0, (Math.PI*2), true);
            context.fill();
            this.make_label(x_pos, y_pos + label_spacing, label);
        } else if(type == 'horizon') {
            //TODO: What is the horizon?
            context.fillStyle = horizon_color;
            center_pos = (milestone_size / 2);
            context.fillRect(
                x_pos - center_pos, y_pos - center_pos, milestone_size,
                milestone_size);
        }
    },

    make_label: function(x_pos, y_pos, label) {
        var graph_scale = this.timeline_graph.graph_scale;
        var canvas = this.timeline_graph.canvas;
        x_pos *= graph_scale;
        y_pos *= graph_scale;
        // Find where the canvas es placed on the page
        offset_y = canvas.offsetTop;
        // Slight correction because of default browser settings. In reality
        // this needs to be centered.
        offset_x = canvas.offsetLeft - 6;

        // If the element already exists, we just want to move it
        if(document.getElementById('txt_'+counter) != null) {
            new_div = document.getElementById('txt_'+counter);
        } else {
            new_text = document.createTextNode(label);
            new_div = document.createElement('div');
            new_div.setAttribute('id', 'txt_'+counter);

            new_div.appendChild(new_text);
            document.getElementById('canvas-container').appendChild(new_div);
        }

        new_div.style.fontSize = (font_size * graph_scale) + 'em';
        new_div.style.position = 'absolute';
        new_div.style.top = (y_pos + offset_y) + "px";
        new_div.style.left = (x_pos + offset_x) + "px";

        counter = counter + 1;
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

module.TimelineGraph = function(timeline, canvas) {
    this.timeline = timeline;
    this.canvas = canvas;
    this.canvas_context = canvas.getContext('2d');
    this.graph_scale = 1;
    this.project_line = new ProjectLine(
        this, this.timeline);
}

module.TimelineGraph.prototype = {

    zoom: function(zoom) {
        if(zoom == 'in') {
            this.graph_scale *= zoom_jumps;
        } else if(zoom == 'out') {
            this.graph_scale /= zoom_jumps;
        }

        this.draw();
    },

    stretch_canvas: function() {
        var max_y = Math.max(
            this.project_line.start.y,
            this.project_line.stop.y);
        this.canvas.width = 
            (this.project_line.get_width() * this.graph_scale) + margin;
        this.canvas.height = (max_y * this.graph_scale) + margin;
    },

    draw: function() {
        // Resize canvas and zoom, if necessary.
        this.stretch_canvas();
        this.canvas_context.clearRect(
            0, 0, this.canvas.width, this.canvas.height);
        this.canvas_context.scale(this.graph_scale, this.graph_scale);
        counter = 0;

        this.canvas_context.strokeStyle = line_color;

        this.project_line.draw();
    }
};

}, '0.1', {requires: []});
