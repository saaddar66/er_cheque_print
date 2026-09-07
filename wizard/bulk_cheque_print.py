from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BulkChequePrintWizard(models.TransientModel):
    _name = 'bulk.cheque.print.wizard'
    _description = 'Bulk Cheque Print Wizard'

    payment_ids = fields.Many2many(
        'account.payment',
        string='Payments',
        required=True,
        readonly=True,
    )

    layout_id = fields.Many2one(
        'cheque.layout',
        string='Cheque Layout',
        required=True,
    )

    cheque_book_id = fields.Many2one(
        'cheque.book',
        string='Cheque Book',
        required=True,
        domain="""
            [
                ('layout_id', '=', layout_id),
                ('state', '=', 'active')
            ]
        """,
    )

    cheque_date = fields.Date(
        string='Cheque Date',
        required=True,
        default=fields.Date.context_today,
    )

    memo = fields.Char(
        string='Memo / Note',
    )

    is_ac_payable = fields.Boolean(
        string='A/C Payee',
        default=True,
    )

    available_leaf_count = fields.Integer(
        string='Available Cheques',
        compute='_compute_available_leaf_count',
    )

    payment_count = fields.Integer(
        string='Number of Payments',
        compute='_compute_payment_count',
    )

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for wizard in self:
            wizard.payment_count = len(
                wizard.payment_ids
            )

    @api.depends('cheque_book_id')
    def _compute_available_leaf_count(self):
        for wizard in self:

            if wizard.cheque_book_id:

                wizard.available_leaf_count = (
                    self.env['cheque.leaf']
                    .search_count([
                        (
                            'cheque_book_id',
                            '=',
                            wizard.cheque_book_id.id,
                        ),
                        (
                            'state',
                            '=',
                            'unused',
                        ),
                    ])
                )

            else:

                wizard.available_leaf_count = 0

    @api.onchange('layout_id')
    def _onchange_layout_id(self):

        self.cheque_book_id = False

        if self.layout_id:

            cheque_book = (
                self.env['cheque.book']
                .search([
                    (
                        'layout_id',
                        '=',
                        self.layout_id.id,
                    ),
                    (
                        'state',
                        '=',
                        'active',
                    ),
                ], limit=1)
            )

            self.cheque_book_id = cheque_book

    def action_print_bulk_cheques(self):
        self.ensure_one()

        payments = self.payment_ids.filtered(
            lambda payment: (
                payment.state == 'paid'
                and not payment.cheque_leaf_id
            )
        )

        if not payments:

            raise UserError(
                _(
                    "There are no eligible payments "
                    "available for cheque printing."
                )
            )

        unused_leaves = (
            self.env['cheque.leaf']
            .search([
                (
                    'cheque_book_id',
                    '=',
                    self.cheque_book_id.id,
                ),
                (
                    'state',
                    '=',
                    'unused',
                ),
            ], order='id')
        )

        if len(unused_leaves) < len(payments):

            raise UserError(
                _(
                    "The selected cheque book does "
                    "not have enough unused cheque leaves.\n\n"
                    "Payments: %(payments)s\n"
                    "Available cheque leaves: %(leaves)s"
                )
                % {
                    'payments': len(payments),
                    'leaves': len(unused_leaves),
                }
            )

        cheque_leaves = unused_leaves[
            :len(payments)
        ]

        printed_leaves = (
            self.env['cheque.leaf']
        )

        for payment, leaf in zip(
            payments,
            cheque_leaves,
        ):

            effective_is_ac_payable = payment.get_cheque_ac_payable(
                fallback=True,
            )

            withholding_total = sum(
                self.env[
                    'account.payment.withholding.line'
                ]
                .search([
                    (
                        'payment_id',
                        '=',
                        payment.id,
                    ),
                ])
                .mapped('amount')
            )

            cheque_amount = round(
                payment.amount
                - withholding_total,
                2,
            )

            amount_words = (
                payment.currency_id
                .amount_to_text(
                    cheque_amount
                )
            )

            if (
                amount_words
                and not amount_words
                .lower()
                .endswith('only')
            ):

                amount_words += " Only"

            # Mark the cheque leaf as used.
            leaf.mark_used(
                payment=payment,
                payee_name=(
                    payment.partner_id.name
                ),
                amount=cheque_amount,
                currency=(
                    payment.currency_id
                ),
                date=self.cheque_date,
                amount_words=amount_words,
            )

            leaf.write({
                'memo_snapshot': self.memo or '',
                'is_ac_payable_snapshot': effective_is_ac_payable,
            })

            payment.write({
                'cheque_leaf_id': leaf.id,
                'is_ac_payable': effective_is_ac_payable,
            })

            printed_leaves |= leaf

        report = self.env.ref(
            'er_cheque_print.'
            'action_report_cheque_print'
        )

        if self.layout_id.paperformat_id:

            report.paperformat_id = (
                self.layout_id.paperformat_id
            )

        return report.report_action(
            printed_leaves
        )