"""API endpoints for the RMA Automation plugin."""

from rest_framework import serializers, generics, permissions
from rest_framework.response import Response

from inventree_rma_plugin.models import RepairStockAllocation


class RepairAllocationSerializer(serializers.ModelSerializer):
    """Serializer for RepairStockAllocation model."""

    # Read-only fields for display
    stock_item_detail = serializers.SerializerMethodField(read_only=True)
    line_item_detail = serializers.SerializerMethodField(read_only=True)
    return_order_line_detail = serializers.SerializerMethodField(read_only=True)
    return_order_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        """Serializer metadata."""

        model = RepairStockAllocation
        fields = [
            'id',
            'return_order_line',
            'return_order_line_detail',
            'line_item_detail',
            'return_order_id',
            'stock_item',
            'stock_item_detail',
            'quantity',
            'consumed',
            'created',
            'notes',
        ]
        read_only_fields = ['id', 'consumed', 'created']

    def get_stock_item_detail(self, obj):
        """Get stock item details for display."""
        stock_item = obj.stock_item
        return {
            'pk': stock_item.pk,
            'part': stock_item.part.pk,
            'part_name': stock_item.part.name,
            'quantity': float(stock_item.quantity),
            'serial': stock_item.serial,
            'batch': stock_item.batch,
            'location': stock_item.location.pk if stock_item.location else None,
            'location_name': str(stock_item.location) if stock_item.location else None,
        }

    def get_line_item_detail(self, obj):
        """Get the line item details (the item being repaired)."""
        line = obj.return_order_line
        item = line.item if line else None
        if not item:
            return {
                'pk': None,
                'part_name': 'Unknown',
                'serial': None,
            }
        return {
            'pk': item.pk,
            'part_name': item.part.name if item.part else 'Unknown',
            'serial': item.serial,
            'batch': item.batch,
        }

    def get_return_order_line_detail(self, obj):
        """Get return order line item details for display."""
        line = obj.return_order_line
        return {
            'pk': line.pk,
            'item_pk': line.item.pk if line.item else None,
            'item_name': str(line.item) if line.item else None,
        }

    def get_return_order_id(self, obj):
        """Get the parent return order ID."""
        return obj.return_order_line.order.pk

    def validate(self, data):
        """Validate the allocation data."""
        stock_item = data.get('stock_item')
        quantity = data.get('quantity', 1)

        if stock_item:
            # Check available quantity
            available = stock_item.quantity

            # Subtract existing allocations for this stock item
            existing_allocations = RepairStockAllocation.objects.filter(
                stock_item=stock_item,
                consumed=False,
            )

            # Exclude current instance if updating
            if self.instance:
                existing_allocations = existing_allocations.exclude(pk=self.instance.pk)

            allocated = sum(float(a.quantity) for a in existing_allocations)
            available -= allocated

            if quantity > available:
                raise serializers.ValidationError({
                    'quantity': f'Only {available} available (already allocated: {allocated})',
                })

        return data


class RepairAllocationList(generics.ListCreateAPIView):
    """List and create repair stock allocations."""

    serializer_class = RepairAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter allocations based on query parameters."""
        queryset = RepairStockAllocation.objects.all()

        # Filter by return order
        return_order = self.request.query_params.get('return_order')
        if return_order:
            queryset = queryset.filter(return_order_line__order__pk=return_order)

        # Filter by return order line
        return_order_line = self.request.query_params.get('return_order_line')
        if return_order_line:
            queryset = queryset.filter(return_order_line__pk=return_order_line)

        # Filter by consumed status
        consumed = self.request.query_params.get('consumed')
        if consumed is not None:
            consumed_bool = consumed.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(consumed=consumed_bool)

        return queryset.select_related(
            'stock_item',
            'stock_item__part',
            'stock_item__location',
            'return_order_line',
            'return_order_line__order',
            'return_order_line__item',
            'return_order_line__item__part',
        )


class RepairAllocationDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a repair stock allocation."""

    serializer_class = RepairAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = RepairStockAllocation.objects.all()
