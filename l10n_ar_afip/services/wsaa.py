# -*- coding: utf-8 -*-
"""
Servicio WSAA para autenticación con ARCA/AFIP.
Basado en la implementación de AgroSentinel.
"""

import base64
import re
from datetime import datetime, timedelta
from lxml import etree
import requests


class WSAAService:
    """Servicio para autenticación WSAA de ARCA/AFIP."""
    
    WSAA_URLS = {
        'homologacion': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
        'produccion': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
    }
    
    def __init__(self, certificate_pem: str, private_key_pem: str, environment: str = 'homologacion'):
        self.certificate_pem = certificate_pem
        self.private_key_pem = private_key_pem
        self.environment = environment
        self.wsaa_url = self.WSAA_URLS.get(environment, self.WSAA_URLS['homologacion'])
    
    def _format_wsaa_date(self, date: datetime) -> str:
        """Formatea fecha para WSAA en formato UTC-3 (Argentina)."""
        return date.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    
    def _create_tra(self, service: str = 'wsfe') -> str:
        """Crea el Ticket de Requerimiento de Acceso (TRA)."""
        now = datetime.now()
        unique_id = int(now.timestamp())
        generation_time = self._format_wsaa_date(now)
        expiration_time = self._format_wsaa_date(now + timedelta(hours=12))
        
        tra = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
  <header>
    <uniqueId>{unique_id}</uniqueId>
    <generationTime>{generation_time}</generationTime>
    <expirationTime>{expiration_time}</expirationTime>
  </header>
  <service>{service}</service>
</loginTicketRequest>"""
        return tra
    
    def _sign_tra(self, tra: str) -> str:
        """Firma el TRA usando PKCS#7/CMS."""
        import subprocess
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tra', delete=False) as f:
            f.write(tra)
            tra_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(self.certificate_pem)
            cert_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
            f.write(self.private_key_pem)
            key_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.out', delete=False) as f:
            out_path = f.name
        
        try:
            cmd = [
                'openssl', 'cms', '-sign',
                '-in', tra_path,
                '-signer', cert_path,
                '-inkey', key_path,
                '-outform', 'DER',
                '-out', out_path,
                '-nodetach'
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            with open(out_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        finally:
            for path in [tra_path, cert_path, key_path, out_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def _parse_login_response(self, xml_response: str) -> dict:
        """Parsea la respuesta XML del loginCms."""
        root = etree.fromstring(xml_response.encode())
        
        namespaces = {
            'wsaa': 'http://wsaa.view.sua.dvadac.desein.afip.gov',
        }
        
        login_return = root.find('.//wsaa:loginCmsReturn', namespaces)
        if login_return is None:
            login_return = root.find('.//loginCmsReturn')
        
        if login_return is None:
            for elem in root.iter():
                if 'loginCmsReturn' in elem.tag or 'LoginCmsReturn' in elem.tag:
                    login_return = elem
                    break
        
        if login_return is None or not login_return.text:
            raise Exception(f"No se encontró loginCmsReturn en la respuesta WSAA: {xml_response[:500]}")
        
        response_xml = login_return.text
        
        token_match = re.search(r'<token>([^<]+)</token>', response_xml)
        sign_match = re.search(r'<sign>([^<]+)</sign>', response_xml)
        
        if not token_match or not sign_match:
            raise Exception(f"WSAA no devolvió token/sign: {response_xml[:500]}")
        
        return {
            'token': token_match.group(1),
            'sign': sign_match.group(1),
        }
    
    def request_token(self, service: str = 'wsfe') -> dict:
        """
        Solicita token y sign a WSAA.
        
        Returns:
            dict con 'token' y 'sign'
        """
        tra = self._create_tra(service)
        signed_tra = self._sign_tra(tra)
        
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">
  <soapenv:Header/>
  <soapenv:Body>
    <wsaa:loginCms>
      <wsaa:in0>{signed_tra}</wsaa:in0>
    </wsaa:loginCms>
  </soapenv:Body>
</soapenv:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '""'
        }
        
        response = requests.post(self.wsaa_url, data=envelope, headers=headers, timeout=30)
        
        if response.status_code != 200:
            faultstring = re.search(r'<faultstring>([^<]+)</faultstring>', response.text)
            if faultstring:
                error_msg = faultstring.group(1)
                if 'alreadyAuthenticated' in error_msg:
                    raise Exception("WSAA: Ya existe un TA válido (coe.alreadyAuthenticated)")
                if 'notAuthorized' in error_msg.lower():
                    raise Exception("WSAA: Certificado no autorizado para el servicio. Verifique en Administrador de Certificados que esté asociado a WSFEv1")
                raise Exception(f"WSAA HTTP {response.status_code}: {error_msg}")
            raise Exception(f"WSAA HTTP {response.status_code}: {response.text[:500]}")
        
        return self._parse_login_response(response.text)
