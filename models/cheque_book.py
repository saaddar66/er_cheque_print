# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Book'
    _order = 'id desc'

    name = fields.Char(required=True, copy=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank Account")
    layout_id = fields.Many2one(
        'cheque.layout', string="Cheque Layout", required=True)

    leaf_digit_length = fields.Integer(
        string="Leaf Number Digits", default=7,
        help="Cheque numbers are zero-padded to this length, e.g. 0001234.")
    leaf_from = fields.Integer(string="Leaf From", required=True)
    total_leaves = fields.Integer(string="Total Leaves", default=25, required=True)
    leaf_to = fields.Integer(
        string="Leaf To", compute='_compute_leaf_to', store=True, readonly=False)

    leaf_ids = fields.One2many('cheque.leaf', 'cheque_book_id', string="Leaves")
    leaf_count = fields.Integer(compute='_compute_leaf_count')
    used_leaf_count = fields.Integer(compute='_compute_leaf_count')
    unused_leaf_count = fields.Integer(compute='_compute_leaf_count')

    state = fields.Selection(
        [('active', 'Active'), ('exhausted', 'Exhausted'), ('closed', 'Closed')],
        default='active', required=True)

    @api.depends('leaf_from', 'total_leaves')
    def _compute_leaf_to(self):
        for rec in self:
            rec.leaf_to = (rec.leaf_from + rec.total_leaves - 1) if rec.leaf_from and rec.total_leaves else rec.leaf_from

    @api.depends('leaf_ids.state')
    def _compute_leaf_count(self):
        for rec in self:
            rec.leaf_count = len(rec.leaf_ids)
            rec.used_leaf_count = len(rec.leaf_ids.filtered(lambda l: l.state == 'used'))
            rec.unused_leaf_count = len(rec.leaf_ids.filtered(lambda l: l.state == 'unused'))

    @api.constrains('leaf_from', 'total_leaves')
    def _check_leaf_range(self):
        for rec in self:
            if rec.leaf_from <= 0:
                raise ValidationError("Leaf From must be a positive number.")
            if rec.total_leaves <= 0:
                raise ValidationError("Total Leaves must be greater than zero.")

    @api.model_create_multi
    def create(self, vals_list):
        books = super().create(vals_list)
        for book in books:
            book._generate_leaves()
        return books

    def _generate_leaves(self):
        self.ensure_one()
        if self.leaf_ids:
            return
        leaves = [{
            'cheque_book_id': self.id,
            'number': str(number).zfill(self.leaf_digit_length or 0),
            'state': 'unused',
        } for number in range(self.leaf_from, self.leaf_to + 1)]
        self.env['cheque.leaf'].create(leaves)

    def get_next_leaf(self):
        """Return the next unused leaf for this book, or raise if none remain."""
        self.ensure_one()
        leaf = self.leaf_ids.filtered(lambda l: l.state == 'unused').sorted('number')[:1]
        if not leaf:
            self.state = 'exhausted'
            raise ValidationError(f"No unused cheque leaves remain in {self.name}.")
        return leaf