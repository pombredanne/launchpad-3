YUI().use('node', function(Y) {

function pad_with_zero(num) {
    num_as_string = String(num);
    if (num_as_string.length == 1) {
        num_as_string = "0" + num_as_string;
    }
    return num_as_string
}

function get_initial_value_for_input(date_input) {
    var date_match = (/(\d{4})-(\d{1,2})-(\d{2})/g).exec(
        date_input.get('value'));
    var time_match = (/(\d{2}):(\d{2})/g).exec(date_input.get('value'));

    var initial_value = new Date();
    if (date_match !== null) {
        initial_value.setFullYear(date_match[1]);
        initial_value.setMonth(parseInt(date_match[2]) - 1);
        initial_value.setDate(date_match[3]);

        if (time_match) {
            initial_value.setHours(time_match[1]);
            initial_value.setMinutes(time_match[2]);
        }
    }
    return initial_value;
}

function create_time_selector_node(selected_time) {
    if (selected_time == null) {
        selected_time = new Date();
    }

    var inner_html = [
        '<div style="margin-top:1em;text-align:center">Time ',
        '  <input class="hours" maxlength="2" size="2"',
        '    value="' + pad_with_zero(selected_time.getHours()) +'"/>',
        '  : ',
        '  <input class="minutes" maxlength="2" size="2" ',
        '    value="' + pad_with_zero(selected_time.getMinutes()) + '"/>',
        '  <button class="lazr-pos lazr-btn" type="button">OK</button>',
        '  </a>',
        '</div>'].join("\n");

    return Y.Node.create(inner_html);
}

function create_calendar_widget_for_input(date_input_node,
                                          containing_div_node) {
    var initial_value = get_initial_value_for_input(date_input_node);

    var calendar_widget = new YAHOO.widget.Calendar(
        "calendar_widget", containing_div_node.get('id'), {
            title:"Select a date",
            close:true,
            pagedate: initial_value,
            selected: [
                initial_value.getMonth() + 1,
                initial_value.getDate(),
                initial_value.getFullYear()].join("/")
            });
    calendar_widget.render();

    // If this widget should also include entering time
    // then add it in.
    var is_datetime_widget = date_input_node.hasClass('withtime');
    var time_selector_node = null;
    if (is_datetime_widget) {
        time_selector_node = create_time_selector_node(initial_value);
        containing_div_node.appendChild(time_selector_node);

        // Ensure that when the ok button is click, the calendar's
        // selectEvent is fired and the calendar closed.
        var ok_button = time_selector_node.query('.lazr-btn');
        Y.on("click", function(e) {
            calendar_widget.selectEvent.fire();
            calendar_widget.hide();
        }, ok_button);
    }

    // Handle the (YUI2) calendar select differently for date widgets
    // and datetime widgets.
    calendar_widget.selectEvent.subscribe(function(type, args, obj) {
        // If this is not a datetime widget, we can close it when the
        // user makes a selection.
        if (!is_datetime_widget) {
            calendar_widget.hide();
        }

        var selected_dates = calendar_widget.getSelectedDates();
        var selected_date = selected_dates[0];

        var value_string = [
            selected_date.getFullYear(),
            pad_with_zero(selected_date.getMonth() + 1),
            pad_with_zero(selected_date.getDate())].join("-")

        if (is_datetime_widget) {
            hours = pad_with_zero(
                time_selector_node.query('.hours').get('value'));
            minutes = pad_with_zero(
                time_selector_node.query('.minutes').get('value'));
            value_string += " " + hours + ":" + minutes
        }

        date_input_node.set('value', value_string);
    }, calendar_widget, true);

    return calendar_widget;
}

/*
 * Initialize any yui2 calendars found on the page, adding the
 * 'choose' link.
 */
Y.on("domready", function() {
    var date_inputs = Y.all('.yui2-date-calendar');

    if (date_inputs === null) {
        return
    }

    date_inputs.each(function(date_input) {
        // Fore each date input, insert the Choose... link right after
        // the date input node.
        var parent_node = date_input.ancestor();
        var choose_link = Y.Node.create(
            '<span>(<a class="js-action" href="#">Choose...</a>)</span>');
        parent_node.insertBefore(choose_link, date_input.next());

        // Add a container div for the calendar right after the choose_link.
        var containing_div_id = "calendar_container-" + date_input.get('id');
        var containing_div_node = Y.Node.create(
            '<div id="' + containing_div_id +
            '" style="position:absolute"></div>')
        parent_node.insertBefore(containing_div_node, choose_link.next());

        // Setup the on click event to display the calendar.
        var calendar_widget = null;
        Y.on("click", function(e) {

            // Just prevent the default link behaviour to avoid scrolling
            // to the top of the page.
            e.preventDefault();

            // Create the calendar widget if this is the first time
            // the link has been clicked.
            if (calendar_widget === null) {
                calendar_widget = create_calendar_widget_for_input(
                    date_input, containing_div_node)
            }

            calendar_widget.show();
        }, choose_link);
    });
});

});

