# coding: utf-8

from odoo import models, fields


class CafeTable(models.Model):
    _name = 'cafe.table'
    _description = 'Cafe Table'
    _rec_name = 'table_num'

    sequence = fields.Integer('Sequence', default=1)
    table_num = fields.Char(required=True)
