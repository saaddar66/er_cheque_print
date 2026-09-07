# -*- coding: utf-8 -*-
from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_jv_cheque_wizard(self):
        self.ensure_one()
        return {
            'name': 'Print Cheque',
            'type': 'ir.actions.act_window',
            'res_model': 'jv.cheque.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            },
        }
