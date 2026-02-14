# Query Presets Feature

## Overview

The Query Presets feature allows users to save and quickly load frequently-used PuppetDB queries through a YAML configuration file. This eliminates the need to repeatedly type common queries and provides a library of useful query examples for users.

## Configuration

### 1. Enable Query Presets

In your Puppetboard configuration file (e.g., `local_settings.py` or `docker_settings.py`), set the path to your presets file:

```python
QUERY_PRESETS_FILE = '/etc/puppetboard/query_presets.yaml'
```

Set to `None` to disable presets:

```python
QUERY_PRESETS_FILE = None  # Presets disabled
```

### 2. Create a Presets File

Create a YAML file with your preset queries. See `query_presets.yaml.example` for a complete example with many preset queries.

**Basic structure:**

```yaml
- name: "All Nodes"
  description: "List all nodes with basic info"
  query: 'nodes[certname, catalog_timestamp] {}'
  endpoint: pql
  raw_json: false

- name: "Failed Nodes"
  description: "Nodes with failed runs"
  query: 'nodes[certname] { latest_report_status = "failed" }'
  endpoint: pql
  raw_json: false
```

## Preset Fields

Each preset supports the following fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | **Yes** | - | Display name shown in the dropdown |
| `query` | **Yes** | - | The PuppetDB query string |
| `description` | No | `""` | Brief description (shown below dropdown) |
| `endpoint` | No | `"pql"` | PuppetDB API endpoint to query |
| `raw_json` | No | `false` | Display results as JSON instead of table |

### Available Endpoints

- `pql` - PQL queries (default, recommended)
- `nodes` - Nodes endpoint (AST queries)
- `resources` - Resources endpoint (AST queries)
- `facts` - Facts endpoint (AST queries)
- `factsets` - Fact Sets endpoint (AST queries)
- `fact-paths` - Fact Paths endpoint (AST queries)
- `fact-contents` - Fact Contents endpoint (AST queries)
- `fact-names` - Fact Names endpoint
- `reports` - Reports endpoint (AST queries)
- `events` - Events endpoint (AST queries)
- `catalogs` - Catalogs endpoint (AST queries)
- `edges` - Edges endpoint (AST queries)
- `environments` - Environments endpoint

**Note:** Non-PQL endpoints expect AST (Abstract Syntax Tree) queries. Puppetboard will automatically wrap them with `[]` brackets if needed.

## Usage

1. Navigate to the **Query** tab in Puppetboard
2. If presets are configured, you'll see a "Load Preset Query" dropdown at the top of the form
3. Select a preset from the dropdown
4. The form fields will auto-populate with:
   - Query text
   - API endpoint
   - Raw JSON checkbox state
5. If the preset has a description, it will appear below the dropdown
6. Click "Submit" to execute the query

## Example Preset Queries

### PQL Queries (Recommended)

```yaml
# Simple node query
- name: "All Nodes"
  query: 'nodes[certname, catalog_timestamp, facts_timestamp] {}'
  endpoint: pql

# Filtered query
- name: "Ubuntu Nodes"
  query: 'inventory[certname, facts.os.release.full] { facts.os.name = "Ubuntu" }'
  endpoint: pql

# Aggregation query
- name: "Node Count by Environment"
  query: |
    nodes[count(), catalog_environment] {
      group by catalog_environment
    }
  endpoint: pql

# Filtered query with condition
- name: "Failed Events"
  query: |
    events[certname, resource_type, message, timestamp] {
      status = "failure"
    }
  endpoint: pql
```

### AST Queries

```yaml
# AST query for nodes endpoint
- name: "AST - Ubuntu Nodes"
  description: "Find Ubuntu nodes using AST query"
  query: '"=", "facts.os.name", "Ubuntu"'
  endpoint: nodes
  raw_json: false
```

### Endpoint-Specific Queries

```yaml
# Get all fact names as JSON
- name: "All Fact Names"
  description: "List all available fact names"
  query: ""
  endpoint: fact-names
  raw_json: true

# Get all environments
- name: "All Environments"
  description: "List all Puppet environments"
  query: ""
  endpoint: environments
  raw_json: true
```

## Tips

1. **Use Multi-line Queries**: For complex queries, use YAML's multi-line string syntax:
   ```yaml
   query: |
     nodes[certname, facts.os.name, facts.os.release.full] {
       facts.os.name ~ "(?i)ubuntu"
       order by catalog_timestamp desc
     }
   ```

2. **Organize by Category**: Group related queries together in your YAML file with comments:
   ```yaml
   # === Node Queries ===
   - name: "All Nodes"
     ...

   # === Fact Queries ===
   - name: "OS Distribution"
     ...
   ```

3. **Include Examples**: Provide example presets that demonstrate different query patterns for your users.

4. **Use Raw JSON for APIs**: When querying endpoint-specific data (like fact-names, environments), use `raw_json: true` to see the actual API response.

5. **Test Your Queries**: Always test queries in the Query tab before adding them to the presets file.

## Troubleshooting

### Presets Not Showing Up

1. **Check Configuration**: Verify `QUERY_PRESETS_FILE` is set correctly in your settings
2. **Check File Path**: Ensure the file path is absolute and accessible to Puppetboard
3. **Check File Permissions**: Ensure Puppetboard process can read the file
4. **Check Logs**: Look for warnings in Puppetboard logs about YAML parsing errors
5. **Validate YAML**: Use a YAML validator to check syntax

### Preset Validation Errors

Presets are validated on load. Check logs for warnings about:
- Missing required fields (`name` or `query`)
- Invalid YAML syntax
- Incorrect data types

Invalid presets are skipped gracefully - the app will continue with valid presets only.

### Query Execution Fails

If a preset query fails when executed:
1. Check that the endpoint is in `ENABLED_QUERY_ENDPOINTS` config
2. Verify the query syntax matches the selected endpoint
3. For AST queries, ensure proper syntax (PQL is recommended for most use cases)

## Security Considerations

1. **File Access**: Only Puppetboard process needs read access to the presets file
2. **Query Safety**: Presets don't bypass PuppetDB query restrictions - all normal security applies
3. **User Modifications**: Users can modify loaded presets before submission - treat presets as templates
4. **Endpoint Restrictions**: Respect `ENABLED_QUERY_ENDPOINTS` configuration to limit available endpoints

## Migration from Manual Queries

To convert frequently-used manual queries to presets:

1. Execute the query normally in the Query tab
2. Once it works, copy the query text
3. Add it to your presets YAML file with a descriptive name
4. Reload Puppetboard to see the new preset

## See Also

- [PuppetDB PQL Query Tutorial](https://puppet.com/docs/puppetdb/latest/api/query/tutorial-pql.html)
- [PuppetDB AST Query Tutorial](https://puppet.com/docs/puppetdb/latest/api/query/tutorial.html)
- [PuppetDB API Endpoints](https://puppet.com/docs/puppetdb/latest/api/query/v4/overview.html)
- `query_presets.yaml.example` - Example presets file with many query examples
