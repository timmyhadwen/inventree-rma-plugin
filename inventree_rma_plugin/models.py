"""Database models for the RMA Automation plugin."""

from django.db import models


class RepairStockAllocation(models.Model):
    """Tracks stock items allocated for repair work on return order line items.

    When a return order line item requires repair, stock items (replacement parts)
    can be allocated to it. These are consumed when the return order is completed.
    """

    return_order_line = models.ForeignKey(
        'order.ReturnOrderLineItem',
        on_delete=models.CASCADE,
        related_name='repair_allocations',
        help_text='The return order line item this allocation is for',
    )

    stock_item = models.ForeignKey(
        'stock.StockItem',
        on_delete=models.CASCADE,
        related_name='repair_allocations',
        help_text='The stock item being allocated for repair',
    )

    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=5,
        default=1,
        help_text='Quantity of stock allocated',
    )

    consumed = models.BooleanField(
        default=False,
        help_text='Whether this allocation has been consumed',
    )

    created = models.DateTimeField(
        auto_now_add=True,
        help_text='When this allocation was created',
    )

    notes = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Optional notes about this allocation',
    )

    class Meta:
        """Model metadata."""

        app_label = 'inventree_rma_plugin'
        verbose_name = 'Repair Stock Allocation'
        verbose_name_plural = 'Repair Stock Allocations'

    def __str__(self):
        """String representation."""
        return f'{self.quantity} x {self.stock_item} for {self.return_order_line}'

    @property
    def return_order(self):
        """Get the parent return order."""
        return self.return_order_line.order

    def clean(self):
        """Validate the allocation."""
        from django.core.exceptions import ValidationError

        # Check stock item has sufficient quantity
        if self.stock_item and not self.consumed:
            available = self.stock_item.quantity
            # Subtract other allocations for this stock item (excluding self)
            other_allocations = RepairStockAllocation.objects.filter(
                stock_item=self.stock_item,
                consumed=False,
            ).exclude(pk=self.pk)
            allocated = sum(a.quantity for a in other_allocations)
            available -= allocated

            if self.quantity > available:
                raise ValidationError({
                    'quantity': f'Only {available} available (already allocated: {allocated})',
                })
