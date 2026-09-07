from odoo import models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_open_validate_journal_entries(self):
        moves = self.mapped('move_id').filtered(
            lambda move: move.state == 'draft'
        )

        if not moves:
            raise UserError(
                _("No draft journal entries were found for the selected payslips.")
            )

        action = self.env.ref(
            'account.action_validate_account_move'
        ).read()[0]

        action['context'] = {
            'default_move_ids': [(6, 0, moves.ids)],
            'active_model': 'account.move',
            'active_ids': moves.ids,
        }

        return action