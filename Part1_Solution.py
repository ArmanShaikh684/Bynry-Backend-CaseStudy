from flask import request, jsonify
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation


@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json

    # 1. First line of defense: Check if they actually sent the required fields
    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        return jsonify({
            "error": f"Bad Request. Missing fields: {', '.join(missing_fields)}"
        }), 400

    # 2. Type checking: Make sure numbers are actually numbers and aren't negative
    try:
        price = Decimal(str(data['price']))
        quantity = int(data['initial_quantity'])

        if quantity < 0 or price < 0:
            return jsonify({"error": "Price and quantity cannot be negative."}), 400

    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid data types for price or quantity."}), 400

    # 3. Database logic wrapped in a try/except for safety
    try:
        # Stage the product creation
        product = Product(
            name=data['name'],
            sku=data['sku'],
            price=price
        )
        db.session.add(product)

        # We need the product.id for the inventory record, but we don't want to
        # commit to the database just yet. flush() simulates the insert and
        # grabs the ID, but keeps the transaction open.
        db.session.flush()

        # Stage the inventory creation
        inventory = Inventory(
            product_id=product.id,
            warehouse_id=data['warehouse_id'],
            quantity=quantity
        )
        db.session.add(inventory)

        # If we made it this far without crashing, commit everything together!
        db.session.commit()

        return jsonify({
            "message": "Product created successfully",
            "product_id": product.id
        }), 201

    except IntegrityError:
        # If the SKU already exists, or the warehouse_id is bogus, it triggers this.
        # We roll back the transaction so the DB isn't stuck in a bad state.
        db.session.rollback()
        return jsonify({"error": "A product with this SKU already exists, or the warehouse ID is invalid."}), 409

    except Exception as e:
        # Catch-all for any other weird errors.
        # Note: In a real environment, I'd log 'e' to Datadog/Sentry here.
        db.session.rollback()
        return jsonify({"error": "An unexpected server error occurred."}), 500