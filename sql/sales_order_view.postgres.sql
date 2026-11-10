-- The same view for PostgreSQL. NOT run by this repo's tests. Test it on your own copy of the data.
-- A database view can feed a connected app, but it cannot accept writes back.
CREATE OR REPLACE VIEW sales_order_for_netsuite AS
SELECT
  o.id                     AS salesforce_order_id,
  a.netsuite_internal_id   AS entity_internal_id,
  o.po_number              AS other_ref_num,
  o.effective_date         AS tran_date,
  (SELECT jsonb_agg(jsonb_build_object(
            'item',     jsonb_build_object('internalId', m.netsuite_item_id),
            'quantity', oi.quantity,
            'rate',     oi.unit_price,
            'line',     oi.line_number)
          ORDER BY oi.line_number)
     FROM order_item oi
     JOIN item_map m ON m.product_code = oi.product_code
    WHERE oi.order_id = o.id) AS item_list
FROM sf_order o
JOIN sf_account a ON a.id = o.account_id
WHERE a.netsuite_internal_id IS NOT NULL;
