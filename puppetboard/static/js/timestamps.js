$.fn.extend({
  localise_timestamp: function (){
    var tstring = $(this).text().trim();
    if (tstring === "None"){
      $(this).text('Unknown');
    } else {
      var result = moment(tstring).utc();
      result.local();
      $(this).text(result.format('MMM DD YYYY - HH:mm:ss'));
    }
  }
})

jQuery(function ($) {
  $("[rel=utctimestamp]").each(
    function(index, timestamp){
      $(this).localise_timestamp();
  });
});
