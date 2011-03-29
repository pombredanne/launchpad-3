/* Log time taken for AJAX requests.
*/
function start_ajax_logging() {
    /* Maximum amount of time we want AJAX requests to take, in seconds.
    */
    var AJAX_MAX_TIME = 1;
    /* Can't use LPS here as it doesn't exist yet.
    */
    LPS.use('node', 'lazr.anim', function(Y) {
        Y.on('contentready', function() {
            var node = Y.one('#ajax-time-list');
            var ajax_request_times = {};
            var ajax_menu_animating = false;
            var flash_menu = Y.lazr.anim.green_flash({node:'#ajax-time'});
            flash_menu.on('end', function() {
                ajax_menu_animating = false;
            });
            /* When an AJAX event starts, record the time.
            */
            Y.on('io:start', function(transactionid) {
                var now = new Date();
                ajax_request_times[transactionid] = now;
            });
            /* When an AJAX event finishes add it to the log.
            */
            Y.on('io:complete', function(transactionid, arguments) {
                /* The AJAX event has finished so record the time.
                */
                var finish_time = new Date();
                var no_events = Y.one('#ajax-time-list .no-events');
                if (no_events) {
                    no_events.remove();
                }
                /* Get the OOPS id if it exists.
                */
                var oops_id = arguments.getResponseHeader('X-Lazr-OopsId');
                if (ajax_request_times[transactionid]) {
                    var start_time = ajax_request_times[transactionid];
                    var time_taken = (finish_time - start_time)/1000;
                    var log_node = Y.Node.create('<li>Time: </li>');
                    log_node.addClass('transaction-' + transactionid);
                    var time_node = Y.Node.create('<strong></strong>');
                    var time_text = time_taken.toFixed(2) + ' seconds';
                    time_node.append(time_text);
                    /* If the AJAX event takes longer than AJAX_MAX_TIME
                       then add a warning.
                    */
                    if (time_taken > AJAX_MAX_TIME) {
                        time_node.addClass('warning');
                    }
                    log_node.append(time_node);
                    log_node.append(Y.Node.create('<br />'));
                    var details_node = Y.Node.create('<span></span>');
                    var details_text = 'ID: '+transactionid+', status: ' +
                            arguments.status + ' ('+arguments.statusText+')';
                    details_node.append(details_text);
                    if (oops_id) {
                        var oops_node = Y.Node.create('<a href="http://pad.lv/'+
                                oops_id+'">'+oops_id+'</a>');
                        details_node.append(', OOPS ID:&nbsp;');
                        details_node.append(oops_node);
                    }
                    log_node.append(details_node);
                    node.prepend(log_node);
                    /* Highlight the new entry in the log.
                    */
                    Y.lazr.anim.green_flash({
                        node:'#ajax-time-list li.transaction-'+transactionid
                        }).run();
                    /* Signify a new entry has been added to the log.
                    */
                    if (ajax_menu_animating == false) {
                        flash_menu.run();
                        ajax_menu_animating = true;
                    }
                }
            });
            
            /* Open/close the log.
            */
            Y.on('click', function(e) {
                e.halt();
                Y.one('#ajax-time-list').toggleClass('hidden');
            }, '#ajax-time a');
        }, '#ajax-time');
    });
}
