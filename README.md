# InvenTree RMA Automation Plugin

An InvenTree plugin that automates stock item status changes when return orders are completed, with support for tracking and consuming repair parts.

## Features

- **Automatic Status Updates**: Updates stock item status based on return order line item outcomes
- **Repair Parts Tracking**: Allocate replacement parts to repairs and consume them on order completion
- **Configurable Status Mapping**: Customize the stock status for each outcome type
- **Customer Reassignment**: Optionally reassign repaired/returned items to the original customer
- **Audit Trail**: Tracking notes added to stock items for full history

## Repair Parts Panel

The plugin adds a "Repair Parts" panel to Return Order detail pages where you can:
- View allocated repair/replacement parts
- Add new part allocations with part search and stock selection
- See the location of parts for easy retrieval
- Parts are automatically consumed when the return order is completed

## Outcome to Stock Status Mapping

| Line Item Outcome | Default Stock Status | Description |
|-------------------|---------------------|-------------|
| Return | OK (10) | Item returned as-is, ready for stock |
| Repair | OK (10) | Item repaired, ready for stock |
| Replace | Attention (50) | Original item - needs processing |
| Refund | Attention (50) | Item kept, needs review |
| Reject | Rejected (65) | Item rejected |

All mappings are configurable in the plugin settings.

## Installation

### From PyPI (when published)

```bash
pip install inventree-rma-plugin
```

### From Source

```bash
pip install -e /path/to/inventree-rma-plugin
```

### In Docker Environment

Add to your InvenTree `plugins.txt`:

```
inventree-rma-plugin
```

Or install from git:

```
git+https://github.com/timmyhadwen/inventree-rma-plugin.git
```

## Configuration

After installation, enable the plugin in InvenTree's admin panel under Settings > Plugins.

### Required InvenTree Settings

Ensure these settings are enabled in InvenTree:

- **ENABLE_PLUGINS_APP**: Required for the plugin's database models
- **ENABLE_PLUGINS_URL**: Required for the plugin's API endpoints
- **ENABLE_PLUGINS_INTERFACE**: Required for the Repair Parts panel UI

### Plugin Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Enable Auto Status Change | True | Automatically update stock status on RO completion |
| Enable Customer Reassignment | False | Reassign repaired/returned items to original customer |
| Add Tracking Notes | True | Add notes to stock item history |
| Consume Repair Parts on Complete | True | Consume allocated repair parts when order completes |
| Status for RETURN Outcome | OK | Stock status when outcome is "Return" |
| Status for REPAIR Outcome | OK | Stock status when outcome is "Repair" |
| Status for REPLACE Outcome | Attention | Stock status when outcome is "Replace" |
| Status for REFUND Outcome | Attention | Stock status when outcome is "Refund" |
| Status for REJECT Outcome | Rejected | Stock status when outcome is "Reject" |

## Prerequisites

- InvenTree >= 0.15.0
- Return Orders feature enabled in InvenTree settings
- Event Integration enabled for plugins

## How It Works

### Status Automation

1. When a Return Order is marked as "Complete", InvenTree triggers the `returnorder.completed` event
2. The plugin listens for this event and processes each line item
3. For each line item with a defined outcome, the plugin:
   - Updates the stock item's status according to the configured mapping
   - Optionally reassigns the item back to the customer (for Return/Repair outcomes)
   - Adds a tracking note to the stock item history

### Repair Parts Consumption

1. Before completing a return order, allocate repair/replacement parts via the "Repair Parts" panel
2. Select the line item being repaired, search for the replacement part, and choose from available stock
3. When the return order is completed, allocated parts are automatically consumed (quantity reduced)
4. A tracking entry is added to each consumed stock item

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Project Structure

```
inventree-rma-plugin/
├── pyproject.toml
├── README.md
├── inventree_rma_plugin/
│   ├── __init__.py
│   ├── apps.py
│   ├── api.py
│   ├── models.py
│   ├── rma_automation.py
│   ├── migrations/
│   └── static/
│       └── repair_panel.js
└── tests/
    ├── __init__.py
    └── test_rma_automation.py
```

## License

MIT License

## Author

Timmy Hadwen (https://github.com/timmyhadwen)
