// Default configuration values
// Horizontal px spacing
var x_px = 40;
// Vertical px spacing
var y_px = 40;
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
    x_px = x_px*zoom_jumps;
    y_px = y_px*zoom_jumps;
    font_size = font_size*zoom_jumps_font;
    milestone_size = milestone_size*zoom_jumps;
    release_size = release_size*zoom_jumps;
  }
  else if(zoom == 'out')
  {
    x_px = x_px/zoom_jumps;
    y_px = y_px/zoom_jumps;
    font_size = font_size/zoom_jumps_font;
    milestone_size = milestone_size/zoom_jumps;
    release_size = release_size/zoom_jumps;
  }

  canvas_context.clearRect(0, 0, canvas.width, canvas.height);
  counter = 0;
  draw_graph(timeline, canvas_context);
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

function draw_graph(timeline, canvas_context) {

    canvas_context.strokeStyle = lod_color;

    for(i in timeline.lines_of_development) {
        o = timeline.lines_of_development[i];

        if(o.type == 'main') {
            // Vertical lines
            x_init_px  = o.start_x * x_px;
            x_start_px = (o.start_x * x_px) - x_px;

            y_end_px   = (o.length * y_px) + y_px;
            y_start_px = o.length * y_px;
            y_init_px  = (o.start_y * y_px) - y_px;

            nodes = [{x:x_init_px, y:y_init_px},
                    {x:x_init_px, y:y_start_px},
                    {x:x_start_px, y:y_end_px}];
        } else {
            // Horizontal lines
            x_init_px  = (o.start_x * x_px) - x_px;
            x_start_px = o.start_x * x_px;
            x_end_px   = (o.length * x_px) + x_start_px;

            y_start_px = o.start_y * y_px;
            y_init_px  = y_start_px - y_px;

            nodes = [{x:x_init_px, y:y_init_px},
                    {x:x_start_px, y:y_start_px},
                    {x:x_end_px, y:y_start_px}];
        }

        draw_line(canvas_context, nodes);

        for (i in o.landmarks) {
            p = o.landmarks[i];
            y_pos = y_px * o.start_y;
            x_pos = x_px * p.point_x;

            make_landmark(canvas_context, x_pos, y_pos, p.type, p.name);
        }
    }
}
