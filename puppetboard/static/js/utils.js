/**
 * Simple debounce function
 */
debounce = function(cb, delay = 250) {
  let timeout

  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      cb(...args)
    }, delay)
  }
}

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


/**
 * Enable filtering on fact list
 *
 * If text is entered as input, it will use that text to create a regexp
 * that will match each fact name.
 * If a match is found, make sure the fact name is visible.
 * If no match is found, make sure the fact name is hidden.
 * Then, we display all segments and hide all those that do not have
 * at least a visible fact name.
 */
$.fn.factList = function () {
  this.each(function() {
    const $el = $(this)
    const $input = $el.find("input[name=filter]")
    const $segments = $el.find(".segment")
    const $facts = $el.find(".segment li")

    $input.on("input", debounce(function (e) {
      const text = $input.val()

      if (!text) {
        $segments.show()
        $facts.show()
        return
      }

      const pattern = new RegExp(text, "i")

      $facts.each(function () {
        const $fact = $(this)

        if (pattern.test($fact.text())) {
          $fact.show()
        } else {
          $fact.hide()
        }
      })
      $segments.show()
      $segments.not(':has(li:visible)').hide()
    }, 250))
  })

  return this
}

$(document).ready(function () {
  $("[data-localise]").transformDatetime()

  let dataTable = $("#main-table").DataTable()
  $("#main-table-search").on("input", function () {
    dataTable.search(this.value).draw()
  })

  $('#fact-list').factList()
})
