{
    'name': 'Cheque Printing',
    'version': '1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Drag-and-drop cheque layout designer with leaf tracking, built for Pakistani banking conventions.',
    'description': """
Pakistan Cheque Printing
=========================
Design cheque layouts visually against an uploaded reference image, then print
real field values (never the image itself) onto blank cheques fed into the
printer. Includes:

* Drag-and-drop field positioning, stored as percentages of cheque size.
* Boxed-digit date support (D D / M M / Y Y Y Y), common on local cheques.
* Lakh/Crore amount-in-words conversion.
* Cheque book and leaf tracking with an audit trail (unused/used/voided).
""",
    'depends': ['account', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'report/cheque_print_templates.xml',
        'views/cheque_layout_views.xml',
        'views/cheque_book_views.xml',
        'views/account_payment_views.xml',
        'views/hr_payslip_views.xml',
        'wizard/bulk_payment_wizard_views.xml',
        'wizard/bulk_cheque_print_views.xml',
        'wizard/jv_cheque_print_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'er_cheque_print/static/src/js/cheque_designer/cheque_designer_field.js',
            'er_cheque_print/static/src/js/cheque_designer/cheque_designer_field.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'author': 'Saad Dar',
}