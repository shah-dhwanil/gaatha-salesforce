-- 
-- depends: 20260113_01_rLns7

CREATE TABLE IF NOT EXISTS orders (
    id UUID DEFAULT gen_random_uuid(),
    retailer_id UUID NOT NULL,
    member_id UUID NOT NULL,
    base_amount NUMERIC NOT NULL,
    discount_amount NUMERIC NOT NULL,
    net_amount NUMERIC NOT NULL,
    igst_amount NUMERIC NOT NULL,
    cgst_amount NUMERIC NOT NULL,
    sgst_amount NUMERIC NOT NULL,
    total_amount NUMERIC NOT NULL,
    order_type VARCHAR(16) NOT NULL,
    order_status VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT fk_orders_retailer FOREIGN KEY (retailer_id) REFERENCES retailer(id),
    CONSTRAINT fk_orders_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT chk_order_value CHECK (base_amount >= 0 AND discount_amount >= 0 AND net_amount <= base_amount AND igst_amount >= 0 AND cgst_amount >= 0 AND sgst_amount >= 0 AND total_amount >= net_amount)
);

CREATE INDEX IF NOT EXISTS idx_orders_retailer_id ON orders(retailer_id);
CREATE INDEX IF NOT EXISTS idx_orders_member_id ON orders(member_id);

CREATE TRIGGER orders_set_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE IF NOT EXISTS order_items (
    order_id UUID NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    CONSTRAINT pk_order_items PRIMARY KEY (order_id, product_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT chk_order_item_quantity CHECK (quantity > 0)
);