{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for catalog in catalogs -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {%- for column in columns -%}
          {%- if not loop.first %},{%- endif -%}
          {%- if column.attr == 'catalog_timestamp' -%}
            "<a rel=\"utctimestamp\" href=\"{{url_for('catalog_node', env=current_env, node_name=catalog.certname)}}\">{{ catalog.catalog_timestamp }}</a>"
          {%- elif column.type == 'node' -%}
            {% filter jsonprint %}<a href="{{url_for('node', env=current_env, node_name=catalog.certname)}}">{{ catalog.certname }}</a>{% endfilter %}
          {%- elif column.attr == 'form' -%}
            {% filter jsonprint -%}
              <div class="ui action input">
                {%- if catalog.form -%}
                <form method="GET" action="{{url_for('catalog_compare', env=current_env, compare=catalog.form, against=catalog.certname)}}">
                {%- else -%}
                <form method="GET" action="{{url_for('catalogs', env=current_env, compare=catalog.certname)}}">
                {%- endif -%}
                  <div class="field inline">
                    {%- if catalog.form -%}
                      <input type="submit" class="ui submit button" style="height:auto;" value="Compare with {{ catalog.form }}"/>
                    {%- else -%}
                      <input type="submit" class="ui submit button" style="height:auto;" value="Compare with ..."/>
                    {%- endif -%}
                  </div>
                </form>
              </div>
            {%- endfilter -%}
          {%- else -%}
            ""
          {%- endif -%}
        {%- endfor -%}
      ]
    {% endfor %}
  ]
}
