"""Tests for RMA Automation Plugin."""

import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock


# Mock InvenTree modules before importing the plugin
sys.modules['plugin'] = MagicMock()
sys.modules['plugin.mixins'] = MagicMock()
sys.modules['structlog'] = MagicMock()


class MockEventMixin:
    """Mock EventMixin class."""
    pass


class MockSettingsMixin:
    """Mock SettingsMixin class."""

    def get_setting(self, key):
        """Return mock settings."""
        return getattr(self, f'_setting_{key}', None)


class MockInvenTreePlugin:
    """Mock InvenTreePlugin class."""
    pass


# Patch the mixins before import
with patch.dict(sys.modules, {
    'plugin': MagicMock(),
    'plugin.mixins': MagicMock(),
}):
    sys.modules['plugin'].InvenTreePlugin = MockInvenTreePlugin
    sys.modules['plugin.mixins'].EventMixin = MockEventMixin
    sys.modules['plugin.mixins'].SettingsMixin = MockSettingsMixin

    from inventree_rma_plugin.rma_automation import RMAAutomationPlugin


class TestRMAAutomationPlugin(TestCase):
    """Test cases for RMAAutomationPlugin."""

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = RMAAutomationPlugin()
        # Set default settings
        self.plugin._setting_ENABLE_AUTO_STATUS = True
        self.plugin._setting_ENABLE_CUSTOMER_REASSIGN = False
        self.plugin._setting_ADD_TRACKING_NOTES = True
        self.plugin._setting_STATUS_FOR_RETURN = 10  # OK
        self.plugin._setting_STATUS_FOR_REPAIR = 10  # OK
        self.plugin._setting_STATUS_FOR_REPLACE = 50  # Attention
        self.plugin._setting_STATUS_FOR_REFUND = 50  # Attention
        self.plugin._setting_STATUS_FOR_REJECT = 65  # Rejected

    def test_plugin_metadata(self):
        """Test plugin metadata is correctly defined."""
        self.assertEqual(self.plugin.NAME, 'RMA Automation')
        self.assertEqual(self.plugin.SLUG, 'rma-automation')
        self.assertEqual(self.plugin.VERSION, '0.2.0')
        self.assertEqual(self.plugin.AUTHOR, 'Timmy Hadwen')

    def test_wants_process_event_returns_true_for_returnorder_completed(self):
        """Test that plugin wants to process returnorder.completed events."""
        result = self.plugin.wants_process_event('returnorder.completed')
        self.assertTrue(result)

    def test_wants_process_event_returns_false_for_other_events(self):
        """Test that plugin ignores other events."""
        self.assertFalse(self.plugin.wants_process_event('returnorder.created'))
        self.assertFalse(self.plugin.wants_process_event('salesorder.completed'))
        self.assertFalse(self.plugin.wants_process_event('stock.changed'))
        self.assertFalse(self.plugin.wants_process_event(''))

    def test_process_event_returns_early_when_disabled(self):
        """Test that processing is skipped when auto status is disabled."""
        self.plugin._setting_ENABLE_AUTO_STATUS = False

        # Should not raise any errors and return early
        self.plugin.process_event('returnorder.completed', id=1)

    def test_process_event_returns_early_without_order_id(self):
        """Test that processing is skipped when no order ID provided."""
        # Should not raise any errors and return early
        self.plugin.process_event('returnorder.completed')

    def test_get_status_for_outcome_return(self):
        """Test status mapping for RETURN outcome."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_RETURN)
        self.assertEqual(result, 10)  # OK

    def test_get_status_for_outcome_repair(self):
        """Test status mapping for REPAIR outcome."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_REPAIR)
        self.assertEqual(result, 10)  # OK

    def test_get_status_for_outcome_replace(self):
        """Test status mapping for REPLACE outcome."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_REPLACE)
        self.assertEqual(result, 50)  # Attention

    def test_get_status_for_outcome_refund(self):
        """Test status mapping for REFUND outcome."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_REFUND)
        self.assertEqual(result, 50)  # Attention

    def test_get_status_for_outcome_reject(self):
        """Test status mapping for REJECT outcome."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_REJECT)
        self.assertEqual(result, 65)  # Rejected

    def test_get_status_for_outcome_pending(self):
        """Test status mapping for PENDING outcome returns None."""
        result = self.plugin._get_status_for_outcome(self.plugin.OUTCOME_PENDING)
        self.assertIsNone(result)

    def test_get_status_for_outcome_unknown(self):
        """Test status mapping for unknown outcome returns None."""
        result = self.plugin._get_status_for_outcome(999)
        self.assertIsNone(result)

    def test_build_tracking_note(self):
        """Test tracking note generation."""
        mock_return_order = MagicMock()
        mock_return_order.reference = 'RMA-001'
        mock_line_item = MagicMock()
        mock_line_item.notes = None

        note = self.plugin._build_tracking_note(
            self.plugin.OUTCOME_REPAIR,
            mock_return_order,
            self.plugin.STOCK_OK,
            mock_line_item,
        )

        self.assertEqual(note, 'RMA-001: Repair → OK')

    def test_build_tracking_note_with_line_item_note(self):
        """Test tracking note includes line item notes."""
        mock_return_order = MagicMock()
        mock_return_order.reference = 'RMA-001'
        mock_line_item = MagicMock()
        mock_line_item.notes = 'Customer reported screen flickering'

        note = self.plugin._build_tracking_note(
            self.plugin.OUTCOME_REPAIR,
            mock_return_order,
            self.plugin.STOCK_OK,
            mock_line_item,
        )

        self.assertEqual(note, 'RMA-001: Repair → OK\nCustomer reported screen flickering')

    def test_build_tracking_note_unknown_outcome(self):
        """Test tracking note with unknown outcome code."""
        mock_return_order = MagicMock()
        mock_return_order.reference = 'RMA-002'
        mock_line_item = MagicMock()
        mock_line_item.notes = None

        note = self.plugin._build_tracking_note(999, mock_return_order, 10, mock_line_item)

        self.assertIn('#999', note)

    def test_settings_defined(self):
        """Test that all expected settings are defined."""
        expected_settings = [
            'ENABLE_AUTO_STATUS',
            'ENABLE_CUSTOMER_REASSIGN',
            'ADD_TRACKING_NOTES',
            'STATUS_FOR_RETURN',
            'STATUS_FOR_REPAIR',
            'STATUS_FOR_REPLACE',
            'STATUS_FOR_REFUND',
            'STATUS_FOR_REJECT',
        ]

        for setting in expected_settings:
            self.assertIn(setting, self.plugin.SETTINGS)

    def test_settings_have_defaults(self):
        """Test that all settings have default values."""
        for key, config in self.plugin.SETTINGS.items():
            self.assertIn('default', config, f"Setting {key} missing default")

    def test_outcome_constants(self):
        """Test outcome constant values match InvenTree."""
        self.assertEqual(self.plugin.OUTCOME_PENDING, 10)
        self.assertEqual(self.plugin.OUTCOME_RETURN, 20)
        self.assertEqual(self.plugin.OUTCOME_REPAIR, 30)
        self.assertEqual(self.plugin.OUTCOME_REPLACE, 40)
        self.assertEqual(self.plugin.OUTCOME_REFUND, 50)
        self.assertEqual(self.plugin.OUTCOME_REJECT, 60)

    def test_stock_status_constants(self):
        """Test stock status constant values match InvenTree."""
        self.assertEqual(self.plugin.STOCK_OK, 10)
        self.assertEqual(self.plugin.STOCK_ATTENTION, 50)
        self.assertEqual(self.plugin.STOCK_DAMAGED, 55)
        self.assertEqual(self.plugin.STOCK_DESTROYED, 60)
        self.assertEqual(self.plugin.STOCK_REJECTED, 65)
        self.assertEqual(self.plugin.STOCK_QUARANTINED, 75)
        self.assertEqual(self.plugin.STOCK_RETURNED, 85)


class TestProcessLineItem(TestCase):
    """Test cases for _process_line_item method."""

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = RMAAutomationPlugin()
        self.plugin._setting_ENABLE_AUTO_STATUS = True
        self.plugin._setting_ENABLE_CUSTOMER_REASSIGN = True
        self.plugin._setting_ADD_TRACKING_NOTES = True
        self.plugin._setting_STATUS_FOR_RETURN = 10
        self.plugin._setting_STATUS_FOR_REPAIR = 10
        self.plugin._setting_STATUS_FOR_REPLACE = 50
        self.plugin._setting_STATUS_FOR_REFUND = 50
        self.plugin._setting_STATUS_FOR_REJECT = 65

    def test_process_line_item_with_no_stock_item(self):
        """Test handling of line item with no stock item."""
        line_item = MagicMock()
        line_item.item = None
        line_item.pk = 1

        return_order = MagicMock()
        customer = MagicMock()

        # Should not raise any errors
        self.plugin._process_line_item(
            line_item, return_order, customer, True, True
        )

    def test_process_line_item_with_pending_outcome(self):
        """Test handling of line item with PENDING outcome (no status change)."""
        stock_item = MagicMock()
        stock_item.pk = 1

        line_item = MagicMock()
        line_item.item = stock_item
        line_item.outcome = self.plugin.OUTCOME_PENDING

        return_order = MagicMock()
        customer = MagicMock()

        with patch.object(self.plugin, '_update_stock_item') as mock_update:
            self.plugin._process_line_item(
                line_item, return_order, customer, True, True
            )
            # Should not call update for PENDING outcome
            mock_update.assert_not_called()

    def test_process_line_item_repair_with_customer_reassign(self):
        """Test REPAIR outcome with customer reassignment enabled."""
        stock_item = MagicMock()
        stock_item.pk = 1

        line_item = MagicMock()
        line_item.item = stock_item
        line_item.outcome = self.plugin.OUTCOME_REPAIR

        return_order = MagicMock()
        return_order.reference = 'RMA-001'
        customer = MagicMock()

        with patch.object(self.plugin, '_update_stock_item') as mock_update:
            self.plugin._process_line_item(
                line_item, return_order, customer,
                enable_reassign=True, add_notes=True
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            # Check that customer is passed for reassignment
            self.assertEqual(call_args[0][0], stock_item)
            self.assertEqual(call_args[0][1], 10)  # OK status
            self.assertEqual(call_args[0][2], customer)

    def test_process_line_item_reject_no_customer_reassign(self):
        """Test REJECT outcome does not reassign customer."""
        stock_item = MagicMock()
        stock_item.pk = 1

        line_item = MagicMock()
        line_item.item = stock_item
        line_item.outcome = self.plugin.OUTCOME_REJECT

        return_order = MagicMock()
        return_order.reference = 'RMA-001'
        customer = MagicMock()

        with patch.object(self.plugin, '_update_stock_item') as mock_update:
            self.plugin._process_line_item(
                line_item, return_order, customer,
                enable_reassign=True, add_notes=True
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            # Check that customer is NOT passed for rejected items
            self.assertEqual(call_args[0][1], 65)  # Rejected status
            self.assertIsNone(call_args[0][2])  # No customer


class TestUpdateStockItem(TestCase):
    """Test cases for _update_stock_item method."""

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = RMAAutomationPlugin()

    def test_update_stock_item_status_change(self):
        """Test updating stock item status."""
        stock_item = MagicMock()
        stock_item.status = 75  # QUARANTINED
        stock_item.customer = None

        with patch.dict(sys.modules, {'stock.status_codes': MagicMock()}):
            self.plugin._update_stock_item(
                stock_item,
                new_status=10,  # OK
                customer=None,
                note=None,
            )

        stock_item.set_status.assert_called_once_with(10)
        stock_item.save.assert_called_once_with(add_note=False)

    def test_update_stock_item_with_customer_reassign(self):
        """Test updating stock item with customer reassignment."""
        stock_item = MagicMock()
        stock_item.status = 75
        stock_item.customer = None

        customer = MagicMock()
        customer.name = 'Test Customer'

        with patch.dict(sys.modules, {'stock.status_codes': MagicMock()}):
            self.plugin._update_stock_item(
                stock_item,
                new_status=10,
                customer=customer,
                note=None,
            )

        self.assertEqual(stock_item.customer, customer)
        stock_item.save.assert_called_once_with(add_note=False)

    def test_update_stock_item_with_tracking_note(self):
        """Test updating stock item with tracking note."""
        stock_item = MagicMock()
        stock_item.status = 75

        mock_history_code = MagicMock()
        mock_history_code.EDITED = 5

        with patch.dict(sys.modules, {'stock.status_codes': MagicMock(StockHistoryCode=mock_history_code)}):
            self.plugin._update_stock_item(
                stock_item,
                new_status=10,
                customer=None,
                note='Test tracking note',
            )

        stock_item.add_tracking_entry.assert_called_once()
        call_args = stock_item.add_tracking_entry.call_args
        self.assertEqual(call_args[1]['notes'], 'Test tracking note')


if __name__ == '__main__':
    import unittest
    unittest.main()
