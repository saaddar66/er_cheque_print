from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cheque_leaf_id = fields.Many2one('cheque.leaf', string="Printed Cheque Leaf", copy=False)
    is_ac_payable = fields.Boolean(string="A/C Payee")

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