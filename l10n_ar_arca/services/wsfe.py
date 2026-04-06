# -*- coding: utf-8 -*-
"""
Servicio WSFE para facturación electrónica ARCA/AFIP.
Basado en la implementación de AgroSentinel.
"""

import re
from datetime import datetime
from lxml import etree
import requests


class WSFEService:
    """Servicio para facturación WSFE de ARCA."""
    
    WSFE_URLS = {
        'homologacion': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx',
        'produccion': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx',
    }
    
    TIPO_COMPROBANTE = {
        'invoice_a': 1,
        'invoice_b': 6,
        'invoice_c': 11,
        'invoice_m': 51,
        'credit_note_a': 2,
        'credit_note_b': 7,
        'credit_note_c': 12,
    }
    
    CONDICION_IVA = {
        'responsable_inscripto': 1,
        'responsable_no_inscripto': 2,
        'exento': 4,
        'consumidor_final': 5,
        'monotributo': 6,
        'no_categorizado': 7,
        'iva_sujeto_exento': 8,
        'small_contributor_eventual': 9,
        'small_contributor_social': 13,
    }
    
    def __init__(self, token: str, sign: str, cuit: int, environment: str = 'homologacion'):
        self.token = token
        self.sign = sign
        self.cuit = cuit
        self.environment = environment
        self.wsfe_url = self.WSFE_URLS.get(environment, self.WSFE_URLS['homologacion'])
    
    def _extract_tag(self, xml: str, tag: str) -> str | None:
        """Extrae el contenido de un tag XML."""
        pattern = f'<{tag}>([^<]+)</{tag}>'
        match = re.search(pattern, xml)
        return match.group(1) if match else None
    
    def _extract_errors(self, xml: str) -> list[dict]:
        """Extrae errores de la respuesta XML."""
        errors = []
        codes = re.findall(r'<Code>(\d+)</Code>', xml)
        msgs = re.findall(r'<Msg>([^<]+)</Msg>', xml)
        for code, msg in zip(codes, msgs):
            errors.append({'code': code, 'msg': msg})
        return errors
    
    def _soap_call(self, action: str, body: str) -> str:
        """Realiza una llamada SOAP al WSFE."""
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    {body}
  </soap:Body>
