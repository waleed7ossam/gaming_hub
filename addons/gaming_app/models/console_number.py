# coding: utf-8

from odoo import models, fields


class ConsoleNumber(models.Model):
    _name = 'console.number'
    _description = 'Console Number'
    _rec_name = 'device_num'

    sequence = fields.Integer('Sequence', default=1)
    device_num = fields.Char(required=True)
    type_id = fields.Many2one(comodel_name='console.type', required=True)
