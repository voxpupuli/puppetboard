/**
* Created by Shodhan Save on Jan 23, 2018.
* Updated @ Jan 25, 2018
* Modified for the Puppetboard by Greg Dubicki.
*/

/**
* This plug-in allows sorting of human-readable time delta, viz.,
* "1 week", "2 weeks 3 days", "4 weeks 5 days 6 hours", "1:24 hours" etc.
*
* Currently this plugin supports time range from microseconds to decades.
*
* The plugin also takes care of singular and plural values like week(s)
*
*  @name Natural Time Delta
*  @summary Sort human-readable time delta
*
*  @example
*    $("#example").DataTable({
*       columnDefs: [
*         { "type": "natural-time-delta", "targets": 2 }
*       ]
*    });
*/

jQuery.extend(jQuery.fn.dataTableExt.oSort,{
    "natural-time-delta-pre" : function(data){
        // get the non-formatted value from title
        data = data.match(/title="(.*?)"/)[1].toLowerCase();

        var total_duration = 0;
        var pattern = /(\d+\s*decades?\s*)?(\d+\s*years?\s*)?(\d+\s*months?\s*)?(\d+\s*weeks?\s*)?(\d+\s*days?\s*)?(\d+:?\d*?\s*hours?\s*)?(\d+\s*minutes?\s*)?(\d+\s*seconds?\s*)?(\d+\s*milliseconds?\s*)?(\d+\s*microseconds?\s*)?/i
        var get_duration = function (el, unit_name, duration_in_seconds) {
            if (el === undefined) {
                return 0;
            }

            var split_by = unit_name[0]
            var no_of_units = el.split(split_by)[0].trim()

            if ((unit_name === "hour") && (no_of_units.split(':').length === 2)) {
                // this is hour with minutes looking like this: "1:26 hours"
                var hours = parseFloat(no_of_units.split(':')[0]);
                var minutes = parseFloat(no_of_units.split(':')[1]);
                return (hours * 60 * 60) + (minutes * 60);
            } else {
                return parseFloat(no_of_units) * duration_in_seconds;
            }
        };

        var matches = data.match(pattern);
        matches.reverse();

        var time_elements = [
            {"unit_name": "microsecond", "duration_in_seconds": 1 / 1000 / 1000},
            {"unit_name": "millisecond", "duration_in_seconds": 1 / 1000},
            {"unit_name": "second", "duration_in_seconds": 1},
            {"unit_name": "minute", "duration_in_seconds": 1 * 60},
            {"unit_name": "hour", "duration_in_seconds": 1 * 60 * 60},
            {"unit_name": "day", "duration_in_seconds": 1 * 60 * 60 * 24},
            {"unit_name": "week", "duration_in_seconds": 1 * 60 * 60 * 24 * 7},
            {"unit_name": "month", "duration_in_seconds": 1 * 60 * 60 * 24 * 7 * 30},
            {"unit_name": "year", "duration_in_seconds": 1 * 60 * 60 * 24 * 7 * 30 * 12},
            {"unit_name": "decade", "duration_in_seconds": 1 * 60 * 60 * 24 * 7 * 30 * 12 * 10},
        ];

        time_elements.forEach(function (el, i) {
            var duration = get_duration(matches[i], el["unit_name"], el["duration_in_seconds"]);
            total_duration += duration;
        });

        return total_duration || -1;
    },

    "natural-time-delta-asc" : function (a, b) {
        return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },

    "natural-time-delta-desc" : function (a, b) {
        return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    }
});
