package com.jaz.gepyco.data.ocr

import android.graphics.Bitmap
import android.util.Log
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.jaz.gepyco.domain.model.Invoice
import com.jaz.gepyco.domain.model.InvoiceLine
import kotlinx.coroutines.suspendCancellableCoroutine
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

private const val TAG = "InvoiceOCR"

@Singleton
class InvoiceOcrProcessor @Inject constructor() {
    
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    
    suspend fun processImage(bitmap: Bitmap): Invoice? = suspendCancellableCoroutine { continuation ->
        val image = InputImage.fromBitmap(bitmap, 0)
        
        Log.d(TAG, "=== INICIANDO PROCESAMIENTO OCR ===")
        Log.d(TAG, "Dimensiones imagen: ${bitmap.width}x${bitmap.height}")
        
        recognizer.process(image)
            .addOnSuccessListener { visionText ->
                Log.d(TAG, "OCR Exitoso. Bloques encontrados: ${visionText.textBlocks.size}")
                Log.d(TAG, "Texto extraído (primeros 500 chars):\n${visionText.text.take(500)}")
                val invoice = parseInvoiceText(visionText, bitmap.width, bitmap.height)
                continuation.resume(invoice)
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Error en OCR", e)
                continuation.resumeWithException(e)
            }
    }
    
