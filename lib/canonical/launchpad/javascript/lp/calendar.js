YUI().use('node', function(Y) {

/*
 * Initialize any yui2 calendars found on the page, adding the
 * 'choose' link.
 */
Y.on("domready", function(){
    var date_inputs = Y.all('.yui2-date-calendar');

    date_inputs.each(function(date_input) {
        // Fore each date input, insert the Choose... link right after
        // the date input node.
        var parent_node = date_input.ancestor();
        var choose_link = Y.Node.create(
            '<span>(<a class="js-action" href="#">Choose...</a>)</span>');
        parent_node.insertBefore(choose_link, date_input.next());

        // Add a container div for the calendar right after the choose_link.
        var containing_div_id = "calendar_container-" + date_input.get('id');
        parent_node.insertBefore(
            Y.Node.create('<div id="' + containing_div_id +
                          '" style="position:absolute"></div>'),
            choose_link.next());

        // Create and render the calendar widget.
        var calendar_widget = new YAHOO.widget.Calendar(
            "calendar_widget", containing_div_id, {
                title:"Please make a selection:",
                close:true
                });
        calendar_widget.hide();
        calendar_widget.render();

        // Setup the on click event to display the calendar.
        Y.on("click", function(e) {
            calendar_widget.show();
        }, choose_link);

        // Handle the (YUI2) calendar select event by hiding the
        // calendar and updating the date input's value.
        calendar_widget.selectEvent.subscribe(function(type, args, obj) {
            calendar_widget.hide();
            var selected_dates = args[0];
            var selected_date = selected_dates[0];

            // Just pad small days/months with a zero.
            for (var index=0; index < selected_date.length; index++) {
                selected_date[index] = String(selected_date[index]);

                if (selected_date[index].length == 1) {
                    selected_date[index] = "0" + selected_date[index];
                }
            }

            date_input.set('value', selected_date.join("-"));
        }, calendar_widget, true);
    });
});

});

