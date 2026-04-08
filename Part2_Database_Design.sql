-- Represents the tenant in our B2B SaaS
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Warehouses belong to a specific company
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Suppliers belong to a specific company
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255)
);

-- Core products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    type VARCHAR(50) DEFAULT 'standard', -- 'standard' or 'bundle'
    low_stock_threshold INT DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, sku) -- SKUs are unique per company, not globally
);

-- Maps which products belong inside a 'bundle' product
CREATE TABLE product_bundles (
    bundle_id UUID REFERENCES products(id) ON DELETE CASCADE,
    component_id UUID REFERENCES products(id) ON DELETE CASCADE,
    quantity_required INT NOT NULL DEFAULT 1 CHECK (quantity_required > 0),
    PRIMARY KEY (bundle_id, component_id)
);

-- Tracks how much of a product is in a specific warehouse
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, warehouse_id)
);

-- Immutable ledger for tracking all inventory changes over time (sales, restocks)
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inventory_id UUID REFERENCES inventory(id) ON DELETE CASCADE,
    quantity_change INT NOT NULL, -- Negative for sales, positive for restocks
    transaction_type VARCHAR(50) NOT NULL, -- 'SALE', 'RESTOCK', 'ADJUSTMENT'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes to speed up the API queries
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_transactions_inventory ON inventory_transactions(inventory_id);
CREATE INDEX idx_transactions_created_at ON inventory_transactions(created_at);