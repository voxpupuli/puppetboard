jQuery(function ($) {
  var localise_timestamp = function(timestamp){
    if (timestamp === "None"){
      return '';
    };
    d = moment.utc(timestamp);
    d.local();
    return d;
  };

  $("[rel=utctimestamp]").each(
    function(index, timestamp){
      var tstamp = $(timestamp);
      var tstring = tstamp.text().trim();
      var result = localise_timestamp(tstring);
      if (result == '') {
        tstamp.text('Unknown');
      } else {
        tstamp.text(localise_timestamp(tstring).format('MMM DD YYYY - HH:mm:ss'));
      };
  });

});
