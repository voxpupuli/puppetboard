(function () {
  var $;

  $ = jQuery;

  $('#switch_env').change(function() {
    path = location.pathname.split('/');
    path[1] = $(this).find(':selected').text();
    location.assign(path.join('/'))
  });
}).call(this)
