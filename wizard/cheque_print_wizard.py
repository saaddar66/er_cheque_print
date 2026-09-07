# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ChequePrintWizard(models.TransientModel):
    _name = 'cheque.print.wizard'
    _description = 'Print Cheque Wizard'

    payment_id = fields.Many2one('account.payment', required=True, readonly=True)
    layout_id = fields.Many2one('cheque.layout', string="Cheque Layout", required=True)
    cheque_book_id = fields.Many2one(
        'cheque.book', string="Cheque Book", required=True,
        domain="[('layout_id', '=', layout_id), ('state', '=', 'active')]")
    leaf_id = fields.Many2one(
        'cheque.leaf', string="Cheque Number", required=True,
        domain="[('cheque_book_id', '=', cheque_book_id), ('state', '=', 'unused')]")

    payee_name = fields.Char(required=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    cheque_date = fields.Date(required=True, default=fields.Date.context_today)
    memo = fields.Char(string="Memo / Note")
    is_ac_payable = fields.Boolean(string="A/C Payee", default=True)

    amount_words = fields.Char(
        string="Amount in Words", compute='_compute_amount_words',
        readonly=False, store=True)

    # Bank fields auto-filled from cheque book's linked bank account
    bank_name = fields.Char(string="Bank Name", compute='_compute_bank_details', store=True, readonly=False)
    bank_account_number = fields.Char(string="Bank Account Number", compute='_compute_bank_details', store=True, readonly=False)
    bank_email = fields.Char(string="Bank Email", compute='_compute_bank_details', store=True, readonly=False)
    bank_address = fields.Char(string="Bank Address", compute='_compute_bank_details', store=True, readonly=False)

    @api.depends('cheque_book_id')
    def _compute_bank_details(self):
        for rec in self:
            if rec.cheque_book_id and rec.cheque_book_id.partner_bank_id:
                bank_acc = rec.cheque_book_id.partner_bank_id
                bank = bank_acc.bank_id

                rec.bank_account_number = bank_acc.acc_number or ''

                if bank:
                    rec.bank_name = bank.name or ''
                    rec.bank_email = bank.email if hasattr(bank, 'email') and bank.email else ''
                    _country = getattr(bank, 'country', None)
                    if hasattr(_country, 'name'):  # it's a Many2one recordset
                        country_name = _country.name or ''
                    elif isinstance(_country, str):  # it's a Char field
                        country_name = _country
                    else:  # fallback via partner
                        country_name = (
                            bank.partner_id.country_id.name
                            if bank.partner_id and bank.partner_id.country_id
                            else ''
                        )
                    address_parts = [bank.street, bank.street2, bank.city, country_name]
                    rec.bank_address = ", ".join([p for p in address_parts if p])
                else:
                    rec.bank_name = ''
                    rec.bank_email = ''
                    rec.bank_address = ''
            else:
                rec.bank_name = ''
                rec.bank_account_number = ''
                rec.bank_email = ''
                rec.bank_address = ''

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        payment_id = self.env.context.get('default_payment_id')
        if not payment_id:
            return res

        payment = self.env['account.payment'].browse(payment_id).exists()
        if not payment:
            return res

        # Sum all withholding amounts linked to this payment
        withholding_total = sum(
            self.env['account.payment.withholding.line'].search([
                ('payment_id', '=', payment.id)
            ]).mapped('amount')
        )

        res.update({
            'payee_name': payment.partner_id.name,
            'amount': round(payment.amount - withholding_total),
            'currency_id': payment.currency_id.id,
            'cheque_date': payment.date or fields.Date.context_today(self),
            'memo': payment.memo or '',
            'is_ac_payable': payment.get_cheque_ac_payable(fallback=True),
        })

        return res

    @api.onchange('layout_id')
    def _onchange_layout_id(self):
        self.cheque_book_id = False
        self.leaf_id = False
        if self.layout_id:
            book = self.env['cheque.book'].search([
                ('layout_id', '=', self.layout_id.id), ('state', '=', 'active'),
            ], limit=1)
            self.cheque_book_id = book

    @api.onchange('cheque_book_id')
    def _onchange_cheque_book_id(self):
        self.leaf_id = False
        if self.cheque_book_id:
            try:
                self.leaf_id = self.cheque_book_id.get_next_leaf()
            except UserError:
                pass

    @api.depends('amount', 'currency_id')
    def _compute_amount_words(self):
        for rec in self:
            if rec.amount:
                # Attempt to get a Rupee currency to use its built-in text formatting
                rupee_currency = self.env['res.currency'].search([('name', 'in', ['PKR', 'INR', 'NPR', 'LKR', 'MUR'])], limit=1)
                
                if rupee_currency:
                    amount_text = rupee_currency.amount_to_text(rec.amount)
                elif rec.currency_id:
                    # Fallback string replacement if no Rupee currency exists in the system
                    amount_text = rec.currency_id.amount_to_text(rec.amount)
                    amount_text = amount_text.replace('Dollars', 'Rupees').replace('Dollar', 'Rupee')
                    amount_text = amount_text.replace('Euros', 'Rupees').replace('Euro', 'Rupee')
                else:
                    amount_text = ""
                
                # Append 'Only' if it's not already there
                if amount_text and not amount_text.lower().endswith('only'):
                    amount_text += " Only"
                    
                rec.amount_words = amount_text
            else:
                rec.amount_words = ""

    def action_print(self):
        self.ensure_one()
        if not self.leaf_id:
            raise UserError("Please select a cheque number before printing.")

        effective_is_ac_payable = self.payment_id.get_cheque_ac_payable(
            fallback=self.is_ac_payable,
        )

        # 1. Freeze all cheque data onto the leaf (snapshot) so the QWeb
        #    template reads from doc.<field>_snapshot — no data= dict needed.
        self.leaf_id.mark_used(
            payment=self.payment_id,
            payee_name=self.payee_name,
            amount=self.amount,
            currency=self.currency_id,
            date=self.cheque_date,
            amount_words=self.amount_words,
        )

        # 2. Also store the extra wizard values (bank details, memo, flags)
        #    onto the leaf so the template can reach them via doc.*
        self.leaf_id.write({
            'bank_name': self.bank_name or '',
            'bank_account_number': self.bank_account_number or '',
            'bank_email': self.bank_email or '',
            'bank_address': self.bank_address or '',
            'memo_snapshot': self.memo or '',
            'is_ac_payable_snapshot': effective_is_ac_payable,
        })

        # 3. Write cheque leaf and A/C Payee flag back to the payment record
        self.payment_id.write({
            'cheque_leaf_id': self.leaf_id.id,
            'is_ac_payable': effective_is_ac_payable,
        })

        # 4. Set paper format from the layout (if configured)
        report = self.env.ref('er_cheque_print.action_report_cheque_print')
        if self.layout_id.paperformat_id:
            report.paperformat_id = self.layout_id.paperformat_id

        # 5. Pass ONLY the leaf record — no data= dict — so docs works in QWeb
        return report.report_action(self.leaf_id)