# -*- coding: utf-8 -*-
"""
Modelo para facturas con integración ARCA/AFIP.
"""

import base64
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    cae = fields.Char(
        string='CAE',
        copy=False,
        readonly=True,
        help='Código de Autorización Electrónico'
    )
    
    cae_due_date = fields.Date(
        string='Fecha Vencimiento CAE',
        copy=False,
        readonly=True,
    )
    
    afip_result = fields.Selection([
        ('A', 'Aprobado'),
        ('R', 'Rechazado'),
        ('O', 'Observado'),
    ], string='Resultado AFIP', copy=False, readonly=True)
    
    afip_errors = fields.Text(
        string='Errores AFIP',
        copy=False,
        readonly=True,
    )
    
    afip_barcode = fields.Char(
        string='Código de Barras',
        compute='_compute_afip_barcode',
        store=True,
    )
    
    afip_qr_data = fields.Char(
        string='Datos QR',
        compute='_compute_afip_qr_data',
        store=True,
    )
    
    afip_qr_image = fields.Binary(
        string='Código QR AFIP',
        compute='_compute_afip_qr_image',
        store={'account.move': lambda self, cr, uid, ids, context=None: ids},
    )
    
    afip_document_type = fields.Selection([
        ('A', 'Factura A'),
        ('B', 'Factura B'),
        ('C', 'Factura C'),
    ], string='Tipo Comprobante AFIP', default='B')
    
    afip_document_number = fields.Char(
        string='Número Comprobante AFIP',
        compute='_compute_afip_document_number',
        store=True,
    )
    
    l10n_ar_afip_state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('authorized', 'Autorizado'),
        ('rejected', 'Rechazado'),
    ], string='Estado AFIP', default='draft', copy=False)
    
    def _compute_afip_barcode(self):
        """Genera el código de barras para el CAE."""
        for move in self:
            if move.cae:
                pto_vta = str(move.journal_id.l10n_ar_afip_pto_vta or 1).zfill(4)
                cbte_nro = str(move.afip_document_number or '').zfill(8)
                barcode = f"{move.partner_id.vat or '0'}{pto_vta}{cbte_nro}{move.cae}"
                move.afip_barcode = barcode
            else:
                move.afip_barcode = False
    
    @api.depends('cae', 'cae_due_date', 'date', 'partner_id', 'amount_total', 'amount_tax', 'amount_untaxed', 'afip_document_type', 'afip_document_number', 'journal_id.l10n_ar_afip_pto_vta')
    def _compute_afip_qr_data(self):
        """Genera los datos para el código QR según especificación AFIP."""
        for move in self:
            if move.cae and move.cae_due_date:
                company = move.company_id
                partner = move.partner_id
                
                fecha = move.date.strftime('%Y%m%d') if move.date else ''
                
                nro_doc_receptor = (partner.vat or '0').replace('-', '').replace(' ', '')
                tipo_doc_receptor = 80 if partner.vat else 99
                
                cbte_nro = move.afip_document_number or ''
                pto_vta = str(move.journal_id.l10n_ar_afip_pto_vta or 1).zfill(4)
                
                tipo_cbte = self._get_tipo_comprobante_afip()
                
                imp_total = f"{move.amount_total:.2f}"
                imp_iva = f"{move.amount_tax:.2f}"
                imp_neto = f"{move.amount_untaxed:.2f}"
                
                cae_str = str(move.cae)
                cae_venc = move.cae_due_date.strftime('%Y%m%d') if move.cae_due_date else ''
                
                qr_data = f"https://www.afip.gob.ar/fe/qr/?p=%7B%22ver%22%3A1%2C%22fecha%22%3A%22{fecha}%22%2C%22cuit%22%3A{company.afip_cuit}%2C%22ptoVta%22%3A{pto_vta}%2C%22tipoCmp%22%3A{tipo_cbte}%2C%22nroCmp%22%3A{cbte_nro.replace('-', '')}%2C%22importe%22%3A{imp_total}%2C%22moneda%22%3A%22PES%22%2C%22ctz%22%3A1%2C%22tipoDocRec%22%3A{tipo_doc_receptor}%2C%22nroDocRec%22%3A{nro_doc_receptor}%2C%22tipoAut%22%3A%22E%22%2C%22codAut%22%3A{cae_str}%7D"
                
                move.afip_qr_data = qr_data
            else:
                move.afip_qr_data = False
    
    def _get_tipo_comprobante_afip(self):
        """Retorna el código AFIP del tipo de comprobante."""
        tipo_map = {
            'A': 1,
            'B': 6,
            'C': 11,
            'M': 51,
        }
        return tipo_map.get(self.afip_document_type, 6)
    
    @api.depends('cae', 'cae_due_date', 'date', 'partner_id', 'amount_total', 'amount_tax', 'amount_untaxed', 'afip_document_type', 'afip_document_number', 'journal_id.l10n_ar_afip_pto_vta', 'company_id.afip_cuit')
    def _compute_afip_qr_image(self):
        """Genera la imagen QR para AFIP."""
        try:
            import qrcode
            import io
            import json
        except ImportError:
            for move in self:
                move.afip_qr_image = False
            return
        
        for move in self:
            if move.cae and move.cae_due_date and move.company_id.afip_cuit:
                company = move.company_id
                partner = move.partner_id
                
                fecha = move.date.strftime('%Y%m%d') if move.date else ''
                
                nro_doc_receptor = (partner.vat or '0').replace('-', '').replace(' ', '')
                tipo_doc_receptor = 80 if partner.vat and len(partner.vat.replace('-', '')) >= 11 else 99
                
                pto_vta = str(move.journal_id.l10n_ar_afip_pto_vta or 1).zfill(4)
                tipo_cbte = self._get_tipo_comprobante_afip()
                
                cbte_nro = ''.join(filter(str.isdigit, move.afip_document_number or ''))
                
                qr_data = {
                    'ver': 1,
                    'fecha': fecha,
                    'cuit': int(company.afip_cuit) if company.afip_cuit else 0,
                    'ptoVta': int(pto_vta),
                    'tipoCmp': tipo_cbte,
                    'nroCmp': int(cbte_nro) if cbte_nro else 0,
                    'importe': float(move.amount_total),
                    'moneda': 'PES',
                    'ctz': 1,
                    'tipoDocRec': tipo_doc_receptor,
                    'nroDocRec': nro_doc_receptor or '0',
                    'tipoAut': 'E',
                    'codAut': str(move.cae),
                }
                
                qr_json = json.dumps(qr_data, separators=(',', ':'))
                
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
                qr.add_data(qr_json)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                move.afip_qr_image = base64.b64encode(buffer.getvalue())
            else:
                move.afip_qr_image = False
    
    def regenerate_afip_qr(self):
        """Regenera el código QR."""
        self._compute_afip_qr_image()
        return True
    
    @api.depends('name', 'afip_document_type', 'journal_id.l10n_ar_afip_pto_vta')
    def _compute_afip_document_number(self):
        """Calcula el número de documento AFIP."""
        for move in self:
            if move.name:
                pto_vta = move.journal_id.l10n_ar_afip_pto_vta or 1
                doc_number = move.name.split('/')[-1] if '/' in move.name else move.name
                move.afip_document_number = f"{str(pto_vta).zfill(4)}-{doc_number.zfill(8)}"
            else:
                move.afip_document_number = False
    
    def _get_afip_document_type(self):
        """Determina el tipo de documento AFIP según la condición IVA del partner."""
        self.ensure_one()
        
        if self.partner_id.l10n_ar_afip_responsibility_type_id:
            responsibility = self.partner_id.l10n_ar_afip_responsibility_type_id.code
        else:
            responsibility = self.partner_id.l10n_ar_vatresponsibility_type_id.code if hasattr(self.partner_id, 'l10n_ar_vatresponsibility_type_id') else 'CF'
        
        if responsibility == '1':
            return 'A'
        elif responsibility in ('4', '5', '6', '9', '10', '13'):
            return 'B'
        else:
            return 'C'
    
    def _prepare_afip_invoice_data(self) -> dict:
        """Prepara los datos de la factura para ARCA."""
        self.ensure_one()
        
        partner = self.partner_id
        
        tipo_doc = 99
        nro_doc = '0'
        
        if hasattr(partner, 'l10n_ar_partner_document_type') and partner.l10n_ar_partner_document_type:
            doc_type = partner.l10n_ar_partner_document_type
        elif partner.vat and len(partner.vat.replace('-', '').replace(' ', '')) == 11:
            doc_type = 'dni'
        elif partner.vat and len(partner.vat.replace('-', '').replace(' ', '')) >= 11:
            doc_type = 'cuit'
        else:
            doc_type = 'other'
        
        if doc_type == 'cuit':
            tipo_doc = 80
            nro_doc = (partner.vat or '').replace('-', '').replace(' ', '')
        elif doc_type == 'dni':
            tipo_doc = 96
            nro_doc = partner.vat or '0'
        else:
            tipo_doc = 99
            nro_doc = partner.vat or '0'
        
        imp_total = self.amount_total
        imp_neto = self.amount_untaxed
        iva_amount = self.amount_tax
        
        iva_lines = self._get_afip_iva_lines()
        
        return {
            'tipo': self.afip_document_type or 'B',
            'punto_vta': self.journal_id.l10n_ar_afip_pto_vta or self.company_id.afip_point_of_sale,
            'concepto': 2,
            'tipo_doc': tipo_doc,
            'nro_doc': nro_doc,
            'condicion_iva': self._get_condicion_iva_partner(),
            'fecha': self.date.strftime('%Y%m%d'),
            'importe_total': imp_total,
            'importe_neto': imp_neto,
            'importe_iva': iva_amount,
            'iva_lines': iva_lines,
        }
    
    def _get_afip_iva_lines(self) -> list:
        """Obtiene las líneas de IVA para AFIP."""
        iva_map = {
            21: 5,
            10.5: 4,
            27: 6,
            2.5: 8,
            0: 3,
        }
        
        iva_amounts = {}
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.amount > 0:
                    iva_id = iva_map.get(tax.amount, 5)
                    base = line.price_subtotal
                    amount = line.price_subtotal * (tax.amount / 100)
                    if iva_id not in iva_amounts:
                        iva_amounts[iva_id] = {'base': 0, 'amount': 0}
                    iva_amounts[iva_id]['base'] += base
                    iva_amounts[iva_id]['amount'] += amount
        
        result = []
        for iva_id, data in iva_amounts.items():
            result.append({
                'id': iva_id,
                'base': data['base'],
                'amount': data['amount'],
            })
        return result
    
    def _get_condicion_iva_partner(self) -> str:
        """Obtiene la condición IVA del partner."""
        self.ensure_one()
        partner = self.partner_id
        
        if hasattr(partner, 'l10n_ar_afip_responsibility_type_id') and partner.l10n_ar_afip_responsibility_type_id:
            code = partner.l10n_ar_afip_responsibility_type_id.code
        elif hasattr(partner, 'l10n_ar_vatresponsibility_type_id') and partner.l10n_ar_vatresponsibility_type_id:
            code = partner.l10n_ar_vatresponsibility_type_id.code
        else:
            return 'consumidor_final'
        
        mapping = {
            '1': 'responsable_inscripto',
            '4': 'exento',
            '5': 'consumidor_final',
            '6': 'monotributo',
            '7': 'no_categorizado',
            '13': 'small_contributor_social',
        }
        return mapping.get(code, 'consumidor_final')
    
    def _get_afip_service(self):
        """Obtiene el servicio WSFE configurado."""
        self.ensure_one()
        company = self.company_id
        
        if not company.afip_token or not company.afip_sign:
            company.refresh_afip_token()
        
        from ..services.wsfe import WSFEService
        
        return WSFEService(
            token=company.afip_token,
            sign=company.afip_sign,
            cuit=int(company.afip_cuit),
            environment=company.afip_ws_environment,
        )
    
    def action_request_afip_cae(self):
        """Solicita CAE a AFIP."""
        for move in self:
            if move.state != 'posted':
                raise UserError('Solo se pueden autorizar facturas publicadas')
            
            if move.cae:
                raise UserError('Esta factura ya tiene CAE')
            
            if not move.company_id.afip_cuit:
                raise UserError('Configure el CUIT de la empresa en la configuración de AFIP')
            
            has_cert = move.company_id.afip_certificate or move.company_id.afip_certificate_text
            has_key = move.company_id.afip_private_key or move.company_id.afip_private_key_text
            
            if not has_cert:
                raise UserError('Configure el certificado digital AFIP (archivo o texto)')
            
            if not has_key:
                raise UserError('Configure la clave privada AFIP (archivo o texto)')
            
            move.l10n_ar_afip_state = 'pending'
            
            try:
                wsfe = move._get_afip_service()
                invoice_data = move._prepare_afip_invoice_data()
                
                result = wsfe.request_cae(invoice_data)
                
                move.write({
                    'cae': result['cae'],
                    'cae_due_date': datetime.strptime(result['cae_due_date'], '%Y%m%d').date(),
                    'afip_result': result['result'],
                    'afip_errors': False,
                    'l10n_ar_afip_state': 'authorized',
                })
                
            except Exception as e:
                move.write({
                    'afip_result': 'R',
                    'afip_errors': str(e),
                    'l10n_ar_afip_state': 'rejected',
                })
                raise UserError(f'Error al solicitar CAE a AFIP: {str(e)}')
    
    def action_retry_afip_cae(self):
        """Reintenta solicitar CAE."""
        self.write({
            'l10n_ar_afip_state': 'draft',
            'afip_result': False,
            'afip_errors': False,
        })
        return self.action_request_afip_cae()
    
    def action_post(self):
        """Override del método post para solicitar CAE automáticamente."""
        res = super().action_post()
        
        for move in self.filtered(lambda m: m.company_id.afip_ws_environment):
            if move.move_type in ('out_invoice', 'out_refund'):
                if move.journal_id.l10n_ar_afip_auto_authorize:
                    move.afip_document_type = move._get_afip_document_type()
                    try:
                        move.action_request_afip_cae()
                    except Exception as e:
                        pass
        
        return res


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    l10n_ar_afip_pto_vta = fields.Integer(
        string='Punto de Venta AFIP',
        help='Punto de venta configurado en AFIP para este diario'
    )
    
    l10n_ar_afip_document_type = fields.Selection([
        ('A', 'Factura A'),
        ('B', 'Factura B'),
        ('C', 'Factura C'),
    ], string='Tipo Documento AFIP')
    
    l10n_ar_afip_auto_authorize = fields.Boolean(
        string='Autorizar automáticamente',
        default=False,
        help='Solicitar CAE automáticamente al confirmar la factura'
    )
