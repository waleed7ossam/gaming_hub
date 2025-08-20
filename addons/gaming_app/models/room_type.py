# coding: utf-8

from odoo import models, fields, api


class RoomType(models.Model):
    _name = 'room.type'
    _description = 'Room Type'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(required=True)
    price_per_hour = fields.Float(string='Price/H', required=True)
