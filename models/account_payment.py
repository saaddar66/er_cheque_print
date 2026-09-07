from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cheque_leaf_id = fields.Many2one('cheque.leaf', string="Printed Cheque Leaf", copy=False)
    is_ac_payable = fields.Boolean(string="A/C Payee", )
    employee_id = fields.Many2one('hr.employee', string="Employee", store=True, readonly=False)

    def get_cheque_ac_payable(self, fallback=True):
        self.ensure_one()

        employee_code = (
            self.employee_id.x_studio_code or ''
        ).strip().upper() if self.employee_id else ''

        if employee_code.endswith('A'):
            return True
        elif employee_code.endswith('B'):
            return False

        return fallback

    def action_open_cheque_print_wizard(self):
        self.ensure_one()
        return {
            'name': "Print Cheque",
            'type': 'ir.actions.act_window',
            'res_model': 'cheque.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_id': self.id},
        }


    def action_open_bulk_cheque_print_wizard(self):
        if not self:
            return False

        payments = self.filtered(
            lambda payment: (
                payment.state == 'paid'
                and not payment.cheque_leaf_id
            )
        )

        if not payments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "No Eligible Payments",
                    'message': (
                        "No posted payments without "
                        "printed cheque leaves were found."
                    ),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        return {
            'name': "Bulk Print Cheques",
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.cheque.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_ids': [
                    (6, 0, payments.ids)
                ],
            },
        }