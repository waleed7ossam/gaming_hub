from odoo import models, fields, tools


class SessionReport(models.Model):
    _name = "session.report"
    _description = "Session Analysis Report"
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

    # Session Information
    session_id = fields.Many2one('session.session', string='Session', readonly=True)
    ref = fields.Char('Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)

    # Session Classification
    session_type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ], string='Session Type', readonly=True)

    individual_type = fields.Selection([
        ('console', 'Console'),
        ('table', 'Table'),
    ], string='Individual Type', readonly=True)

    state = fields.Selection([
        ('reserved', 'Reserved'),
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
    room_id = fields.Many2one('room.name', string='Room', readonly=True)
    console_id = fields.Many2one('console.number', string='Console', readonly=True)
    table_id = fields.Many2one('table.tables', string='Table', readonly=True)

    # Resource Types
    room_type_id = fields.Many2one('room.type', string='Room Type', readonly=True)
    console_type_id = fields.Many2one('console.type', string='Console Type', readonly=True)
    table_type_id = fields.Many2one('table.type', string='Table Type', readonly=True)

    # Time Analysis
    starting_time = fields.Datetime('Starting Time', readonly=True)
    ending_time = fields.Datetime('Ending Time', readonly=True)
    spent_time = fields.Float('Spent Time (Minutes)', readonly=True)
    spent_hours = fields.Float('Spent Time (Hours)', readonly=True)

    # Financial Analysis
    time_price = fields.Monetary('Time Price', readonly=True, currency_field='currency_id')
    products_total = fields.Monetary('Products Total', readonly=True, currency_field='currency_id')
    total = fields.Monetary('Total Amount', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # Aggregated Fields for Pivot Analysis
    session_count = fields.Integer('Sessions Count', readonly=True)
    avg_session_duration = fields.Float('Avg Session Duration (Hours)', readonly=True)
    total_revenue = fields.Monetary('Total Revenue', readonly=True, currency_field='currency_id')

    # Performance Indicators
    resource_utilization = fields.Float('Resource Utilization %', readonly=True)
    revenue_per_hour = fields.Monetary('Revenue per Hour', readonly=True, currency_field='currency_id')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT 
                -- Primary Key
                row_number() OVER () AS id,

                -- Date Analysis
                DATE(s.starting_time) AS date,
                to_char(s.starting_time, 'MM') AS month,
                to_char(s.starting_time, 'YYYY') AS year,
                'Q' || to_char(s.starting_time, 'Q') AS quarter,

                -- Session Information
                s.id AS session_id,
                s.ref AS ref,
                s.partner_id AS partner_id,

                -- Session Classification
                s.session_type AS session_type,
                s.individual_type AS individual_type,
                s.state AS state,

                -- Payment Status (from related invoices)
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
                     WHERE am.session_id = s.id 
                       AND am.move_type = 'out_invoice' 
                     ORDER BY am.create_date DESC
                     LIMIT 1),
                    'not_paid'
                ) AS payment_status,

                -- Resources
                s.room_id AS room_id,
                s.console_id AS console_id,
                s.table_id AS table_id,

                -- Resource Types
                CASE 
                    WHEN s.session_type = 'private' THEN r.type_id
                    ELSE NULL
                END AS room_type_id,

                CASE 
                    WHEN s.session_type = 'public' AND s.individual_type = 'console' THEN c.type_id
                    ELSE NULL
                END AS console_type_id,

                CASE 
                    WHEN s.session_type = 'public' AND s.individual_type = 'table' THEN t.type_id
                    ELSE NULL
                END AS table_type_id,

                -- Time Analysis
                s.starting_time AS starting_time,
                s.ending_time AS ending_time,

                -- Spent Time Calculation
                CASE 
                    WHEN s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 60.0
                    ELSE 0.0
                END AS spent_time,

                CASE 
                    WHEN s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0
                    ELSE 0.0
                END AS spent_hours,

                -- Time Price Calculation
                CASE 
                    WHEN s.session_type = 'private' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(rt.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'console' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(ct.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'table' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(tt.price_per_hour, 0)
                    ELSE 0.0
                END AS time_price,

                -- Products Total
                COALESCE(
                    (SELECT SUM(ssl.discount_included)
                     FROM session_session_line ssl
                     WHERE ssl.session_id = s.id), 0.0
                ) AS products_total,

                -- Total Amount
                CASE 
                    WHEN s.session_type = 'private' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(rt.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'console' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(ct.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'table' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(tt.price_per_hour, 0)
                    ELSE 0.0
                END + COALESCE(
                    (SELECT SUM(ssl.discount_included)
                     FROM session_session_line ssl
                     WHERE ssl.session_id = s.id), 0.0
                ) AS total,

                -- Currency
                comp.currency_id AS currency_id,

                -- Aggregated Fields
                1 AS session_count,

                CASE 
                    WHEN s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0
                    ELSE 0.0
                END AS avg_session_duration,

                CASE 
                    WHEN s.session_type = 'private' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(rt.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'console' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(ct.price_per_hour, 0)
                    WHEN s.session_type = 'public' AND s.individual_type = 'table' AND s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(tt.price_per_hour, 0)
                    ELSE 0.0
                END + COALESCE(
                    (SELECT SUM(ssl.discount_included)
                     FROM session_session_line ssl
                     WHERE ssl.session_id = s.id), 0.0
                ) AS total_revenue,

                -- Resource Utilization (simplified calculation)
                CASE 
                    WHEN s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL THEN
                        LEAST(100.0, (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * 100.0 / 24.0)
                    ELSE 0.0
                END AS resource_utilization,

                -- Revenue per Hour
                CASE 
                    WHEN s.starting_time IS NOT NULL AND s.ending_time IS NOT NULL AND 
                         EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) > 0 THEN
                        (CASE 
                            WHEN s.session_type = 'private' THEN
                                (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(rt.price_per_hour, 0)
                            WHEN s.session_type = 'public' AND s.individual_type = 'console' THEN
                                (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(ct.price_per_hour, 0)
                            WHEN s.session_type = 'public' AND s.individual_type = 'table' THEN
                                (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0) * COALESCE(tt.price_per_hour, 0)
                            ELSE 0.0
                        END + COALESCE(
                            (SELECT SUM(ssl.discount_included)
                             FROM session_session_line ssl
                             WHERE ssl.session_id = s.id), 0.0
                        )) / (EXTRACT(EPOCH FROM (s.ending_time - s.starting_time)) / 3600.0)
                    ELSE 0.0
                END AS revenue_per_hour

            FROM session_session s
            LEFT JOIN res_company comp ON comp.id = 1
            LEFT JOIN room_name r ON r.id = s.room_id
            LEFT JOIN room_type rt ON rt.id = r.type_id
            LEFT JOIN console_number c ON c.id = s.console_id
            LEFT JOIN console_type ct ON ct.id = c.type_id
            LEFT JOIN table_tables t ON t.id = s.table_id
            LEFT JOIN table_type tt ON tt.id = t.type_id

            WHERE s.starting_time IS NOT NULL
        )""" % (self._table,))
