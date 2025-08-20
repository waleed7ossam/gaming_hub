from odoo import models, fields, tools


class CafeReport(models.Model):
    _name = "cafe.report"
    _description = "Cafe Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Date and Time fields
    date = fields.Date('Date', readonly=True)
    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month', readonly=True)
    year = fields.Char('Year', readonly=True)
    quarter = fields.Char('Quarter', readonly=True)

    # Order Information
    order_id = fields.Many2one('cafe.order', string='Order', readonly=True)
    ref = fields.Char('Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)

    # Order Classification
    state = fields.Selection([
        ('available', 'Available'),
        ('running', 'Running'),
        ('finished', 'Finished'),
    ], string='State', readonly=True)

    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('blocked', 'Blocked'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
        ('draft', "Draft"),
        ('cancel', "Cancelled"),
    ], string='Payment Status', readonly=True)

    # Resources
    table_id = fields.Many2one('cafe.table', string='Table', readonly=True)
    table_num = fields.Char('Table Number', readonly=True)

    # Financial Analysis
    total = fields.Monetary('Total Amount', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # Order Line Analysis
    product_count = fields.Integer('Products Count', readonly=True)
    total_quantity = fields.Float('Total Quantity', readonly=True)
    avg_unit_price = fields.Monetary('Average Unit Price', readonly=True, currency_field='currency_id')
    total_discount = fields.Monetary('Total Discount Amount', readonly=True, currency_field='currency_id')
    discount_percentage = fields.Float('Average Discount %', readonly=True)

    # Aggregated Fields for Pivot Analysis (these make sense when aggregated)
    order_count = fields.Integer('Orders Count', readonly=True)
    total_revenue = fields.Monetary('Total Revenue', readonly=True, currency_field='currency_id')
    # This field will be used differently in pivot - represents the order value for averaging
    order_value_for_avg = fields.Monetary('Order Value for Averaging', readonly=True, currency_field='currency_id')

    # Performance Indicators
    items_per_order = fields.Float('Items per Order', readonly=True)
    revenue_per_table = fields.Monetary('Revenue per Table', readonly=True, currency_field='currency_id')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT 
                -- Primary Key
                row_number() OVER () AS id,

                -- Date Analysis (using create_date as cafe.order doesn't have explicit date field)
                DATE(co.create_date) AS date,
                to_char(co.create_date, 'MM') AS month,
                to_char(co.create_date, 'YYYY') AS year,
                'Q' || to_char(co.create_date, 'Q') AS quarter,

                -- Order Information
                co.id AS order_id,
                co.ref AS ref,
                co.partner_id AS partner_id,

                -- Order Classification
                co.state AS state,

                -- Payment Status (computed from move_ids)
                COALESCE(
                    (SELECT 
                        CASE 
                            WHEN am.payment_state = 'paid' THEN 'paid'
                            WHEN am.payment_state = 'partial' THEN 'partial'
                            WHEN am.payment_state = 'in_payment' THEN 'in_payment'
                            WHEN am.payment_state = 'not_paid' AND am.state = 'posted' THEN 'not_paid'
                            WHEN am.state = 'draft' THEN 'draft'
                            WHEN am.state = 'cancel' THEN 'cancel'
                            ELSE 'not_paid'
                        END
                     FROM account_move am 
                     WHERE am.cafe_id = co.id 
                       AND am.move_type = 'out_invoice' 
                     ORDER BY am.create_date DESC
                     LIMIT 1),
                    'not_paid'
                ) AS payment_status,

                -- Resources
                co.table_id AS table_id,
                ct.table_num AS table_num,

                -- Financial Analysis (computed from order lines)
                COALESCE(
                    (SELECT SUM(col.discount_included)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS total,
                comp.currency_id AS currency_id,

                -- Order Line Analysis
                COALESCE(
                    (SELECT COUNT(*)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0
                ) AS product_count,

                COALESCE(
                    (SELECT SUM(col.product_uom_qty)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS total_quantity,

                -- Average Unit Price: Weighted average considering quantities
                CASE 
                    WHEN COALESCE((SELECT SUM(col.product_uom_qty) FROM cafe_order_line col WHERE col.order_id = co.id), 0) > 0 THEN
                        COALESCE(
                            (SELECT SUM(col.price_unit * col.product_uom_qty) / NULLIF(SUM(col.product_uom_qty), 0)
                             FROM cafe_order_line col
                             WHERE col.order_id = co.id), 0.0
                        )
                    ELSE 0.0
                END AS avg_unit_price,

                -- Total Discount Amount
                COALESCE(
                    (SELECT SUM(col.discount_excluded - col.discount_included)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS total_discount,

                -- Average Discount Percentage
                CASE 
                    WHEN (SELECT COUNT(*) FROM cafe_order_line col WHERE col.order_id = co.id) > 0 THEN
                        COALESCE(
                            (SELECT AVG(col.discount)
                             FROM cafe_order_line col
                             WHERE col.order_id = co.id), 0.0
                        )
                    ELSE 0.0
                END AS discount_percentage,

                -- These fields are meant for aggregation in pivot views
                1 AS order_count,
                COALESCE(
                    (SELECT SUM(col.discount_included)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS total_revenue,
                -- This will be averaged in pivot view to get true average order value
                COALESCE(
                    (SELECT SUM(col.discount_included)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS order_value_for_avg,

                -- Performance Indicators
                COALESCE(
                    (SELECT SUM(col.product_uom_qty)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS items_per_order,

                COALESCE(
                    (SELECT SUM(col.discount_included)
                     FROM cafe_order_line col
                     WHERE col.order_id = co.id), 0.0
                ) AS revenue_per_table

            FROM cafe_order co
            LEFT JOIN res_company comp ON comp.id = 1
            LEFT JOIN cafe_table ct ON ct.id = co.table_id

            WHERE co.create_date IS NOT NULL
        )""" % (self._table,))