</soap:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': f'"http://ar.gov.afip.dif.FEV1/{action}"'
        }
        
        response = requests.post(self.wsfe_url, data=envelope, headers=headers, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"WSFE HTTP {response.status_code}: {response.text[:500]}")
        
        return response.text
    
    def get_last_voucher_number(self, pto_vta: int, cbte_tipo: int) -> int:
        """Obtiene el último número de comprobante autorizado."""
        body = f"""<FECompUltimoAutorizado xmlns="http://ar.gov.afip.dif.FEV1/">
  <Auth>
    <Token>{self.token}</Token>
    <Sign>{self.sign}</Sign>
    <Cuit>{self.cuit}</Cuit>
  </Auth>
  <PtoVta>{pto_vta}</PtoVta>
  <CbteTipo>{cbte_tipo}</CbteTipo>
</FECompUltimoAutorizado>"""
        
        xml = self._soap_call('FECompUltimoAutorizado', body)
        cbte_nro = self._extract_tag(xml, 'CbteNro')
        return int(cbte_nro) if cbte_nro else 0
    
    def request_cae(self, invoice_data: dict) -> dict:
        """
        Solicita CAE para un comprobante.
        
        Args:
            invoice_data: dict con datos de la factura:
                - tipo: 'A', 'B', 'C' o 'M'
                - punto_vta: número de punto de venta
                - concepto: 1 (productos), 2 (servicios), 3 (ambos)
                - tipo_doc: tipo de documento del receptor
                - nro_doc: número de documento del receptor
                - condicion_iva: condición IVA del receptor
                - fecha: fecha del comprobante (YYYYMMDD)
                - importe_total: monto total
                - importe_neto: monto neto gravado
                - importe_iva: monto total de IVA
                - iva_lines: lista de líneas de IVA [{id, base, amount}]
        
        Returns:
            dict con 'cae', 'cae_due_date', 'cbte_nro', 'result', 'errors'
        """
        tipo = invoice_data.get('tipo', 'B')
        pto_vta = invoice_data.get('punto_vta', 1)
        concepto = invoice_data.get('concepto', 2)
        tipo_doc = invoice_data.get('tipo_doc', 99)
        nro_doc = invoice_data.get('nro_doc', '0')
        condicion_iva = invoice_data.get('condicion_iva', 'consumidor_final')
        fecha = invoice_data.get('fecha', datetime.now().strftime('%Y%m%d'))
        imp_total = invoice_data.get('importe_total', 0)
        imp_neto = invoice_data.get('importe_neto', 0)
        imp_iva = invoice_data.get('importe_iva', 0)
        moneda = invoice_data.get('moneda', 'PES')
        cotizacion = invoice_data.get('cotizacion', 1)
        iva_lines = invoice_data.get('iva_lines', [])
        
        cbte_tipo = invoice_data.get('codigo_cbte') or self.TIPO_COMPROBANTE.get(f'invoice_{tipo.lower()}', 6)
        condicion_iva_id = self.CONDICION_IVA.get(condicion_iva.lower().replace(' ', '_'), 5)
        
        last_nro = self.get_last_voucher_number(pto_vta, cbte_tipo)
        next_nro = last_nro + 1
        
        iva_nodes = ''
        if iva_lines and imp_neto > 0:
            iva_nodes = '<Iva>'
            for iva in iva_lines:
                iva_nodes += f"""
              <AlicIva>
                <Id>{iva['id']}</Id>
                <BaseImp>{iva['base']:.2f}</BaseImp>
                <Importe>{iva['amount']:.2f}</Importe>
              </AlicIva>"""
            iva_nodes += '</Iva>'
        
        body = f"""<FECAESolicitar xmlns="http://ar.gov.afip.dif.FEV1/">
  <Auth>
    <Token>{self.token}</Token>
    <Sign>{self.sign}</Sign>
    <Cuit>{self.cuit}</Cuit>
  </Auth>
  <FeCAEReq>
    <FeCabReq>
      <CantReg>1</CantReg>
      <PtoVta>{pto_vta}</PtoVta>
      <CbteTipo>{cbte_tipo}</CbteTipo>
    </FeCabReq>
    <FeDetReq>
      <FECAEDetRequest>
        <Concepto>{concepto}</Concepto>
        <DocTipo>{tipo_doc}</DocTipo>
        <DocNro>{nro_doc}</DocNro>
        <CondicionIVAReceptorId>{condicion_iva_id}</CondicionIVAReceptorId>
        <CbteDesde>{next_nro}</CbteDesde>
        <CbteHasta>{next_nro}</CbteHasta>
        <CbteFch>{fecha}</CbteFch>
        <ImpTotal>{imp_total:.2f}</ImpTotal>
        <ImpTotConc>0.00</ImpTotConc>
        <ImpNeto>{imp_neto:.2f}</ImpNeto>
        <ImpOpEx>0.00</ImpOpEx>
        <ImpIVA>{imp_iva:.2f}</ImpIVA>
        <ImpTrib>0.00</ImpTrib>
        <MonId>{moneda}</MonId>
        <MonCotiz>{cotizacion}</MonCotiz>
        <FchServDesde>{fecha}</FchServDesde>
        <FchServHasta>{fecha}</FchServHasta>
        <FchVtoPago>{fecha}</FchVtoPago>
        {iva_nodes}
      </FECAEDetRequest>
    </FeDetReq>
  </FeCAEReq>
</FECAESolicitar>"""
        
        xml_response = self._soap_call('FECAESolicitar', body)
        
        result = self._extract_tag(xml_response, 'Resultado') or 'R'
        cae = self._extract_tag(xml_response, 'CAE')
        cae_due_date = self._extract_tag(xml_response, 'CAEFchVto')
        errors = self._extract_errors(xml_response)
        
        if result != 'A' or not cae or not cae_due_date:
            error_msgs = ', '.join([f"{e['code']}: {e['msg']}" for e in errors]) or 'Sin detalle'
            raise Exception(f"ARCA rechazó comprobante: {error_msgs}")
        
        return {
            'cae': cae,
            'cae_due_date': cae_due_date,
            'cbte_nro': next_nro,
            'result': result,
            'errors': errors,
        }
    
    def test_connection(self, pto_vta: int = 1) -> dict:
        """Prueba la conexión con WSFE."""
        try:
            last_voucher = self.get_last_voucher_number(pto_vta, 6)
            return {
                'ok': True,
                'message': 'Conexión exitosa con ARCA WSFE',
                'last_voucher': last_voucher,
            }
        except Exception as e:
            return {
                'ok': False,
                'message': str(e),
            }
