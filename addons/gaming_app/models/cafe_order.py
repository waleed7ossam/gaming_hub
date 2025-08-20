# coding: utf-8

from odoo import models, fields, api


class CafeOrder(models.Model):
    _name = 'cafe.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'CafeOrder'
    _rec_name = 'ref'

    ref = fields.Char(default='New', readonly=True, copy=False)
    partner_id = fields.Many2one(comodel_name='res.partner', required=True)
    table_id = fields.Many2one(comodel_name='cafe.table', required=True, domain="[('id', 'not in', unavailable_table_ids)]")
    cafe_line_ids = fields.One2many(comodel_name='cafe.order.line', inverse_name='order_id')
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency')
    total = fields.Monetary(compute='_compute_total', currency_field='currency_id')
    move_ids = fields.One2many(comodel_name='account.move', inverse_name='cafe_id')
    state = fields.Selection([
        ('available', 'Available'),
        ('running', 'Running'),
        ('finished', 'Finished'),
    ], default="available", tracking=True)
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
    ], compute='_compute_payment_status')
    unavailable_table_ids = fields.Many2many(comodel_name='cafe.table', compute='_compute_table_domain', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('seq_cafe_order')

        return super().create(vals_list)

    def _compute_currency(self):
        for session in self:
            session.currency_id = self.env.company.currency_id

    @api.depends('cafe_line_ids', 'cafe_line_ids.discount_included', 'cafe_line_ids.discount',
                 'cafe_line_ids.product_uom_qty')
    def _compute_total(self):
        for session in self:
            session.total = sum(session.cafe_line_ids.mapped('discount_included'))

    @api.depends('table_id')
    def _compute_table_domain(self):
        for order in self:
            tables = self.env['cafe.order'].search([('state', 'in', ('available', 'running'))])
            order.unavailable_table_ids = tables.mapped('table_id')


    @api.depends('move_ids.status_in_payment')
    def _compute_payment_status(self):
        for order in self:
            move = order.move_ids.search([('cafe_id', '=', order.id), ('move_type', '=', 'out_invoice')]).mapped('status_in_payment')
            if move:
                order.payment_status = move[0]
            else:
                order.payment_status = None

    def action_running(self):
        self.state = 'running'

    def action_finished(self):
        self.state = 'finished'

    def action_create_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'res_model': 'payment.workflow.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('gaming_app.payment_workflow_wizard_form_view').id,
            'target': 'new',
            'context': {
                'default_cafe_id': self.id,
                'default_is_partially': bool(self.payment_status == 'partial'),
                'default_payment_way': 'partially_paid' if self.payment_status == 'partial' else False
            }
        }

    def action_view_invoice(self):
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', self.move_ids.ids), ('move_type', '=', 'out_invoice')]
        return action


class CafeOrderLine(models.Model):
    _name = 'cafe.order.line'

    order_id = fields.Many2one(comodel_name='cafe.order')
    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True
    )

    product_uom_qty = fields.Float(
        string="Quantity",
        digits='Product Unit of Measure',
        default=1.0,
        store=True, readonly=False, required=True, precompute=True)

    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, readonly=False, required=True, precompute=True)

    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])

    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")

    discount_excluded = fields.Float(
        string="Disc. excl.",
        compute='_compute_disc_excl',
        store=True, precompute=True)

    discount_included = fields.Float(
        string="Disc. incl.",
        compute='_compute_disc_incl',
        store=True, precompute=True)

    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        store=True, readonly=False, precompute=True)

    @api.depends('product_uom_qty', 'discount', 'price_unit')
    def _compute_disc_excl(self):
        for line in self:
            line.discount_excluded = line.product_uom_qty * line.price_unit

    @api.depends('product_uom_qty', 'discount', 'price_unit')
    def _compute_disc_incl(self):
        for line in self:
            line.discount_included = (line.product_uom_qty * line.price_unit) - (
                    (line.product_uom_qty * line.price_unit) * line.discount / 100)

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line.product_id.lst_price

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id
