# coding: utf-8

from odoo import models, fields, api


class ConsoleType(models.Model):
    _name = 'console.type'
    _description = 'ConsoleType'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(required=True)
    price_per_hour = fields.Integer(string='Price/H', required=True)
