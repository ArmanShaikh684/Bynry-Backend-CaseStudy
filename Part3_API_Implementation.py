from flask import Blueprint, jsonify
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from models import db, Product, Inventory, Warehouse, Supplier, InventoryTransaction

# Setting up a Flask blueprint for our alerts
alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/api/companies/<uuid:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    # Set our "recent" window to 30 days ago
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    try:
        # 1. Fetch the raw low-stock inventory
        # We join the necessary tables and critically filter by the company_id
        # to ensure Tenant Isolation (nobody sees another company's data).
        low_stock_items = db.session.query(Inventory) \
            .join(Product) \
            .join(Warehouse) \
            .outerjoin(Supplier, Product.supplier_id == Supplier.id) \
            .filter(
            Product.company_id == company_id,
            Inventory.quantity <= Product.low_stock_threshold
        ) \
            .options(
            joinedload(Inventory.product),
            joinedload(Inventory.warehouse)
        ).all()

        alerts = []

        # 2. Process each low-stock item to check sales velocity
        for inv in low_stock_items:

            # Query the transaction ledger to sum up sales for this specific inventory record
            sales_data = db.session.query(
                func.sum(InventoryTransaction.quantity_change).label('total_sold')
            ).filter(
                InventoryTransaction.inventory_id == inv.id,
                InventoryTransaction.transaction_type == 'SALE',
                InventoryTransaction.created_at >= thirty_days_ago
            ).first()

            # Since sales are recorded as negative numbers in the ledger, we take the absolute value.
            # If there are no sales, it returns None, so we default to 0.
            total_sold_last_30 = abs(sales_data.total_sold) if sales_data.total_sold else 0

            # Edge Case: The "Dead Stock" check.
            # If it hasn't sold recently, don't alert them. Just skip to the next item.
            if total_sold_last_30 == 0:
                continue

            # 3. Math: Figure out when they will run out
            daily_burn_rate = total_sold_last_30 / 30.0
            # Prevent division by zero just in case, though the zero check above handles it
            days_left = int(inv.quantity / daily_burn_rate) if daily_burn_rate > 0 else 999

            # 4. Safely package the supplier data
            # We used an outerjoin earlier, so product.supplier might be None.
            supplier_info = None
            if inv.product.supplier:
                supplier_info = {
                    "id": inv.product.supplier.id,
                    "name": inv.product.supplier.name,
                    "contact_email": inv.product.supplier.contact_email
                }

            # 5. Append to our final response list
            alerts.append({
                "product_id": inv.product.id,
                "product_name": inv.product.name,
                "sku": inv.product.sku,
                "warehouse_id": inv.warehouse.id,
                "warehouse_name": inv.warehouse.name,
                "current_stock": inv.quantity,
                "threshold": inv.product.low_stock_threshold,
                "days_until_stockout": days_left,
                "supplier": supplier_info
            })

        # Return standard 200 OK with the payload
        return jsonify({
            "total_alerts": len(alerts),
            "alerts": alerts
        }), 200

    except Exception as e:
        # In a real app, I'd use logging.error(f"Low stock alert failed: {e}") here
        return jsonify({"error": "Failed to process low stock alerts. Please try again later."}), 500