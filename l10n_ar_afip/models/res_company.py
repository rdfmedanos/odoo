# -*- coding: utf-8 -*-
"""
Modelo para configuración de empresa con ARCA/AFIP.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64


class ResCompany(models.Model):
    _inherit = 'res.company'

    
    afip_certificate = fields.Binary(
        string='Certificado Digital (.pem)',
        attachment=True,
        help='Certificado digital en formato PEM'
    )
    
    afip_certificate_text = fields.Text(
        string='Certificado (texto)',
        help='Pegue aquí el contenido del certificado PEM firmado por ARCA'
    )
    
    afip_certificate_filename = fields.Char(
        string='Nombre del Certificado',
        compute='_compute_certificate_filename',
    )
    
    afip_private_key = fields.Binary(
        string='Clave Privada (.key)',
        attachment=True,
        help='Clave privada en formato PEM'
    )
    
    afip_private_key_text = fields.Text(
        string='Clave Privada (texto)',
        help='Pegue aquí el contenido de la clave privada PEM'
    )
    
    afip_private_key_filename = fields.Char(
        string='Nombre de Clave Privada',
        compute='_compute_key_filename',
    )
    
    afip_csr = fields.Text(
        string='CSR (Solicitud de Certificado)',
        readonly=True,
        help='CSR para subir a ARCA'
    )
    
    afip_ws_environment = fields.Selection([
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
    ], string='Ambiente WSFE', default='homologacion',
       help='Ambiente de ARCA para facturación electrónica')
    
    afip_point_of_sale = fields.Integer(
        string='Punto de Venta',
        default=1,
        help='Número de punto de venta asignado por AFIP'
    )
    
    afip_token = fields.Char(
        string='Token WSAA',
        copy=False,
        help='Token de autenticación WSAA'
    )
    
    afip_sign = fields.Char(
        string='Sign WSAA',
        copy=False,
        help='Firma de autenticación WSAA'
    )
    
    afip_token_expiration = fields.Datetime(
        string='Vencimiento Token',
        copy=False,
        help='Fecha de vencimiento del token WSAA'
    )
    
    afip_electronic_invoice_type = fields.Selection([
        ('A', 'Factura A'),
        ('B', 'Factura B'),
        ('C', 'Factura C'),
    ], string='Tipo de Comprobante por Defecto', default='B')
    
    afip_sequence_ids = fields.One2many(
        'l10n_ar_afip.sequence',
        'company_id',
        string='Secuencias AFIP',
    )
    
    def _compute_certificate_filename(self):
        for rec in self:
            if rec.afip_certificate:
                rec.afip_certificate_filename = 'certificate.pem'
            else:
                rec.afip_certificate_filename = False
    
    def _compute_key_filename(self):
        for rec in self:
            if rec.afip_private_key:
                rec.afip_private_key_filename = 'private.key'
            else:
                rec.afip_private_key_filename = False
    
    def action_generate_csr(self):
        """Genera clave privada y CSR para ARCA."""
        self.ensure_one()
        
        if not self.afip_cuit:
            raise UserError('Debe ingresar el CUIT antes de generar el CSR')
        
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            import datetime
            
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            csr_builder = x509.CertificateSigningRequestBuilder()
            csr_builder = csr_builder.subject_name(
                x509.Name([
                    x509.NameAttribute(NameOID.COUNTRY_NAME, 'AR'),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'Buenos Aires'),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, 'Buenos Aires'),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.name or 'Empresa'),
                    x509.NameAttribute(NameOID.COMMON_NAME, self.afip_cuit),
                ])
            )
            
            csr = csr_builder.sign(private_key, hashes.SHA256(), default_backend())
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            
            self.write({
                'afip_private_key': base64.b64encode(private_key_pem).decode('utf-8'),
                'afip_csr': csr_pem,
            })
            
            raise UserError('Clave privada y CSR generados correctamente. Descargue el CSR y súbalo a AFIP.')
            
        except UserError:
            raise
        except ImportError:
            raise UserError(
                'No se encontró la librería cryptography. '
                'Instale con: pip install cryptography'
            )
        except Exception as e:
            raise UserError(f'Error al generar CSR: {str(e)}')
    
    def action_download_csr(self):
        """Descarga el CSR generado."""
        self.ensure_one()
        if not self.afip_csr:
            raise UserError('Primero debe generar el CSR')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=res.company&id={self.id}&field=afip_csr&download=true&filename=csr.csr',
            'target': 'self',
        }
    
    def action_download_key(self):
        """Descarga la clave privada generada."""
        self.ensure_one()
        if not self.afip_private_key:
            raise UserError('Primero debe generar la clave privada')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=res.company&id={self.id}&field=afip_private_key&download=true&filename=private.key',
            'target': 'self',
        }
    
    def action_copy_private_key(self):
        """Abre un modal con la clave para copiar."""
        self.ensure_one()
        if not self.afip_private_key:
            raise UserError('Primero debe generar la clave privada')
        
        key_pem = base64.b64decode(self.afip_private_key).decode('utf-8')
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_ar_afip.clipboard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_key_content': key_pem},
        }
    
    def get_afip_credentials(self) -> dict:
        """Obtiene las credenciales AFIP de la empresa."""
        self.ensure_one()
        
        cert_data = self.afip_certificate
        key_data = self.afip_private_key
        
        if cert_data:
            certificate_pem = base64.b64decode(cert_data).decode('utf-8')
        elif self.afip_certificate_text:
            certificate_pem = self.afip_certificate_text
        else:
            raise UserError('Falta certificado AFIP (subir archivo o pegar texto)')
        
        if key_data:
            private_key_pem = base64.b64decode(key_data).decode('utf-8')
        elif self.afip_private_key_text:
            private_key_pem = self.afip_private_key_text
        else:
            raise UserError('Falta clave privada AFIP (subir archivo o pegar texto)')
        
        return {
            'certificate_pem': certificate_pem,
            'private_key_pem': private_key_pem,
            'cuit': self.afip_cuit,
            'environment': self.afip_ws_environment,
            'pto_vta': self.afip_point_of_sale,
            'token': self.afip_token,
            'sign': self.afip_sign,
        }
    
    def refresh_afip_token(self) -> dict:
        """Refresca el token WSAA."""
        self.ensure_one()
        
        from ..services.wsaa import WSAAService
        
        creds = self.get_afip_credentials()
        wsaa = WSAAService(
            creds['certificate_pem'],
            creds['private_key_pem'],
            creds['environment']
        )
        
        result = wsaa.request_token('wsfe')
        
        expiration = fields.Datetime.now() + datetime.timedelta(hours=12)
        
        self.write({
            'afip_token': result['token'],
            'afip_sign': result['sign'],
            'afip_token_expiration': expiration,
        })
        
        return result


class L10nArAfipSettings(models.TransientModel):
    _name = 'l10n_ar_afip.settings'
    _description = 'Configuración AFIP'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Empresa', required=True,
                                 default=lambda self: self.env.company)
    afip_cuit = fields.Char(related='company_id.l10n_ar_afip_cuit', string='CUIT', readonly=False)
    afip_ws_environment = fields.Selection(related='company_id.afip_ws_environment', 
                                           string='Ambiente', readonly=False)
    afip_point_of_sale = fields.Integer(related='company_id.afip_point_of_sale',
                                         string='Punto de Venta', readonly=False)
    afip_certificate = fields.Binary(related='company_id.afip_certificate',
                                     string='Certificado', readonly=False)
    afip_certificate_text = fields.Text(related='company_id.afip_certificate_text',
                                         string='Certificado (texto)', readonly=False)
    afip_private_key = fields.Binary(related='company_id.afip_private_key',
                                     string='Clave Privada', readonly=False)
    afip_private_key_text = fields.Text(related='company_id.afip_private_key_text',
                                        string='Clave Privada (texto)', readonly=False)
    afip_csr = fields.Text(related='company_id.afip_csr', string='CSR', readonly=True)

    def refresh_afip_token(self):
        """Refresca el token WSAA."""
        self.ensure_one()
        company = self.company_id
        company.refresh_afip_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class L10nArAfipClipboard(models.TransientModel):
    _name = 'l10n_ar_afip.clipboard'
    _description = 'Clipboard para copiar clave privada'
    
    key_content = fields.Text(string='Clave Privada', readonly=True)
    
    def copy_to_clipboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_ar_afip.clipboard',
            'target': 'new',
            'context': {
                'default_key_content': self.key_content,
            },
        }


class L10nArAfipSequence(models.Model):
    _name = 'l10n_ar_afip.sequence'
    _description = 'Secuencia AFIP por tipo de comprobante'
    
    company_id = fields.Many2one('res.company', string='Empresa', required=True)
    
    document_type = fields.Selection([
        ('A', 'Factura A'),
        ('B', 'Factura B'),
        ('C', 'Factura C'),
        ('M', 'Nota de Crédito A'),
        ('N', 'Nota de Crédito B'),
        ('O', 'Nota de Crédito C'),
    ], string='Tipo de Comprobante', required=True)
    
    sequence_id = fields.Many2one('ir.sequence', string='Secuencia')
    last_number = fields.Integer(string='Último Número', default=0)
    
    _sql_constraints = [
        ('unique_company_document', 'UNIQUE(company_id, document_type)',
         'Solo puede existir una secuencia por empresa y tipo de documento'),
    ]
