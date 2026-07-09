# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class ChequeLeaf(models.Model):
    _name = 'cheque.leaf'
    _description = 'Cheque Leaf'
    _order = 'number'
    _rec_name = 'number'

    cheque_book_id = fields.Many2one('cheque.book', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='cheque_book_id.company_id', store=True)
    number = fields.Char(required=True)

    state = fields.Selection([
        ('unused', 'Unused'),
        ('used', 'Used'),
        ('voided', 'Voided'),
        ('cancelled', 'Cancelled'),
    ], default='unused', required=True)

    payment_id = fields.Many2one('account.payment', string="Payment", readonly=True, copy=False)

    # Snapshot fields are frozen at print time, independent of later edits
    # to the related payment, so printed-cheque history never silently
    # changes underneath you.
    payee_name_snapshot = fields.Char(string="Payee Name", readonly=True)
    amount_snapshot = fields.Monetary(string="Amount", readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    date_snapshot = fields.Date(string="Date", readonly=True)
    amount_words_snapshot = fields.Char(string="Amount in Words", readonly=True)

    # Extended snapshot fields written by the print wizard
    memo_snapshot = fields.Char(string="Memo", readonly=True)
    is_ac_payable_snapshot = fields.Boolean(string="A/C Payee", readonly=True)
    bank_name = fields.Char(string="Bank Name", readonly=True)
    bank_account_number = fields.Char(string="Bank Account Number", readonly=True)
    bank_email = fields.Char(string="Bank Email", readonly=True)
    bank_address = fields.Char(string="Bank Address", readonly=True)

    printed_date = fields.Datetime(readonly=True)
    void_reason = fields.Char()

    _sql_constraints = [
        ('uniq_number_per_book', 'unique(cheque_book_id, number)',
         'Cheque numbers must be unique within a cheque book.'),
    ]

    def action_void(self):
        for rec in self:
            if not rec.void_reason:
                raise ValidationError("Please provide a Void Reason before voiding the cheque.")
            # Allow voiding cheques in any state (including 'used')
            # if rec.state == 'used':
            #     raise ValidationError(
            #         "A used cheque leaf cannot be voided directly; "
            #         "cancel or reverse the related payment instead.")
            rec.state = 'voided'

    def action_reset_to_unused(self):
        for rec in self:
            rec.write({
                'state': 'unused',
                'payment_id': False,
                'payee_name_snapshot': False,
                'amount_snapshot': 0.0,
                'date_snapshot': False,
                'amount_words_snapshot': False,
                'printed_date': False,
            })

    def mark_used(self, payment, payee_name, amount, currency, date, amount_words):
        self.ensure_one()
        if self.state != 'unused':
            raise ValidationError(
                f"Cheque leaf {self.number} is not available (current state: {self.state}).")
        self.write({
            'state': 'used',
            'payment_id': payment.id if payment else False,
            'payee_name_snapshot': payee_name,
            'amount_snapshot': amount,
            'currency_id': currency.id if currency else False,
            'date_snapshot': date,
            'amount_words_snapshot': amount_words,
            'printed_date': fields.Datetime.now(),
        })