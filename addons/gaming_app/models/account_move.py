# coding: utf-8

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    session_id = fields.Many2one(comodel_name='session.session')
    cafe_id = fields.Many2one(comodel_name='cafe.order')
