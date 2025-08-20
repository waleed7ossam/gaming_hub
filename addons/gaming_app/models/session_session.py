# coding: utf-8

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SessionSession(models.Model):
    _name = 'session.session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sessions'
    _rec_name = 'ref'
    _order = 'state DESC'

    ref = fields.Char(default='New', readonly=True, copy=False)
    partner_id = fields.Many2one(comodel_name='res.partner', required=True)
    room_id = fields.Many2one(comodel_name='room.name', domain="[('id', 'not in', unavailable_rooms_ids)]")
    console_id = fields.Many2one(comodel_name='console.number', domain="[('id', 'not in', unavailable_consoles_ids)]")
    table_id = fields.Many2one(comodel_name='table.tables', domain="[('id', 'not in', unavailable_table_ids)]")
    room_type_id = fields.Many2one(related='room_id.type_id')
    console_type_id = fields.Many2one(related='console_id.type_id')
    table_type_id = fields.Many2one(related='table_id.type_id')
    move_ids = fields.One2many(comodel_name='account.move', inverse_name='session_id')
    session_type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ], default="public")
    individual_type = fields.Selection([
        ('console', 'Console'),
        ('table', 'Table'),
    ], default=None)
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
    starting_time = fields.Datetime(readonly=True)
    ending_time = fields.Datetime(readonly=True)
    spent_time = fields.Float(compute='_compute_spent_time')
    time_price = fields.Monetary(compute='_compute_time_price', currency_field='currency_id', store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency')
    session_line_ids = fields.One2many(comodel_name='session.session.line', inverse_name='session_id')
    total = fields.Monetary(compute='_compute_total', currency_field='currency_id')
    unavailable_rooms_ids = fields.Many2many(comodel_name='room.name', compute='_compute_room_console_table_domain',
                                             store=True)
    unavailable_consoles_ids = fields.Many2many(comodel_name='console.number',
                                                compute='_compute_room_console_table_domain', store=True)
    unavailable_table_ids = fields.Many2many(comodel_name='table.tables', compute='_compute_room_console_table_domain',
                                             store=True)

    @api.constrains('starting_time', 'ending_time')
    def _check_negative_time(self):
        for rec in self:
            if rec.starting_time and rec.ending_time:
                if rec.starting_time >= rec.ending_time:
                    raise ValidationError("Starting Time Can't be later than Or the same of Ending Time")

    @api.ondelete(at_uninstall=True)
    def _unlink_if_available(self):
        if any(rec.state in ('running', 'finished') for rec in self):
            raise ValidationError("This record isn't in Available state. You Can't delete it.")

    @api.onchange('session_type', 'individual_type')
    def _onchange_session_individual(self):
        self.room_id = None
        self.console_id = None
        self.table_id = None

    def _check_reservation_time(self):
        sessions = self.env['session.session'].search([('state', '=', 'available'), ('starting_time', '<=', fields.Datetime.now())])
        if sessions:
            for session in sessions:
                session.state = 'running'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['starting_time'] = fields.Datetime.now()
            if vals['session_type'] == 'private':
                vals['ref'] = self.env['ir.sequence'].next_by_code('seq_room_session', sequence_date=self.starting_time)
            if vals['session_type'] == 'public':
                if vals['individual_type'] == 'console':
                    vals['ref'] = self.env['ir.sequence'].next_by_code('seq_console_session',
                                                                       sequence_date=self.starting_time)
                if vals['individual_type'] == 'table':
                    vals['ref'] = self.env['ir.sequence'].next_by_code('seq_table_session',
                                                                       sequence_date=self.starting_time)
            vals['state'] = 'running'

        return super().create(vals_list)

    @api.depends('move_ids.status_in_payment')
    def _compute_payment_status(self):
        for session in self:
            move = session.move_ids.search([('session_id', '=', session.id), ('move_type', '=', 'out_invoice')]).mapped(
                'status_in_payment')
            if move:
                session.payment_status = move[0]
            else:
                session.payment_status = None

    @api.depends('room_id', 'console_id', 'table_id')
    def _compute_room_console_table_domain(self):
        for session in self:
            rooms = self.env['session.session'].search(
                [('session_type', '=', 'private'), ('state', 'in', ('available', 'running'))])
            consoles = self.env['session.session'].search(
                [('session_type', '=', 'public'), ('individual_type', '=', 'console'),
                 ('state', 'in', ('available', 'running'))])
            tables = self.env['session.session'].search(
                [('session_type', '=', 'public'), ('individual_type', '=', 'table'),
                 ('state', 'in', ('available', 'running'))])
            if session.session_type == 'private':
                session.unavailable_rooms_ids = rooms.mapped('room_id')
            elif session.session_type == 'public':
                if session.individual_type == 'console':
                    session.unavailable_consoles_ids = consoles.mapped('console_id')
                elif session.individual_type == 'table':
                    session.unavailable_table_ids = tables.mapped('table_id')

    @api.depends('session_line_ids', 'session_line_ids.discount_included', 'session_line_ids.discount',
                 'session_line_ids.product_uom_qty', 'time_price', 'spent_time')
    def _compute_total(self):
        for session in self:
            session.total = sum(session.session_line_ids.mapped('discount_included')) + session.time_price

    @api.depends('starting_time', 'ending_time')
    def _compute_spent_time(self):
        for rec in self:
            if rec.starting_time and rec.ending_time:
                delta = rec.ending_time - rec.starting_time
                rec.spent_time = delta.total_seconds() / 60.0
            else:
                rec.spent_time = 0.0

    @api.depends('spent_time', 'room_type_id', 'console_type_id', 'table_type_id', 'room_type_id.price_per_hour',
                 'console_type_id.price_per_hour', 'table_type_id.price_per_hour', 'starting_time', 'ending_time',
                 'session_type')
    def _compute_time_price(self):
        for rec in self:
            price = 0.0
            if rec.session_type == 'private':
                if rec.spent_time and rec.room_type_id:
                    price = (rec.spent_time / 60) * rec.room_type_id.price_per_hour
            elif rec.session_type == 'public':
                if rec.spent_time and rec.console_type_id:
                    price = (rec.spent_time / 60) * rec.console_type_id.price_per_hour
                if rec.spent_time and rec.table_type_id:
                    price = (rec.spent_time / 60) * rec.table_type_id.price_per_hour
            rec.time_price = price

    def _compute_currency(self):
        for session in self:
            session.currency_id = self.env.company.currency_id

    def action_running(self):
        self.state = 'running'

    def action_finished(self):
        self.ending_time = fields.Datetime.now()
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
                'default_session_id': self.id,
                'default_is_partially' : bool(self.payment_status == 'partial'),
                'default_payment_way' : 'partially_paid' if self.payment_status == 'partial' else False
            }
        }

    def action_view_invoice(self):
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', self.move_ids.ids), ('move_type', '=', 'out_invoice')]
        return action


class SessionSessionLine(models.Model):
    _name = 'session.session.line'

    session_id = fields.Many2one(comodel_name='session.session')
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
