# coding: utf-8

from odoo import models, fields


class TableTables(models.Model):
    _name = 'table.tables'
    _description = 'Tables'
    _rec_name = 'table_num'

    sequence = fields.Integer('Sequence', default=1)
    table_num = fields.Char(required=True)
    type_id = fields.Many2one(comodel_name='table.type', required=True)
