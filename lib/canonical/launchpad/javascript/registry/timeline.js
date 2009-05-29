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

module.TimelineGraph = function(timeline, canvas) {
    this.timeline = timeline;
    this.canvas = canvas;
    this.canvas_context = canvas.getContext('2d');
    this.graph_scale = 1;
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

    make_landmark: function(canvas_context, x_pos, y_pos, type, label) {
        if(type == 'milestone') {
            this.canvas_context.fillStyle = milestone_color;
            center_pos = (milestone_size / 2);
            this.canvas_context.fillRect (
                x_pos - center_pos, y_pos - center_pos, milestone_size,
                milestone_size);
            this.make_label(x_pos, y_pos + label_spacing, label);
        } else if(type == 'release') {
            this.canvas_context.fillStyle = release_color;
            this.canvas_context.beginPath();
            this.canvas_context.arc(
                x_pos, y_pos, release_size, 0, (Math.PI*2), true);
            this.canvas_context.fill();
            this.make_label(x_pos, y_pos + label_spacing, label);
        } else if(type == 'horizon') {
            this.canvas_context.fillStyle = horizon_color;
            center_pos = (milestone_size / 2);
            this.canvas_context.fillRect(
                x_pos - center_pos, y_pos - center_pos, milestone_size,
                milestone_size);
        }
    },

    make_label: function(x_pos, y_pos, label) {
        x_pos *= this.graph_scale;
        y_pos *= this.graph_scale;
        // Find where the canvas es placed on the page
        offset_y = this.canvas.offsetTop;
        // Slight correction because of default browser settings. In reality
        // this needs to be centered.
        offset_x = this.canvas.offsetLeft - 6;

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

        new_div.style.fontSize = (font_size * this.graph_scale) + 'em';
        new_div.style.position = 'absolute';
        new_div.style.top = (y_pos + offset_y) + "px";
        new_div.style.left = (x_pos + offset_x) + "px";

        counter = counter + 1;
    },

    draw_line: function(nodes) {
        this.canvas_context.beginPath();
        for(i in nodes) {
            if(i == 0) {
                // Starting the line.
                this.canvas_context.moveTo(nodes[i].x, nodes[i].y);
            } else {
                // Specify nodes.
                this.canvas_context.lineTo(nodes[i].x, nodes[i].y);
            }
        }
        // Draw!
        this.canvas_context.stroke();
    },

    stretch_canvas: function() {
        var points = this.get_vertical_line_points();
        var max_y = Math.max(points[0].y, points[1].y);
        this.canvas.width = 
            (this.get_content_width() * this.graph_scale) + margin;
        this.canvas.height = (max_y * this.graph_scale) + margin;
    },


    get_x_start_timeline: function() {
        return x_spacing;
    },

    get_y_start_timeline: function() {
        return this.timeline.length * y_spacing
    },

    get_vertical_line_points: function() {
        return [
            {
                x: this.get_x_start_timeline(),
                y: this.get_y_start_timeline()
            },
            {
                x: this.get_x_start_timeline()
                   + (this.timeline.length * angle_x_spacing),
                y: 0
            }
        ];
    },

    get_content_width: function() {
        var max_x = 0;
        for(var i in this.timeline) {
            i = parseInt(i);
            var series = this.timeline[i];
            max_x = Math.max(max_x, this.get_x_end_series(i, series));
        }
        return max_x;
    },
    
    get_x_start_series: function(index, series) {
        return this.get_x_start_timeline() + (index * angle_x_spacing);
    },

    get_x_end_series: function(index, series) {
        return this.get_x_start_series(index, series)
               + (series.landmarks.length * x_spacing);
    },

    draw: function() {
        // Resize canvas and zoom, if necessary.
        this.stretch_canvas();
        this.canvas_context.clearRect(
            0, 0, this.canvas.width, this.canvas.height);
        this.canvas_context.scale(this.graph_scale, this.graph_scale);
        counter = 0;

        this.canvas_context.strokeStyle = line_color;

        // Vertical line.
        this.draw_line(this.get_vertical_line_points());

        for(var i in this.timeline) {
            // Convert index to an actual integer so it can
            // used in calculations.
            i = parseInt(i);
            var series = this.timeline[i];

            // Horizontal lines

            var y_series = this.get_y_start_timeline() - (i * y_spacing);

            var x_start_series = this.get_x_start_series(i, series);
            nodes = [
                {x: x_start_series, y: y_series},
                {x: this.get_x_end_series(i, series), y: y_series}
                ];

            this.draw_line(nodes);

            for (var j in series.landmarks) {
                j = parseInt(j);
                var landmark = series.landmarks[j];
                var x_landmark = x_start_series + ((j + 1) * x_spacing);

                this.make_landmark(
                    this.canvas_context, x_landmark, y_series,
                    landmark.type, landmark.name);
            }
        }
    }
};
}, '0.1', {requires: []});
