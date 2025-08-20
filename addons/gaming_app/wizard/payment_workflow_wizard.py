from odoo import fields, models, api


class PaymentWorkflowWizard(models.TransientModel):
    _name = "payment.workflow.wizard"
    _description = "Payment Workflow Wizard"

    payment_way = fields.Selection([
        ('fully_paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('later_paid', 'Paid Later'),
    ], string='Payment Method')
    paid_amount = fields.Char()
    session_id = fields.Many2one(comodel_name='session.session')
    cafe_id = fields.Many2one(comodel_name='cafe.order')
    is_partially = fields.Boolean()

    def action_confirm(self):
        if self.payment_way == 'fully_paid':
            move = self.create_invoice()
            self.create_payment(move)

        elif self.payment_way == 'partially_paid':
            move = self.env['account.move'].search([('session_id', '=', self.session_id.id), ('move_type', '=', 'out_invoice'), ('session_id', '!=', False)]) or self.env['account.move'].search([('cafe_id', '=', self.cafe_id.id), ('move_type', '=', 'out_invoice'), ('cafe_id', '!=', False)])
            print(move)
            print('#' * 200)
            if move:
                self.create_payment(move)
            else:
                move = self.create_invoice()
                self.create_payment(move)

        elif self.payment_way == 'later_paid':
            self.create_invoice()

    def create_invoice(self):
        move = self.env['account.move'].create(self._prepare_invoice_values())
        move.action_post()
        return move

    def _prepare_invoice_values(self):
        type = self.session_id or self.cafe_id
        vals = {
            'partner_id': type.partner_id.id,
            'ref':type.ref,
            'invoice_date_due': type.create_date,
            'invoice_date': type.create_date,
            'currency_id': type.currency_id.id,
            'invoice_user_id': type.create_uid.id,
            'move_type': 'out_invoice',
            'session_id': self.session_id.id,
            'cafe_id': self.cafe_id.id,
            'invoice_line_ids': self._prepare_lines()
        }
        print(vals)
        print('#' * 200)
        return vals

    def _prepare_lines(self):
        type = self.session_id.session_line_ids or self.cafe_id.cafe_line_ids
        values = [(0, 0, self._prepare_lines_values(line)) for line in type]
        if type == self.session_id.session_line_ids:
            values.append((0, 0, {
                'product_id': self.session_id.env.ref('gaming_app.product_product_time_spent').id,
                'quantity': 1,
                'price_unit': self.session_id.time_price,
            }))
        return values

    def _prepare_lines_values(self, line):
        vals = {
            'product_id': line.product_id.id,
            'quantity': line.product_uom_qty,
            'price_unit': line.price_unit,
            'discount': line.discount,
        }

        return vals

    def create_payment(self, move):
        payment_register = self.env['account.payment.register'].with_context(active_model='account.move',active_ids=[move.id]).create(
            self._prepare_payment_vals(move))
        payment_register._create_payments()

    def _prepare_payment_vals(self, move):
        vals = {
            'amount': move.amount_total if self.payment_way == 'fully_paid' else self.paid_amount,
            'payment_date': fields.Date.context_today(self),
            'journal_id': self.env['account.journal'].search([('type', '=', 'cash')], limit=1).id,
            'payment_method_line_id': self.env['account.payment.method.line'].search(
                [('payment_method_id.payment_type', '=', 'inbound'), ('journal_id.type', '=', 'cash')
                 ], limit=1).id,
        }
        return vals

    @api.onchange('payment_way')
    def _onchange_paid_amount(self):
        session_invoice = self.env['account.move'].search([('session_id', '=', self.session_id.id), ('move_type', '=', 'entry'), ('session_id', '!=', False)])
        cafe_invoice = self.env['account.move'].search([('cafe_id', '=', self.cafe_id.id), ('move_type', '=', 'entry'), ('cafe_id', '!=', False)])
        if self.payment_way == 'partially_paid':
            if self.session_id:
                print('self.session_id.total', self.session_id.total)
                print("sum(session_invoice.mapped('amount_total'))", sum(session_invoice.mapped('amount_total')))
                self.paid_amount = round(self.session_id.total - sum(session_invoice.mapped('amount_total')), 2)
            if self.cafe_id:
                print('#' * 200)
                print('self.cafe_id.total', self.cafe_id.total)
                print('sum(cafe_invoice.mapped("amount_total"))', sum(cafe_invoice.mapped('amount_total')))
                self.paid_amount = round(self.cafe_id.total - sum(cafe_invoice.mapped('amount_total')), 2)
