# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class AfipBillingController(http.Controller):

    @http.route('/api/billing/invoices/<int:invoice_id>/pdf', type='http', auth='public', website=False, csrf=False)
    def get_invoice_pdf(self, invoice_id, token=None, **kwargs):
        """Endpoint para descargar factura ARCA en PDF con autenticación por token JWT."""
        
        if not token:
            return request.not_found()
        
        try:
            import jwt
            secret = request.env['ir.config_parameter'].sudo().get_param('l10n_ar_afip.jwt_secret', 'default_secret_key')
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return request.not_found()
            
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'l10n_ar_afip.report_invoice_afip',
                [invoice_id]
            )
            
            pdf_http = request.make_response(pdf_content, [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename=Factura_{invoice.name.replace("/", "_")}.pdf'),
            ])
            
            return pdf_http
            
        except jwt.ExpiredSignatureError:
            return request.make_response('Token expirado', [('Content-Type', 'text/plain')])
        except jwt.InvalidTokenError:
            return request.not_found()
        except Exception as e:
            _logger.error(f'Error generando PDF: {e}')
            return request.make_response(f'Error: {str(e)}', [('Content-Type', 'text/plain')])

    @http.route('/api/billing/invoices/<int:invoice_id>/json', type='json', auth='public', website=False, csrf=False)
    def get_invoice_json(self, invoice_id, token=None, **kwargs):
        """Endpoint para obtener datos de la factura en JSON."""
        
        if not token:
            return request.not_found()
        
        try:
            import jwt
            secret = request.env['ir.config_parameter'].sudo().get_param('l10n_ar_afip.jwt_secret', 'default_secret_key')
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return {'error': 'Factura no encontrada'}
            
            return {
                'id': invoice.id,
                'name': invoice.name,
                'date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                'partner': invoice.partner_id.name if invoice.partner_id else None,
                'amount_untaxed': invoice.amount_untaxed,
                'amount_tax': invoice.amount_tax,
                'amount_total': invoice.amount_total,
                'currency': invoice.currency_id.name if invoice.currency_id else 'ARS',
                'cae': invoice.cae,
                'cae_due_date': invoice.cae_due_date.isoformat() if invoice.cae_due_date else None,
                'afip_result': invoice.afip_result,
                'state': invoice.state,
            }
            
        except jwt.ExpiredSignatureError:
            return {'error': 'Token expirado'}
        except jwt.InvalidTokenError:
            return {'error': 'Token inválido'}
        except Exception as e:
            _logger.error(f'Error: {e}')
            return {'error': str(e)}
