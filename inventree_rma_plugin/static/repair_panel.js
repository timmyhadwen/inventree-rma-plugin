/**
 * Repair Parts Panel for RMA Automation Plugin
 * React-based implementation using InvenTree's native components and form system
 */

// Format quantity - show whole number if no decimal, otherwise show decimal
function formatQty(value) {
    if (value == null) return '0';
    const num = parseFloat(value);
    return Number.isInteger(num) ? num.toString() : num.toFixed(2).replace(/\.?0+$/, '');
}

// API helper using the context's api instance or fetch fallback
async function apiFetch(ctx, url, options = {}) {
    // If we have the InvenTree api instance, use it
    if (ctx?.api) {
        try {
            const response = await ctx.api({
                url: url,
                method: options.method || 'GET',
                data: options.body ? JSON.parse(options.body) : undefined,
            });
            return response.data;
        } catch (error) {
            throw new Error(error.response?.data?.detail || error.message || 'Request failed');
        }
    }

    // Fallback to fetch
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            ...options.headers,
        },
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || JSON.stringify(error));
    }
    if (response.status === 204) return null;
    return response.json();
}

function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Main Panel Component
function RepairPartsPanel({ ctx }) {
    const React = window.React;
    const { useState, useEffect, useCallback, useMemo } = React;
    const { Button, Table, Text, Group, Badge, Stack, Loader, Alert, Paper, ActionIcon, Tooltip } = window.MantineCore;
    const IconTrash = window.TablerIcons?.IconTrash;

    const [allocations, setAllocations] = useState([]);
    const [lines, setLines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);

    const returnOrderId = ctx.id;
    const isComplete = ctx.instance?.status === 30;

    // Fetch data
    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const [allocData, linesData] = await Promise.all([
                apiFetch(ctx, `/plugin/rma-automation/allocations/?return_order=${returnOrderId}`),
                apiFetch(ctx, `/api/order/ro-line/?order=${returnOrderId}`),
            ]);
            setAllocations(allocData || []);
            setLines(linesData?.results || linesData || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [returnOrderId]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Delete allocation
    const handleDelete = async (id) => {
        if (!confirm('Remove this repair part allocation?')) return;
        try {
            await apiFetch(ctx, `/plugin/rma-automation/allocations/${id}/`, { method: 'DELETE' });
            fetchData();
        } catch (err) {
            alert('Failed to remove: ' + err.message);
        }
    };

    // Handle form success
    const handleFormSuccess = () => {
        setShowForm(false);
        fetchData();
    };

    if (loading) {
        return React.createElement(Group, { justify: 'center', p: 'xl' },
            React.createElement(Loader, { size: 'sm' }),
            React.createElement(Text, { size: 'sm', c: 'dimmed' }, 'Loading repair parts...')
        );
    }

    if (error) {
        return React.createElement(Alert, { color: 'red', title: 'Error' }, error);
    }

    // Render delete button with or without icon
    const renderDeleteButton = (allocId) => {
        if (IconTrash) {
            return React.createElement(Tooltip, { label: 'Remove allocation' },
                React.createElement(ActionIcon, {
                    color: 'red',
                    variant: 'subtle',
                    onClick: () => handleDelete(allocId)
                }, React.createElement(IconTrash, { size: 16 }))
            );
        }
        return React.createElement(Button, {
            color: 'red',
            size: 'xs',
            variant: 'subtle',
            onClick: () => handleDelete(allocId)
        }, '×');
    };

    return React.createElement(Stack, { gap: 'md' },
        // Header with description and add button
        React.createElement(Group, { justify: 'space-between', align: 'center' },
            React.createElement(Text, { size: 'sm', c: 'dimmed' },
                isComplete
                    ? 'This order is complete. Allocated parts have been consumed.'
                    : 'Allocate stock items to be consumed when this return order is completed.'
            ),
            !isComplete && React.createElement(Button, {
                onClick: () => setShowForm(true),
                size: 'compact-sm',
                variant: 'light',
            }, '+ Add Part')
        ),

        // Allocations table
        allocations.length === 0
            ? React.createElement(Paper, { p: 'lg', withBorder: true },
                React.createElement(Text, { c: 'dimmed', ta: 'center', fs: 'italic' },
                    'No repair parts allocated yet.'
                )
            )
            : React.createElement(Table, {
                striped: true,
                highlightOnHover: true,
                withTableBorder: true,
                verticalSpacing: 'sm',
            },
                React.createElement(Table.Thead, null,
                    React.createElement(Table.Tr, null,
                        React.createElement(Table.Th, { style: { width: '30%' } }, 'Repair Item'),
                        React.createElement(Table.Th, { style: { width: '30%' } }, 'Replacement Part'),
                        React.createElement(Table.Th, { style: { textAlign: 'center', width: '10%' } }, 'Qty'),
                        React.createElement(Table.Th, { style: { textAlign: 'center', width: '20%' } }, 'Status'),
                        !isComplete && React.createElement(Table.Th, { style: { width: '10%' } }, '')
                    )
                ),
                React.createElement(Table.Tbody, null,
                    allocations.map(alloc => {
                        const detail = alloc.stock_item_detail || {};
                        const lineDetail = alloc.line_item_detail || {};
                        return React.createElement(Table.Tr, { key: alloc.id },
                            // Repair Item column - show the line item being repaired
                            React.createElement(Table.Td, null,
                                React.createElement(Stack, { gap: 0 },
                                    React.createElement(Text, { size: 'sm', fw: 500 }, lineDetail.part_name || 'Unknown'),
                                    lineDetail.serial && React.createElement(Text, { size: 'xs', c: 'dimmed' }, `SN: ${lineDetail.serial}`)
                                )
                            ),
                            // Replacement Part column - show the stock item being consumed with location
                            React.createElement(Table.Td, null,
                                React.createElement(Stack, { gap: 0 },
                                    React.createElement(Text, { size: 'sm' }, detail.part_name || 'Unknown'),
                                    (detail.serial || detail.batch) && React.createElement(Text, { size: 'xs', c: 'dimmed' },
                                        detail.serial ? `SN: ${detail.serial}` : `Batch: ${detail.batch}`
                                    ),
                                    detail.location_name && React.createElement(Text, { size: 'xs', c: 'teal', fw: 500 },
                                        detail.location_name
                                    )
                                )
                            ),
                            React.createElement(Table.Td, { style: { textAlign: 'center' } },
                                React.createElement(Text, { size: 'sm' }, formatQty(alloc.quantity))
                            ),
                            React.createElement(Table.Td, { style: { textAlign: 'center' } },
                                React.createElement(Badge, {
                                    color: alloc.consumed ? 'green' : 'blue',
                                    variant: 'light',
                                    size: 'sm'
                                }, alloc.consumed ? 'Consumed' : 'Allocated')
                            ),
                            !isComplete && React.createElement(Table.Td, { style: { textAlign: 'center' } },
                                !alloc.consumed && renderDeleteButton(alloc.id)
                            )
                        );
                    })
                )
            ),

        // Add form modal
        showForm && React.createElement(AddAllocationForm, {
            ctx: ctx,
            lines: lines,
            returnOrderId: returnOrderId,
            onSuccess: handleFormSuccess,
            onCancel: () => setShowForm(false),
        })
    );
}

// Add Allocation Form Component (Modal)
function AddAllocationForm({ ctx, lines, returnOrderId, onSuccess, onCancel }) {
    const React = window.React;
    const { useState, useEffect } = React;
    const { Modal, TextInput, Select, NumberInput, Button, Text, Group, Badge, Stack, Loader, Alert, Paper, ScrollArea, UnstyledButton, Box, Divider } = window.MantineCore;

    const [selectedLine, setSelectedLine] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [selectedPart, setSelectedPart] = useState(null);
    const [stockItems, setStockItems] = useState([]);
    const [selectedStock, setSelectedStock] = useState(null);
    const [quantity, setQuantity] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searching, setSearching] = useState(false);
    const [loadingStock, setLoadingStock] = useState(false);

    // Search parts
    useEffect(() => {
        if (searchQuery.length < 2) {
            setSearchResults([]);
            return;
        }
        const timer = setTimeout(async () => {
            setSearching(true);
            try {
                const data = await apiFetch(ctx, `/api/part/?search=${encodeURIComponent(searchQuery)}&limit=20`);
                setSearchResults(data?.results || data || []);
            } catch (err) {
                console.error('Search failed:', err);
            } finally {
                setSearching(false);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Load stock when part selected - only show available stock
    useEffect(() => {
        if (!selectedPart) {
            setStockItems([]);
            return;
        }
        setLoadingStock(true);
        (async () => {
            try {
                // Filter for in_stock=true and available=true to exclude fully allocated stock
                const data = await apiFetch(ctx, `/api/stock/?part=${selectedPart.pk}&in_stock=true&available=true&limit=50`);
                const items = data?.results || data || [];
                // Calculate available quantity for each item
                const itemsWithAvailable = items.map(item => ({
                    ...item,
                    available_quantity: Math.max(0, (item.quantity || 0) - (item.allocated || 0))
                }));
                // Filter out items with no available quantity
                setStockItems(itemsWithAvailable.filter(item => item.available_quantity > 0));
            } catch (err) {
                console.error('Failed to load stock:', err);
            } finally {
                setLoadingStock(false);
            }
        })();
    }, [selectedPart]);

    // Submit
    const handleSubmit = async () => {
        if (!selectedLine || !selectedStock || !quantity) {
            setError('Please fill in all fields');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await apiFetch(ctx, '/plugin/rma-automation/allocations/', {
                method: 'POST',
                body: JSON.stringify({
                    return_order_line: parseInt(selectedLine),
                    stock_item: selectedStock.pk,
                    quantity: quantity,
                }),
            });
            onSuccess();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const lineOptions = lines.map(line => ({
        value: String(line.pk),
        label: `${line.item_detail?.part_detail?.name || 'Unknown'}${line.item_detail?.serial ? ` (SN: ${line.item_detail.serial})` : ''}`
    }));

    return React.createElement(Modal, {
        opened: true,
        onClose: onCancel,
        title: 'Add Repair Part',
        size: 'lg',
        centered: true,
        overlayProps: { backgroundOpacity: 0.55, blur: 3 },
    },
        React.createElement(Stack, { gap: 'md' },
            // Step 1: Line item select
            React.createElement(Select, {
                label: 'Line Item Being Repaired',
                description: 'Select which return order item this repair part is for',
                placeholder: 'Select line item...',
                data: lineOptions,
                value: selectedLine,
                onChange: setSelectedLine,
                searchable: true,
                required: true,
                withAsterisk: true,
            }),

            React.createElement(Divider, { label: 'Repair Part Selection', labelPosition: 'center' }),

            // Step 2: Part search
            !selectedPart ? React.createElement(Stack, { gap: 'xs' },
                React.createElement(TextInput, {
                    label: 'Search for Part',
                    placeholder: 'Type at least 2 characters to search...',
                    value: searchQuery,
                    onChange: (e) => setSearchQuery(e.target.value),
                    rightSection: searching ? React.createElement(Loader, { size: 'xs' }) : null,
                }),
                searchResults.length > 0 && React.createElement(Paper, { withBorder: true, p: 0, radius: 'sm' },
                    React.createElement(ScrollArea, { h: 200 },
                        searchResults.map((part, index) => React.createElement(React.Fragment, { key: part.pk },
                            React.createElement(UnstyledButton, {
                                onClick: () => {
                                    setSelectedPart(part);
                                    setSearchQuery('');
                                    setSearchResults([]);
                                },
                                style: { display: 'block', width: '100%' },
                            },
                                React.createElement(Box, {
                                    p: 'sm',
                                    style: {
                                        cursor: 'pointer',
                                        transition: 'background-color 150ms ease',
                                    },
                                    onMouseEnter: (e) => e.currentTarget.style.backgroundColor = 'var(--mantine-color-gray-1)',
                                    onMouseLeave: (e) => e.currentTarget.style.backgroundColor = 'transparent',
                                },
                                    React.createElement(Text, { size: 'sm', fw: 500 }, part.full_name || part.name),
                                    part.description && React.createElement(Text, { size: 'xs', c: 'dimmed', lineClamp: 1 }, part.description)
                                )
                            ),
                            index < searchResults.length - 1 && React.createElement(Divider, null)
                        ))
                    )
                )
            ) : React.createElement(Paper, { withBorder: true, p: 'sm', radius: 'sm', bg: 'var(--mantine-color-blue-light)' },
                React.createElement(Group, { justify: 'space-between' },
                    React.createElement(Stack, { gap: 0 },
                        React.createElement(Text, { size: 'xs', c: 'dimmed' }, 'Selected Part'),
                        React.createElement(Text, { fw: 500 }, selectedPart.full_name || selectedPart.name)
                    ),
                    React.createElement(Button, {
                        onClick: () => {
                            setSelectedPart(null);
                            setSelectedStock(null);
                            setStockItems([]);
                            setQuantity(1);
                        },
                        variant: 'subtle',
                        size: 'xs',
                    }, 'Change')
                )
            ),

            // Step 3: Stock items
            selectedPart && React.createElement(Stack, { gap: 'xs' },
                React.createElement(Group, { justify: 'space-between' },
                    React.createElement(Text, { size: 'sm', fw: 500 }, 'Select Stock Item'),
                    React.createElement(Text, { size: 'xs', c: 'dimmed' }, 'Only unallocated stock shown')
                ),
                loadingStock
                    ? React.createElement(Group, { justify: 'center', p: 'md' },
                        React.createElement(Loader, { size: 'sm' })
                    )
                    : stockItems.length === 0
                        ? React.createElement(Alert, { color: 'yellow', variant: 'light' }, 'No available stock for this part')
                        : React.createElement(Paper, { withBorder: true, p: 0, radius: 'sm' },
                            React.createElement(ScrollArea, { h: 200 },
                                stockItems.map((stock, index) => React.createElement(React.Fragment, { key: stock.pk },
                                    React.createElement(UnstyledButton, {
                                        onClick: () => {
                                            setSelectedStock(stock);
                                            setQuantity(Math.min(1, stock.available_quantity));
                                        },
                                        style: { display: 'block', width: '100%' },
                                    },
                                        React.createElement(Box, {
                                            p: 'sm',
                                            style: {
                                                backgroundColor: selectedStock?.pk === stock.pk ? 'var(--mantine-color-blue-light)' : undefined,
                                                cursor: 'pointer',
                                            },
                                        },
                                            React.createElement(Group, { justify: 'space-between', wrap: 'nowrap' },
                                                React.createElement(Stack, { gap: 0 },
                                                    React.createElement(Text, { size: 'sm', fw: selectedStock?.pk === stock.pk ? 600 : 400 },
                                                        stock.serial ? `SN: ${stock.serial}` :
                                                        stock.batch ? `Batch: ${stock.batch}` :
                                                        `Stock #${stock.pk}`
                                                    ),
                                                    React.createElement(Text, { size: 'xs', c: 'dimmed' },
                                                        stock.location_detail?.pathstring || 'Unknown location'
                                                    )
                                                ),
                                                React.createElement(Badge, {
                                                    color: 'green',
                                                    variant: 'light',
                                                    size: 'lg'
                                                }, formatQty(stock.available_quantity))
                                            )
                                        )
                                    ),
                                    index < stockItems.length - 1 && React.createElement(Divider, null)
                                ))
                            )
                        )
            ),

            // Step 4: Quantity
            selectedStock && React.createElement(NumberInput, {
                label: 'Quantity to Allocate',
                description: `Maximum available: ${formatQty(selectedStock.available_quantity)}`,
                value: quantity,
                onChange: setQuantity,
                min: 0.00001,
                max: selectedStock.available_quantity,
                step: 1,
                required: true,
                withAsterisk: true,
            }),

            // Error
            error && React.createElement(Alert, { color: 'red', variant: 'light', withCloseButton: true, onClose: () => setError(null) }, error),

            // Buttons
            React.createElement(Group, { justify: 'flex-end', mt: 'md' },
                React.createElement(Button, { variant: 'default', onClick: onCancel }, 'Cancel'),
                React.createElement(Button, {
                    onClick: handleSubmit,
                    loading: loading,
                    disabled: !selectedLine || !selectedStock || !quantity,
                }, 'Add Repair Part')
            )
        )
    );
}

// Export the render function for InvenTree plugin system
// Using the new single-argument signature - InvenTree handles context wrapping
export function renderRepairPartsPanel(ctx) {
    return window.React.createElement(RepairPartsPanel, { ctx: ctx });
}
