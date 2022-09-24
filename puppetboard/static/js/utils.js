/**
 * Transform date string with tz to shorter string.
 * If localisation enabled in config,  date is timezoned with browser
 * If localisation disabled in config, date is UTC
 */
$.fn.transformDatetime = function (format = "MMM DD YYYY - HH:mm:ss") {
  this.each(function () {
    let $el = $(this)
    let localise = $el.data("localise")
    let dt = moment($el.text())

    if (!dt.isValid()) return

    if (localise) {
      $el.text(dt.format("MMM DD YYYY - HH:mm:ss"))
    } else {
      $el.text(dt.utc().format("MMM DD YYYY - HH:mm:ss"))
    }
  })
  return this
}

$(document).ready(function () {
  $("[data-localise]").transformDatetime()

  let dataTable = $("#main-table").DataTable()
  $("#main-table-search").on("input", function () {
    dataTable.search(this.value).draw()
  })
})
