from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class HrPayslipBulkPayment(models.TransientModel):
    _name = 'hr.payslip.bulk.payment'
    _description = 'Bulk Payslip Payment'


    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Selected Payslips',
        readonly=True,
    )

    eligible_payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Eligible Payslips',
        compute='_compute_eligible_payslips',
    )

    skipped_payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Skipped Payslips',
        compute='_compute_eligible_payslips',
    )

    # =========================================================
    # PAYMENT FIELDS
    # =========================================================

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
    )

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        required=True,
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )

    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        string='Available Payment Methods',
        compute='_compute_available_payment_method_line_ids',
    )

    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
    )

    x_cheque_maturity_date = fields.Date(
        string='Cheque Maturity Date',
    )

    cheque_start_number = fields.Integer(
        string='Cheque Start Number',
        required=True,
    )

    cheque_end_number = fields.Integer(
        string='Cheque End Number',
        required=True,
    )

    other_particulars = fields.Char(
        string='Other Particulars',
    )

    # =========================================================
    # ELIGIBLE PAYSLIPS
    # =========================================================

    @api.depends(
        'payslip_ids',
        'payslip_ids.move_id',
        'payslip_ids.move_id.state',
    )
    def _compute_eligible_payslips(self):
        for wizard in self:

            eligible_payslips = wizard.payslip_ids.filtered(
                lambda slip: (
                    slip.move_id
                    and slip.move_id.state == 'posted'
                )
            )

            wizard.eligible_payslip_ids = eligible_payslips

            wizard.skipped_payslip_ids = (
                wizard.payslip_ids
                - eligible_payslips
            )

    # =========================================================
    # PAYMENT METHOD
    # =========================================================

    @api.depends('journal_id')
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:

            if wizard.journal_id:

                wizard.available_payment_method_line_ids = (
                    wizard.journal_id
                    ._get_available_payment_method_lines(
                        'outbound'
                    )
                )

            else:

                wizard.available_payment_method_line_ids = False

    @api.onchange('journal_id')
    def _onchange_journal_id(self):

        if not self.journal_id:

            self.payment_method_line_id = False
            return

        available_methods = (
            self.journal_id
            ._get_available_payment_method_lines(
                'outbound'
            )
        )

        if available_methods:

            self.payment_method_line_id = (
                available_methods[0]
            )

        else:

            self.payment_method_line_id = False

    # =========================================================
    # CHEQUE RANGE VALIDATION
    # =========================================================

    def _validate_cheque_range(self):
        self.ensure_one()

        if self.cheque_start_number <= 0:

            raise UserError(
                _(
                    "Cheque start number must be "
                    "greater than zero."
                )
            )

        if (
            self.cheque_end_number
            < self.cheque_start_number
        ):

            raise UserError(
                _(
                    "Cheque end number must be "
                    "greater than or equal to "
                    "cheque start number."
                )
            )

        payment_count = len(
            self.eligible_payslip_ids
        )

        required_end_number = (
            self.cheque_start_number
            + payment_count
            - 1
        )

        if (
            self.cheque_end_number
            < required_end_number
        ):

            raise UserError(
                _(
                    "The cheque range is insufficient.\n\n"
                    "Eligible payslips: %(count)s\n"
                    "Required cheque range: "
                    "%(start)s to %(end)s"
                )
                % {
                    'count': payment_count,
                    'start': (
                        self.cheque_start_number
                    ),
                    'end': (
                        required_end_number
                    ),
                }
            )

    # =========================================================
    # CREATE BULK PAYMENTS
    # =========================================================

    def action_create_bulk_payments(self):
        self.ensure_one()

        eligible_payslips = (
            self.eligible_payslip_ids
        )

        if not eligible_payslips:

            raise UserError(
                _(
                    "No payment was created because "
                    "none of the selected payslips "
                    "have posted journal entries."
                )
            )

        self._validate_cheque_range()

        created_payments = (
            self.env['account.payment']
        )

        failed_payslips = []

        cheque_number = (
            self.cheque_start_number
        )

        for payslip in eligible_payslips:
            try:
                # Use the same context as the normal Payslip Pay button.
                payment_action = payslip.with_context(
                    dont_redirect_to_payments=True,
                    hr_payroll_payment_register=True,
                ).action_register_payment()

                # Keep the complete context generated by Odoo.
                payment_context = dict(
                    payment_action.get('context', {})
                )

                # Add only the values from the bulk wizard.
                payment_context.update({
                    'default_journal_id': self.journal_id.id,

                    'default_payment_method_line_id':
                        self.payment_method_line_id.id,

                    'default_payment_date':
                        self.payment_date,

                    'default_x_cheque_maturity_date':
                        self.x_cheque_maturity_date,

                    'default_check_number':
                        str(cheque_number),

                    'default_other_particulars':
                        self.other_particulars,

                    # Same context as the original Payslip button.
                    'dont_redirect_to_payments': True,

                    'hr_payroll_payment_register': True,
                })

                # Initialize the standard Odoo payment wizard.
                payment_register_model = self.env[
                    'account.payment.register'
                ].with_context(
                    payment_context
                )

                # Get standard defaults.
                default_values = (
                    payment_register_model.default_get(
                        list(
                            payment_register_model._fields
                        )
                    )
                )

                # Create the standard payment register.
                payment_register = (
                    payment_register_model.create(
                        default_values
                    )
                )

                # Debug logs — temporarily keep these.
                _logger.info(
                    """
                    BULK PAYSLIP PAYMENT
                    Payslip: %s
                    Payment Type: %s
                    Amount: %s
                    Journal: %s
                    Payment Method: %s
                    Journal Lines: %s
                    """,
                    payslip.display_name,
                    payment_register.payment_type,
                    payment_register.amount,
                    payment_register.journal_id.display_name,
                    payment_register.payment_method_line_id.display_name,
                    payment_register.line_ids.ids,
                )

                # Use standard Odoo payment creation.
                payments = payment_register._create_payments()

                if payments:
                    # Link the employee from the payslip
                    payments.write({
                        'employee_id': payslip.employee_id.id,
                    })

                    created_payments |= payments
                    cheque_number += 1

                else:
                    failed_payslips.append(
                        payslip.display_name
                    )

            except Exception as error:
                failed_payslips.append(
                    "%s: %s"
                    % (
                        payslip.display_name,
                        str(error),
                    )
                )

        # =====================================================
        # NO PAYMENT CREATED
        # =====================================================

        if not created_payments:

            error_message = _(
                "No payments could be created."
            )

            if self.skipped_payslip_ids:

                skipped_names = ", ".join(
                    self.skipped_payslip_ids
                    .mapped(
                        'display_name'
                    )
                )

                error_message += (
                    "\n\n"
                    + _(
                        "Skipped because their journal "
                        "entries are not posted:\n%s"
                    )
                    % skipped_names
                )

            if failed_payslips:

                error_message += (
                    "\n\n"
                    + _(
                        "Payment errors:\n%s"
                    )
                    % "\n".join(
                        failed_payslips
                    )
                )

            raise UserError(
                error_message
            )

        # =====================================================
        # OPEN CREATED PAYMENTS
        # =====================================================

        return {
            'type':
                'ir.actions.act_window',

            'name':
                _('Bulk Payslip Payments'),

            'res_model':
                'account.payment',

            'view_mode':
                'list,form',

            'domain': [
                (
                    'id',
                    'in',
                    created_payments.ids,
                )
            ],

            'target':
                'current',
        }

