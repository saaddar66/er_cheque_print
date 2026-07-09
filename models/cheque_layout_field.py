# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

FIELD_KEYS = [
    ('payee_name', 'Payee Name'),
    ('payee_name_line1', 'Payee Name - Line 1'),
    ('payee_name_line2', 'Payee Name - Line 2'),
    ('amount_words_line1', 'Amount in Words - Line 1'),
    ('amount_words_line2', 'Amount in Words - Line 2'),
    ('amount_figures', 'Amount in Figures'),
    ('date', 'Date'),
    ('account_title', 'Account Title'),
    ('cheque_number', 'Cheque Number'),
    ('memo', 'Memo / Note'),
    ('bank_name', 'Bank Name'),
    ('bank_account_number', 'Bank Account Number'),
    ('bank_email', 'Bank Email'),
    ('bank_address', 'Bank Address'),
    ('account_payee', 'Account Payee Only'),
]


class ChequeLayoutField(models.Model):
    _name = 'cheque.layout.field'
    _description = 'Cheque Layout Field Position'
    _order = 'sequence, id'

    layout_id = fields.Many2one('cheque.layout', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    field_key = fields.Selection(FIELD_KEYS, required=True, default='payee_name')
    label = fields.Char(compute='_compute_label', store=True)

    pos_x = fields.Float(
        string="X Position (%)", default=10.0,
        help="Horizontal position as a percentage of cheque width (0-100), from the left edge.")
    pos_y = fields.Float(
        string="Y Position (%)", default=10.0,
        help="Vertical position as a percentage of cheque height (0-100), from the top edge.")

    font_size = fields.Integer(default=12)
    font_weight = fields.Selection(
        [('normal', 'Normal'), ('bold', 'Bold')], default='normal')
    letter_spacing = fields.Float(default=0.0, string="Letter Spacing (px)")
    text_align = fields.Selection(
        [('left', 'Left'), ('center', 'Center'), ('right', 'Right')], default='left')

    is_boxed = fields.Boolean(
        string="Boxed Digits",
        help="Render each character in its own evenly spaced box. "
             "Typically used for the Date field on local cheque formats.")
    box_count = fields.Integer(
        string="Box Count", default=8, help="Number of digit boxes, e.g. 8 for DDMMYYYY.")
    box_spacing = fields.Float(
        string="Box Spacing (%)", default=3.0,
        help="Horizontal gap between boxed digits, as a percentage of cheque width.")

    @api.depends('field_key')
    def _compute_label(self):
        selection = dict(self._fields['field_key'].selection)
        for rec in self:
            rec.label = selection.get(rec.field_key, '')

    @api.constrains('pos_x', 'pos_y')
    def _check_position_bounds(self):
        for rec in self:
            if not (0 <= rec.pos_x <= 100) or not (0 <= rec.pos_y <= 100):
                raise ValidationError("Field position (X/Y) must be between 0 and 100 percent.")

    @api.constrains('box_count')
    def _check_box_count(self):
        for rec in self:
            if rec.is_boxed and rec.box_count <= 0:
                raise ValidationError("Box Count must be greater than zero for boxed fields.")