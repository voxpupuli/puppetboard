/**
 * Custom DataTables sort plugin for IPv4 address strings.
 * Converts each octet to a zero-padded value so "10.2.11.99" sorts
 * correctly relative to "10.2.9.1" (which string sort gets wrong).
 *
 *  @name Natural IP
 *  @summary Sort IPv4 addresses numerically by octet
 *
 *  @example
 *    $("#example").DataTable({
 *       columnDefs: [
 *         { "type": "natural-ip", "targets": 1 }
 *       ]
 *    });
 */

jQuery.extend(jQuery.fn.dataTableExt.oSort, {
    "natural-ip-pre": function (data) {
        // Strip HTML tags and whitespace
        data = String(data).replace(/<[^>]*>/g, '').trim();

        // Convert IPv4 "a.b.c.d" to a zero-padded sortable string "aaa.bbb.ccc.ddd"
        var match = data.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
        if (match) {
            return match.slice(1).map(function (n) {
                return ('000' + n).slice(-3);
            }).join('.');
        }

        // Non-IP values (empty, hostnames, etc.) sort to the end
        return 'zzz.zzz.zzz.zzz';
    },

    "natural-ip-asc": function (a, b) {
        return a < b ? -1 : a > b ? 1 : 0;
    },

    "natural-ip-desc": function (a, b) {
        return a < b ? 1 : a > b ? -1 : 0;
    }
});
