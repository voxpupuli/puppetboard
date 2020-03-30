jQuery(function ($) {
  function generateChart(el) {
    var url = "daily_reports_chart.json";
    var certname = $(el).attr('data-certname');
    if (typeof certname !== typeof undefined && certname !== false) {
      // truncate /node/certname from URL, to determine path to json
      url = window.location.href.replace(/\/node\/[^/]+$/,'') + "/daily_reports_chart.json?certname=" + certname;
    }
    d3.json(url, function(data) {
      var chart = c3.generate({
        bindto: '#dailyReportsChart',
        data: {
          type: 'bar',
          json: data['result'],
          keys: {
            x: 'day',
            value: ['failed', 'changed', 'unchanged'],
          },
          groups: [
            ['failed', 'changed', 'unchanged']
          ],
          colors: {  // Must match CSS colors
            'failed':'#AA4643',
            'changed':'#4572A7',
            'unchanged':'#89A54E',
          }
        },
        size: {
          height: 160
        },
        axis: {
          x: {
            type: 'category'
          }
        }
      });
    });
  }
  generateChart($("#dailyReportsChart"));
});
