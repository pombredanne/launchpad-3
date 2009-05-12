// TODO:
// - Slanting


// Default configuration values
// Horizontal px spacing
var x_spacing = 40;
// Vertical px spacing
var y_spacing = 80;
// font size in em's
var font_size = 1;
// Color for lines
var lod_color = 'blue';
// Color for milestones
var milestone_color = 'darkgray';
// Color for releases
var release_color = 'black';
// Milestone px size
var milestone_size = 8;
// Release px size
var release_size = 5;
// External ref counter, should probably use unique IDs from json
var counter = 0;
// Zoom level (increase/decrease 30%)
var zoom_jumps = 1.3;
// Zoom level for fonts (increas/decrease 10%)
var zoom_jumps_font = 1.1;

function zoom_graph(zoom, canvas_context)
{
  if(zoom == 'in')
  {
    x_spacing = x_spacing*zoom_jumps;
    y_spacing = y_spacing*zoom_jumps;
    font_size = font_size*zoom_jumps_font;
    milestone_size = milestone_size*zoom_jumps;
    release_size = release_size*zoom_jumps;
  }
  else if(zoom == 'out')
  {
    x_spacing = x_spacing/zoom_jumps;
    y_spacing = y_spacing/zoom_jumps;
    font_size = font_size/zoom_jumps_font;
    milestone_size = milestone_size/zoom_jumps;
    release_size = release_size/zoom_jumps;
  }

  canvas_context.clearRect(0, 0, canvas.width, canvas.height);
  counter = 0;
  draw_graph(timeline, canvas);
}


function make_landmark(canvas_context, x_pos, y_pos, type, label)
{
    if(type == 'milestone') {
        canvas_context.fillStyle = milestone_color;
        center_pos = (milestone_size / 2);
        canvas_context.fillRect (
            x_pos - center_pos, y_pos - center_pos, milestone_size,
            milestone_size);
        make_label(x_pos, y_pos + milestone_size * 1.6, label);
    } else if(type == 'release') {
        canvas_context.fillStyle = release_color;
        canvas_context.beginPath();
        canvas_context.arc(x_pos, y_pos, release_size, 0, (Math.PI*2), true);
        canvas_context.fill();
        make_label(x_pos, y_pos + release_size * 1.6, label);
    } else if(type == 'horizon') {
        canvas_context.fillStyle = horizon_color;
        center_pos = (milestone_size / 2);
        canvas_context.fillRect(
            x_pos - center_pos, y_pos - center_pos, milestone_size,
            milestone_size);
    }
}

function make_label(x_pos, y_pos, label)
{
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
        document.getElementById('container').appendChild(new_div);
    }

    new_div.style.fontSize = font_size + 'em';
    new_div.style.position = 'absolute';
    new_div.style.top = y_pos + offset_y;
    new_div.style.left = x_pos + offset_x;

    counter = counter+1;
}

function draw_line(canvas_context, nodes) {
    // Initialize
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

function draw_graph(timeline, canvas) {

    // Vertical lines
    var series_count = timeline.lines_of_development.length;
    var angle_x_spacing = 0.6 * y_spacing;
    var x_left_px  = x_spacing;
    var x_right_px = x_left_px + (series_count * angle_x_spacing);

    var y_top_px = 0;
    var y_bottom_px = timeline.lines_of_development.length * y_spacing;

    canvas.width = x_right_px + 3 * x_spacing;
    canvas.height = y_bottom_px + y_spacing;
    // Evil global.
    canvas_context = canvas.getContext('2d');

    canvas_context.strokeStyle = lod_color;

    var nodes = [
        {x: x_left_px,  y: y_bottom_px},
        {x: x_right_px,  y: y_top_px}
        ];

    draw_line(canvas_context, nodes);

    for(var i in timeline.lines_of_development) {
        // Convert index to an actual integer so it can used in calculations.
        i = parseInt(i);
        var o = timeline.lines_of_development[i];

        // Horizontal lines
        var x_start_series = x_left_px + (i * angle_x_spacing);
        var x_end_series =
            x_start_series + (o.landmarks.length * x_spacing);

        var y_series = y_bottom_px - (i * y_spacing);

        nodes = [
            {x: x_start_series, y: y_series},
            {x: x_end_series, y: y_series}
            ];

        draw_line(canvas_context, nodes);

        for (var j in o.landmarks) {
            j = parseInt(j);
            var landmark = o.landmarks[j];
            var x_landmark = x_start_series + ((j + 1) * x_spacing);

            make_landmark(
                canvas_context, x_landmark, y_series,
                landmark.type, landmark.name);
        }
    }
}
