# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ChequeLayout(models.Model):
    _name = 'cheque.layout'
    _description = 'Cheque Print Layout'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    reference_image = fields.Binary(
        string="Reference Cheque Image", attachment=True,
        help="Used only to visually position fields in the designer. "
             "This image is never included in the printed output.")
    reference_image_filename = fields.Char()

    cheque_width_mm = fields.Float(string="Cheque Width (mm)", default=210.0, required=True)
    cheque_height_mm = fields.Float(string="Cheque Height (mm)", default=75.0, required=True)

    paperformat_id = fields.Many2one(
        'report.paperformat', string="Paper Format", readonly=True, copy=False)

    field_ids = fields.One2many('cheque.layout.field', 'layout_id', string="Fields", copy=True)


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_paperformat()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('cheque_width_mm', 'cheque_height_mm', 'name')):
            self._sync_paperformat()
        return res

    def action_sync_paperformat(self):
        self._sync_paperformat()

    def _sync_paperformat(self):
        for rec in self:
            vals = {
                'name': f'Cheque Format - {rec.name or rec.id}',
                # format='A4' ignores page_width/page_height entirely -
                # Odoo only honors custom dimensions when format='custom'.
                # This was the actual cause of cheques printing as
                # standard portrait A4 instead of the cheque's own size.
                'format': 'custom',
                'page_width': rec.cheque_width_mm,
                'page_height': rec.cheque_height_mm,
                # Do NOT switch this to 'Landscape' even though the
                # cheque is wider than it is tall: page_width/page_height
                # already fully describe the page shape once format is
                # 'custom'. 'orientation' would apply an *additional*
                # rotation on top of those explicit dimensions, which
                # would rotate an already-landscape-shaped page again and
                # produce the wrong result. This mirrors Odoo's own
                # built-in "French Bank Check" paperformat (page_width=175
                # > page_height=80, orientation=Portrait) - the reference
                # example for exactly this use case.
                'orientation': 'Portrait',
                'margin_top': 0,
                'margin_bottom': 0,
                'margin_left': 0,
                'margin_right': 0,
                'header_spacing': 0,
                'dpi': 90,
            }
            if rec.paperformat_id:
                rec.paperformat_id.write(vals)
            else:
                rec.paperformat_id = self.env['report.paperformat'].create(vals)