    private fun parseInvoiceText(visionText: Text, imageWidth: Int, imageHeight: Int): Invoice {
        Log.d(TAG, "\n" + "=".repeat(60))
        Log.d(TAG, "INICIANDO PARSING DE INVOICE")
        Log.d(TAG, "=".repeat(60))
        
        val textBlocks = visionText.textBlocks
        val fullText = visionText.text
        val fullTextUpper = fullText.uppercase()
        
        Log.d(TAG, "Total de bloques OCR: ${textBlocks.size}")
        Log.d(TAG, "Texto completo extraído:\n$fullText\n")
        
        // Dividir por secciones usando posición Y (más robusto)
        val quarterY = imageHeight / 4
        val halfY = imageHeight / 2
        val threeQuarterY = (imageHeight * 3) / 4
        
        Log.d(TAG, "Parámetros división: quarterY=$quarterY, halfY=$halfY, threeQuarterY=$threeQuarterY")
        
        val headerBlocks = mutableListOf<Text.TextBlock>()  // Arriba (emisor + factura)
        val productBlocks = mutableListOf<Text.TextBlock>() // Centro (productos)
        val footerBlocks = mutableListOf<Text.TextBlock>()  // Abajo (totales)
        
        // Función auxiliar para detectar si un bloque contiene un monto
        fun isMoneyBlock(text: String): Boolean {
            val textUpper = text.uppercase()
            // Patrones que indican que es dinero/total
            return Regex("(TOTAL|SUBTOTAL|NETO|IMPORTE|IVA)[\\s:\\$]*[0-9.,]+").containsMatchIn(textUpper) ||
                   Regex("^\\$?\\s*[0-9.,]+\\s*(\\$|ARS)?\\s*$").matches(text.trim()) || // Solo dinero: "$1234,56"
                   Regex("\\b(TOTAL|SUBTOTAL|NETO|IMPORTE|IVA)\\b").containsMatchIn(textUpper) && 
                   Regex("[0-9.,]{4,}").containsMatchIn(text) // Palabra de total + números largos
        }
        
        Log.d(TAG, "\n--- CLASIFICANDO BLOQUES CON HEURÍSTICA MEJORADA ---")
        
        // Primera pasada: identificar bloques especiales
        val moneyBlockIndices = mutableSetOf<Int>()
        val productHeaderIndices = mutableSetOf<Int>()
        
        for ((index, block) in textBlocks.withIndex()) {
            val textUpper = block.text.uppercase()
            
            // Detectar totales/montos
            if (Regex("\\b(TOTAL|SUBTOTAL|NETO|IMPORTE)\\b").containsMatchIn(textUpper)) {
                moneyBlockIndices.add(index)
                Log.d(TAG, "Bloque $index es TOTAL/DINERO")
            }
            
            // Detectar encabezado de productos
            if (Regex("\\b(CANTIDAD|CANT|DESC|DESCRIPCIÓN|PRECIO|UNITARIO|VALOR)\\b").containsMatchIn(textUpper)) {
                productHeaderIndices.add(index)
                Log.d(TAG, "Bloque $index es ENCABEZADO DE PRODUCTOS")
            }
        }
        
        // Segunda pasada: clasificar bloques
        for ((index, block) in textBlocks.withIndex()) {
            val blockCenterY = (block.boundingBox?.top ?: 0) + ((block.boundingBox?.bottom ?: 0) - (block.boundingBox?.top ?: 0)) / 2
            val texto = block.text.replace("\n", " ")
            val textUpper = texto.uppercase()
            
            Log.d(TAG, "Block[$index] Y=$blockCenterY → '$texto'")
            
            when {
                // Si es identificado como dinero, va a footer SIEMPRE
                index in moneyBlockIndices -> {
                    footerBlocks.add(block)
                    Log.d(TAG, "        ✓ ABAJO (DINERO DETECTADO)")
                }
                // Si es encabezado de productos, va a productos
                index in productHeaderIndices -> {
                    productBlocks.add(block)
                    Log.d(TAG, "        ✓ CENTRO (ENCABEZADO PRODUCTOS)")
                }
                // Si hay dinero después, cualquier bloque numérico va a footer
                moneyBlockIndices.isNotEmpty() && index > moneyBlockIndices.minOrNull()!! -> {
                    if (Regex("[0-9.,]{5,}").containsMatchIn(texto)) {
                        footerBlocks.add(block)
                        Log.d(TAG, "        ✓ ABAJO (DESPUÉS DE DINERO + NÚMEROS)")
                    } else {
                        productBlocks.add(block)
                        Log.d(TAG, "        ✓ CENTRO (DESPUÉS DE DINERO)")
                    }
                }
                // Clasificar por posición Y si hay encabezado de productos
                productHeaderIndices.isNotEmpty() -> {
                    val productHeaderY = textBlocks[productHeaderIndices.minOrNull()!!].boundingBox?.top ?: (imageHeight / 3)
                    when {
                        blockCenterY < productHeaderY -> {
                            headerBlocks.add(block)
                            Log.d(TAG, "        ✓ ARRIBA (ANTES DE ENCABEZADO PRODUCTOS)")
                        }
                        else -> {
                            productBlocks.add(block)
                            Log.d(TAG, "        ✓ CENTRO (DESPUÉS DE ENCABEZADO)")
                        }
                    }
                }
                // Si no hay referencias, usar posición Y
                blockCenterY < quarterY -> {
                    headerBlocks.add(block)
                    Log.d(TAG, "        ✓ ARRIBA (POR POSICIÓN Y)")
                }
                blockCenterY < threeQuarterY -> {
                    productBlocks.add(block)
                    Log.d(TAG, "        ✓ CENTRO (POR POSICIÓN Y)")
                }
                else -> {
                    footerBlocks.add(block)
                    Log.d(TAG, "        ✓ ABAJO (POR POSICIÓN Y)")
                }
            }
        }
        
        Log.d(TAG, "\nResumen clasificación:")
        Log.d(TAG, "  • Bloques ARRIBA: ${headerBlocks.size}")
        Log.d(TAG, "  • Bloques CENTRO: ${productBlocks.size}")
        Log.d(TAG, "  • Bloques ABAJO: ${footerBlocks.size}")
        
        // Limpiar header blocks removiendo montos que hayan pasado la clasificación
        val cleanedHeaderBlocks = cleanHeaderBlocks(headerBlocks)
        Log.d(TAG, "  • Bloques ARRIBA después de limpiar: ${cleanedHeaderBlocks.size}")
        
        // Inicializar variables
        var invoiceType = ""
        var puntoVenta = ""
        var numeroComprobante = ""
        var date = ""
        var cae = ""
        var vencimientoCAE = ""
        var supplierName = ""
        var supplierVat = ""
        var supplierIVA = ""
        var supplierDomicilio = ""
        var subtotal = 0.0
        var ivaTotal = 0.0
        var total = 0.0
        val invoiceLines = mutableListOf<InvoiceLine>()
        
        // ========== SECCIÓN ARRIBA: EMISOR Y FACTURA ==========
        Log.d(TAG, "\n" + "-".repeat(60))
        Log.d(TAG, "EXTRAYENDO SECCIÓN ARRIBA (EMISOR Y FACTURA)")
        Log.d(TAG, "-".repeat(60))
        
        val headerText = headerBlocks.joinToString("\n") { it.text }
        val headerTextUpper = headerText.uppercase()
        Log.d(TAG, "Texto de sección arriba:\n$headerText\n")
        
        // Nombre del emisor usando función mejorada con bloques limpios
        supplierName = extractSupplierName(cleanedHeaderBlocks)
        if (supplierName.isNotEmpty()) {
            Log.d(TAG, "✓ Proveedor extraído: '$supplierName'")
        } else {
            Log.d(TAG, "⚠ No se pudo extraer nombre del proveedor")
        }
        
        // CUIT con validación mejorada
        Log.d(TAG, "Buscando CUIT en texto...")
        supplierVat = validateAndExtractCUIT(headerTextUpper) ?: ""
        if (supplierVat.isNotEmpty()) {
            Log.d(TAG, "✓ CUIT válido extraído: $supplierVat")
        } else {
            Log.d(TAG, "⚠ CUIT no encontrado o inválido")
            // Intento adicional: buscar patrones de CUIT sin validación strict
            val cuitPattern = Regex("([0-9]{2})[.\\-\\s]*([0-9]{8})[.\\-\\s]*([0-9])")
            cuitPattern.find(headerTextUpper)?.let {
                Log.d(TAG, "  → Patrón CUIT encontrado pero no pasó validación: ${it.value}")
            }
        }
        
        // Domicilio (línea que contiene palabras de domicilio)
        val addressPattern = Regex("\\b(calle|avenue|av\\.?|avenida|número|n°|piso|depto\\.?|departamento|localidad|provincia)\\b", RegexOption.IGNORE_CASE)
        for (block in headerBlocks.sortedBy { it.boundingBox?.top ?: 0 }) {
            val text = block.text.trim().uppercase()
            if (addressPattern.containsMatchIn(text) && supplierDomicilio.isEmpty()) {
                supplierDomicilio = block.text.trim()
                Log.d(TAG, "✓ Domicilio extraído: '$supplierDomicilio'")
            }
        }
        
        // Condición IVA
        when {
            headerTextUpper.contains("RESPONSABLE INSCRIPTO") -> {
                supplierIVA = "IVA Responsable Inscripto"
                Log.d(TAG, "✓ Condición IVA: $supplierIVA")
            }
            headerTextUpper.contains("MONOTRIBUTISTA") -> {
                supplierIVA = "Monotributista"
                Log.d(TAG, "✓ Condición IVA: $supplierIVA")
            }
        }
        
        // ========== EXTRAYENDO DATOS DE FACTURA ==========
        Log.d(TAG, "\n" + "-".repeat(60))
        Log.d(TAG, "EXTRAYENDO DATOS DE FACTURA")
        Log.d(TAG, "-".repeat(60))
        
        // Usar la función mejorada de comprobante
        extractComprobanteArgentino(headerTextUpper)?.let { compData ->
            invoiceType = compData.tipo
            puntoVenta = compData.puntoVenta
            numeroComprobante = compData.numero
            Log.d(TAG, "✓ Comprobante: Tipo=${compData.tipo}, PV=${compData.puntoVenta}, Num=${compData.numero}")
        } ?: run {
            Log.d(TAG, "⚠ No se encontró comprobante en formato esperado")
        }
        
        // Fecha mejorada
        val fechaPattern = Regex("(\\d{1,2})[/-](\\d{1,2})[/-](\\d{4})")
        fechaPattern.find(headerText)?.let { match ->
            val fechaStr = "${match.groupValues[1]}/${match.groupValues[2]}/${match.groupValues[3]}"
            date = parseAndValidateDate(fechaStr) ?: ""
            if (date.isNotEmpty()) {
                Log.d(TAG, "✓ Fecha extraída: $date")
            }
        }
        
        // CAE (14 dígitos)
        val caePattern = Regex("(?:CAE|C\\.A\\.E\\.)[:\\s]*-?\\s*0*(\\d{14})")
        caePattern.find(headerTextUpper)?.let {
            cae = it.groupValues[1]
            Log.d(TAG, "✓ CAE extraído: $cae")
        }
        
        // ========== SECCIÓN CENTRAL: PRODUCTOS ==========
        Log.d(TAG, "\n" + "-".repeat(60))
        Log.d(TAG, "EXTRAYENDO SECCIÓN CENTRAL (PRODUCTOS)")
        Log.d(TAG, "-".repeat(60))
        Log.d(TAG, "Total bloques en sección: ${productBlocks.size}\n")
        
        for ((idx, block) in productBlocks.withIndex()) {
            val blockText = block.text.trim()
            Log.d(TAG, "Bloque $idx: '$blockText'")
            
            // Saltear encabezados
            if (isHeaderLine(blockText)) {
                Log.d(TAG, "    → SALTADO (es encabezado)")
                continue
            }
            
            // Intentar parsear como línea de producto
            parseProductLine(blockText, idx)?.let { productInfo ->
                invoiceLines.add(
                    InvoiceLine(
                        description = productInfo.description,
                        barcode = "",
                        quantity = productInfo.quantity,
                        unitPrice = productInfo.unitPrice,
                        totalPrice = productInfo.totalPrice
                    )
                )
                Log.d(TAG, "    ✓ PRODUCTO AGREGADO:")
                Log.d(TAG, "      Desc: ${productInfo.description}")
                Log.d(TAG, "      Qty: ${productInfo.quantity} | Price: $${productInfo.unitPrice} | Total: $${productInfo.totalPrice}")
            } ?: run {
                Log.d(TAG, "    ⚠ No se pudo parsear como producto")
            }
        }
        
        Log.d(TAG, "\nTotal de productos extraídos: ${invoiceLines.size}")
        
        // ========== EXTRAER TOTALES (desde bloques finales) ==========
        Log.d(TAG, "\n" + "-".repeat(60))
        Log.d(TAG, "EXTRAYENDO TOTALES")
        Log.d(TAG, "-".repeat(60))
        
        val footerText = footerBlocks.joinToString("\n") { it.text }
        val footerTextUpper = footerText.uppercase()
        
        val subtotalPattern = Regex("(?:SUBTOTAL|NETO|SUB\\s*TOTAL)[:\\s]*\\$?\\s*([\\d.,]+)")
        subtotalPattern.find(footerTextUpper)?.let {
            subtotal = parseArgentineNumber(it.groupValues[1]) ?: 0.0
            Log.d(TAG, "✓ Subtotal: $subtotal")
        }
        
        // IVA usando función mejorada (evita duplicados)
        val ivaMap = extractIVATotals(footerTextUpper)
        ivaTotal = calculateTotalIVA(ivaMap)
        if (ivaMap.isNotEmpty()) {
            Log.d(TAG, "✓ IVA desglosado: $ivaMap")
            Log.d(TAG, "  Total IVA: $ivaTotal")
        }
        
        val totalPattern = Regex("(?:TOTAL|IMPORTE\\s*TOTAL)[:\\s]*\\$?\\s*([\\d.,]+)")
        totalPattern.find(footerTextUpper)?.let {
            total = parseArgentineNumber(it.groupValues[1]) ?: 0.0
            Log.d(TAG, "✓ Total: $total")
        }
        
        Log.d(TAG, "\n" + "=".repeat(60))
        Log.d(TAG, "RESUMEN FINAL")
        Log.d(TAG, "=".repeat(60))
        Log.d(TAG, "Proveedor: '$supplierName' (CUIT: $supplierVat)")
        Log.d(TAG, "Factura: Tipo=$invoiceType PV=$puntoVenta Num=$numeroComprobante")
        Log.d(TAG, "Fecha: $date | CAE: $cae")
        Log.d(TAG, "Productos: ${invoiceLines.size} items")
        for ((i, item) in invoiceLines.withIndex()) {
            Log.d(TAG, "  [$i] ${item.description}: ${item.quantity} x $${item.unitPrice} = $${item.totalPrice}")
        }
        Log.d(TAG, "Totales: Subtotal=$subtotal, IVA=$ivaTotal, Total=$total")
        Log.d(TAG, "=".repeat(60))
        
        return Invoice(
            supplierName = supplierName,
            supplierVat = supplierVat,
            supplierCondicionIVA = supplierIVA,
            supplierDomicilio = supplierDomicilio,
            invoiceNumber = if (numeroComprobante.isNotEmpty()) "$puntoVenta-$numeroComprobante" else "",
            invoiceType = invoiceType,
            puntoVenta = puntoVenta,
            numeroComprobante = numeroComprobante,
            cae = cae,
            vencimientoCAE = vencimientoCAE,
            date = date,
            lines = invoiceLines,
            subtotal = if (subtotal > 0) subtotal else if (total > 0 && ivaTotal > 0) total - ivaTotal else 0.0,
            ivaTotal = ivaTotal,
            total = total
        )
    }
    
    fun close() {
        recognizer.close()
    }
}
