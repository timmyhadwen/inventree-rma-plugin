"""RMA Automation Plugin for InvenTree.

Automates stock item status changes when return orders are completed,
based on the outcome set for each return order line item.

Also provides repair parts tracking - allocate stock items to be consumed
when repairs are completed.
"""

from typing import Optional

import structlog

from plugin import InvenTreePlugin
from plugin.mixins import AppMixin, EventMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin

logger = structlog.get_logger('inventree')


class RMAAutomationPlugin(AppMixin, UserInterfaceMixin, UrlsMixin, EventMixin, SettingsMixin, InvenTreePlugin):
    """Plugin that automates actions on return order line items when a return order is completed.

    When a return order is marked as complete, this plugin:
    1. Iterates through all line items
    2. Updates each stock item's status based on the line item outcome
    3. Optionally reassigns stock items back to the customer
    4. Consumes any allocated repair parts

    Outcome-to-Status Mapping:
    - RETURN (20): Stock status -> OK (ready to return to customer)
    - REPAIR (30): Stock status -> OK (repaired and ready)
    - REPLACE (40): Stock status -> configurable (original item handling)
    - REFUND (50): Stock status -> ATTENTION (item needs review)
    - REJECT (60): Stock status -> REJECTED
    """

    NAME = 'RMA Automation'
    SLUG = 'rma-automation'
    TITLE = 'RMA Workflow Automation'
    DESCRIPTION = 'Automates stock status changes and repair parts tracking for return orders'
    VERSION = '0.2.0'
    AUTHOR = 'Timmy Hadwen'

    # Status code constants (from InvenTree)
    # ReturnOrderLineStatus
    OUTCOME_PENDING = 10
    OUTCOME_RETURN = 20
    OUTCOME_REPAIR = 30
    OUTCOME_REPLACE = 40
    OUTCOME_REFUND = 50
    OUTCOME_REJECT = 60

    # StockStatus
    STOCK_OK = 10
    STOCK_ATTENTION = 50
    STOCK_DAMAGED = 55
    STOCK_DESTROYED = 60
    STOCK_REJECTED = 65
    STOCK_LOST = 70
    STOCK_QUARANTINED = 75
    STOCK_RETURNED = 85

    # All available stock status choices
    ALL_STATUS_CHOICES = [
        ('10', 'OK'),
        ('50', 'Attention'),
        ('55', 'Damaged'),
        ('60', 'Destroyed'),
        ('65', 'Rejected'),
        ('70', 'Lost'),
        ('75', 'Quarantined'),
        ('85', 'Returned'),
    ]

    SETTINGS = {
        'ENABLE_AUTO_STATUS': {
            'name': 'Enable Auto Status Change',
            'description': 'Automatically update stock item status when return order is completed',
            'validator': bool,
            'default': True,
        },
        'ENABLE_CUSTOMER_REASSIGN': {
            'name': 'Enable Customer Reassignment',
            'description': 'Reassign repaired/returned items back to the original customer',
            'validator': bool,
            'default': False,
        },
        'ADD_TRACKING_NOTES': {
            'name': 'Add Tracking Notes',
            'description': 'Add tracking notes to stock items when status changes',
            'validator': bool,
            'default': True,
        },
        'CONSUME_REPAIR_PARTS': {
            'name': 'Consume Repair Parts on Complete',
            'description': 'Automatically consume allocated repair parts when return order is completed',
            'validator': bool,
            'default': True,
        },
        'STATUS_FOR_RETURN': {
            'name': 'Status for RETURN Outcome',
            'description': 'Stock status to set when line item outcome is RETURN',
            'default': '10',
            'choices': ALL_STATUS_CHOICES,
        },
        'STATUS_FOR_REPAIR': {
            'name': 'Status for REPAIR Outcome',
            'description': 'Stock status to set when line item outcome is REPAIR',
            'default': '10',
            'choices': ALL_STATUS_CHOICES,
        },
        'STATUS_FOR_REPLACE': {
            'name': 'Status for REPLACE Outcome',
            'description': 'Stock status to set for original item when outcome is REPLACE',
            'default': '50',
            'choices': ALL_STATUS_CHOICES,
        },
        'STATUS_FOR_REFUND': {
            'name': 'Status for REFUND Outcome',
            'description': 'Stock status to set when line item outcome is REFUND',
            'default': '50',
            'choices': ALL_STATUS_CHOICES,
        },
        'STATUS_FOR_REJECT': {
            'name': 'Status for REJECT Outcome',
            'description': 'Stock status to set when line item outcome is REJECT',
            'default': '65',
            'choices': ALL_STATUS_CHOICES,
        },
    }

    def setup_urls(self):
        """Set up URL patterns for the plugin API."""
        from django.urls import path
        from inventree_rma_plugin import api

        return [
            path('allocations/', api.RepairAllocationList.as_view(), name='repair-allocation-list'),
            path('allocations/<int:pk>/', api.RepairAllocationDetail.as_view(), name='repair-allocation-detail'),
        ]

    def get_ui_panels(self, request, context, **kwargs):
        """Return custom panels to display on Return Order pages."""
        panels = []
        target_model = context.get('target_model', None) if context else None

        # Add repair parts panel to return order detail pages
        if target_model == 'returnorder':
            panels.append({
                'key': 'repair-parts',
                'title': 'Repair Parts',
                'description': 'Stock items allocated for repairs',
                'icon': 'ti:tools:outline',
                'source': self.plugin_static_file('repair_panel.js:renderRepairPartsPanel'),
            })

        return panels

    def wants_process_event(self, event: str) -> bool:
        """Determine if this plugin wants to process the given event.

        Only process return order completion events.
        """
        return event == 'returnorder.completed'

    def process_event(self, event: str, *args, **kwargs) -> None:
        """Process a return order completion event.

        Args:
            event: The event name (should be 'returnorder.completed')
            *args: Additional positional arguments
            **kwargs: Keyword arguments containing:
                - id: The primary key of the completed ReturnOrder
        """
        order_id = kwargs.get('id')
        if not order_id:
            logger.warning('RMA Automation: No order ID provided in event kwargs')
            return

        logger.info('RMA Automation: Processing return order completion', order_id=order_id)

        try:
            # Process status changes
            if self.get_setting('ENABLE_AUTO_STATUS'):
                self._process_return_order(order_id)

            # Consume allocated repair parts
            if self.get_setting('CONSUME_REPAIR_PARTS'):
                self._consume_repair_parts(order_id)

        except Exception as e:
            logger.error(
                'RMA Automation: Error processing return order',
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )

    def _process_return_order(self, order_id: int) -> None:
        """Process all line items for a completed return order.

        Args:
            order_id: The primary key of the ReturnOrder
        """
        # Import models here to avoid circular imports
        from order.models import ReturnOrder

        try:
            return_order = ReturnOrder.objects.get(pk=order_id)
        except ReturnOrder.DoesNotExist:
            logger.error('RMA Automation: Return order not found', order_id=order_id)
            return

        customer = return_order.customer
        enable_reassign = self.get_setting('ENABLE_CUSTOMER_REASSIGN')
        add_notes = self.get_setting('ADD_TRACKING_NOTES')

        # Process each line item
        for line_item in return_order.lines.all():
            self._process_line_item(
                line_item,
                return_order,
                customer,
                enable_reassign,
                add_notes,
            )

    def _process_line_item(
        self,
        line_item,
        return_order,
        customer,
        enable_reassign: bool,
        add_notes: bool,
    ) -> None:
        """Process a single return order line item.

        Args:
            line_item: The ReturnOrderLineItem instance
            return_order: The parent ReturnOrder
            customer: The customer Company (may be None)
            enable_reassign: Whether to reassign items to customer
            add_notes: Whether to add tracking notes
        """
        stock_item = line_item.item
        if not stock_item:
            logger.warning(
                'RMA Automation: Line item has no stock item',
                line_item_id=line_item.pk,
            )
            return

        outcome = line_item.outcome
        new_status = self._get_status_for_outcome(outcome)

        if new_status is None:
            logger.debug(
                'RMA Automation: No status change for outcome',
                outcome=outcome,
                stock_item_id=stock_item.pk,
            )
            return

        # Determine if we should reassign to customer
        should_reassign = (
            enable_reassign
            and customer
            and outcome in (self.OUTCOME_RETURN, self.OUTCOME_REPAIR)
        )

        # Build the tracking note
        note = self._build_tracking_note(outcome, return_order, new_status, line_item) if add_notes else None

        # Update the stock item
        self._update_stock_item(
            stock_item,
            new_status,
            customer if should_reassign else None,
            note,
        )

        logger.info(
            'RMA Automation: Updated stock item',
            stock_item_id=stock_item.pk,
            outcome=outcome,
            new_status=new_status,
            reassigned_to_customer=should_reassign,
        )

    def _get_status_for_outcome(self, outcome: int) -> Optional[int]:
        """Get the stock status to set based on line item outcome.

        Args:
            outcome: The ReturnOrderLineStatus value

        Returns:
            The StockStatus value to set, or None if no change needed
        """
        status_mapping = {
            self.OUTCOME_RETURN: self.get_setting('STATUS_FOR_RETURN'),
            self.OUTCOME_REPAIR: self.get_setting('STATUS_FOR_REPAIR'),
            self.OUTCOME_REPLACE: self.get_setting('STATUS_FOR_REPLACE'),
            self.OUTCOME_REFUND: self.get_setting('STATUS_FOR_REFUND'),
            self.OUTCOME_REJECT: self.get_setting('STATUS_FOR_REJECT'),
        }

        status = status_mapping.get(outcome)
        if status is not None:
            return int(status)
        return None

    def _build_tracking_note(self, outcome: int, return_order, new_status: int, line_item) -> str:
        """Build a tracking note for the stock item.

        Args:
            outcome: The line item outcome
            return_order: The ReturnOrder instance
            new_status: The new stock status
            line_item: The ReturnOrderLineItem instance

        Returns:
            A descriptive note string
        """
        outcome_names = {
            self.OUTCOME_PENDING: 'Pending',
            self.OUTCOME_RETURN: 'Return',
            self.OUTCOME_REPAIR: 'Repair',
            self.OUTCOME_REPLACE: 'Replace',
            self.OUTCOME_REFUND: 'Refund',
            self.OUTCOME_REJECT: 'Reject',
        }

        status_names = {
            self.STOCK_OK: 'OK',
            self.STOCK_ATTENTION: 'Attention',
            self.STOCK_DAMAGED: 'Damaged',
            self.STOCK_DESTROYED: 'Destroyed',
            self.STOCK_REJECTED: 'Rejected',
            self.STOCK_LOST: 'Lost',
            self.STOCK_QUARANTINED: 'Quarantined',
            self.STOCK_RETURNED: 'Returned',
        }

        outcome_name = outcome_names.get(outcome, f'#{outcome}')
        status_name = status_names.get(new_status, f'#{new_status}')

        # Format: "RMA-0003: Repair → OK"
        note = f'{return_order.reference}: {outcome_name} → {status_name}'

        # Append any notes from the line item
        if line_item.notes:
            note += f'\n{line_item.notes}'

        return note

    def _update_stock_item(
        self,
        stock_item,
        new_status: int,
        customer=None,
        note: Optional[str] = None,
    ) -> None:
        """Update a stock item's status and optionally reassign to customer.

        Args:
            stock_item: The StockItem instance
            new_status: The new status code to set
            customer: Optional customer Company to reassign to
            note: Optional tracking note to add
        """
        from stock.status_codes import StockHistoryCode

        # Only update if status is changing
        if stock_item.status != new_status:
            stock_item.set_status(new_status)

        # Reassign to customer if specified
        if customer is not None:
            stock_item.customer = customer

        # Save the stock item
        stock_item.save(add_note=False)

        # Add tracking note if provided
        if note:
            stock_item.add_tracking_entry(
                StockHistoryCode.EDITED,
                None,  # User - will be None for automated actions
                notes=note,
                deltas={'status': new_status},
            )

    def _consume_repair_parts(self, order_id: int) -> None:
        """Consume all allocated repair parts for a return order.

        Args:
            order_id: The primary key of the ReturnOrder
        """
        from inventree_rma_plugin.models import RepairStockAllocation
        from order.models import ReturnOrder
        from stock.status_codes import StockHistoryCode

        try:
            return_order = ReturnOrder.objects.get(pk=order_id)
        except ReturnOrder.DoesNotExist:
            logger.error('RMA Automation: Return order not found for parts consumption', order_id=order_id)
            return

        # Get all unconsumed allocations for this order's line items
        allocations = RepairStockAllocation.objects.filter(
            return_order_line__order=return_order,
            consumed=False,
        )

        for allocation in allocations:
            stock_item = allocation.stock_item
            quantity = allocation.quantity

            logger.info(
                'RMA Automation: Consuming repair part',
                stock_item_id=stock_item.pk,
                quantity=quantity,
                return_order=return_order.reference,
            )

            # Subtract the quantity from stock
            if stock_item.quantity >= quantity:
                stock_item.quantity -= quantity
                stock_item.save(add_note=False)

                # Add tracking entry
                stock_item.add_tracking_entry(
                    StockHistoryCode.EDITED,
                    None,
                    notes=f'Consumed for repair: {return_order.reference}',
                    deltas={'removed': float(quantity)},
                )

                # Mark allocation as consumed
                allocation.consumed = True
                allocation.save()
            else:
                logger.warning(
                    'RMA Automation: Insufficient stock to consume',
                    stock_item_id=stock_item.pk,
                    available=stock_item.quantity,
                    requested=quantity,
                )
