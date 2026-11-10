-- A view that turns Salesforce order rows into ONE row per order with an `itemList` JSON array.
-- This is the SQLite version, so the repo can test it. The Postgres version is next to it.
-- Table names are an example of a synced copy of Salesforce Order and OrderItem.
CREATE VIEW sales_order_for_netsuite AS
SELECT
  o.id                     AS salesforce_order_id,
  a.netsuite_internal_id   AS entity_internal_id,
  o.po_number              AS other_ref_num,
  o.effective_date         AS tran_date,
  (SELECT json_group_array(json_object(
            'item',     json_object('internalId', m.netsuite_item_id),
            'quantity', oi.quantity,
            'rate',     oi.unit_price,
            'line',     oi.line_number))
     FROM order_item oi
     JOIN item_map m ON m.product_code = oi.product_code
    WHERE oi.order_id = o.id
    ORDER BY oi.line_number) AS item_list
FROM sf_order o
JOIN sf_account a ON a.id = o.account_id
WHERE a.netsuite_internal_id IS NOT NULL;   -- never send an order for a customer that does not exist in NetSuite yet
