# -*- coding: utf-8 -*-
from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_internal_transfer_journal = fields.Boolean(compute='_compute_is_internal_transfer_journal')

    @api.depends('journal_id.name')
    def _compute_is_internal_transfer_journal(self):
        for move in self:
            move.is_internal_transfer_journal = (move.journal_id.name == 'Internal Transfer')
    
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
