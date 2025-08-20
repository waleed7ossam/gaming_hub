# coding: utf-8

from odoo import models, fields


class RoomName(models.Model):
    _name = 'room.name'
    _description = 'Room Name'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(required=True)
    type_id = fields.Many2one(comodel_name='room.type', required=True)
