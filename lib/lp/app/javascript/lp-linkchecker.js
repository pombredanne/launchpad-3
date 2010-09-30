YUI().add('lp.app.linkchecker', function(Y) {

    var namespace = Y.namespace('lp.app.linkchecker');

    namespace.checklinks = function() {

        var qs = '';
        qs = LP.client.append_qs(qs, 'name', 'fred');
        qs = LP.client.append_qs(qs, 'search_text', 'test');
        qs = LP.client.append_qs(qs, 'start', start);


        CHECK_LINKS='+check-links?';
        Y.io(CHECK_LINKS+qs, {
            headers: {'Accept': 'application/json'},
            on: {
                success: function(id, response) {
                    alert("Success: " +  + id + ", " + response.responseText)
                },
                failure: function(id, response) {
                    alert('Error: ' + id + ", " + response.responseText);
                }
            }
        });
    }

}, "0.1", {"requires": ["base", "lp.client.plugins"]});

