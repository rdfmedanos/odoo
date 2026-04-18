package com.jaz.gepyco.data.ocr

import android.util.Log
import kotlin.math.max

private const val TAG = "OcrUtils"

/**
 * Utilidad para parsear números argentinos con múltiples formatos
 * 
 * Soporta:
 * - "25,50" → 25.50
 * - "1.500,00" → 1500.00 (con separador de miles)
 * - "$1.234.567,89" → 1234567.89 (con símbolo de moneda)
 * - "1,500" → 1500 (cuando coma es separador de miles)
 */
fun parseArgentineNumber(text: String): Double? {
    if (text.isBlank()) return null
    
    // Remover símbolos de moneda y espacios
    val cleaned = text.trim()
        .replace(Regex("[^0-9,.]"), "")
        .trim()
    
    if (cleaned.isEmpty()) return null
    
    // Encontrar posiciones del último separador
    val lastCommaIdx = cleaned.lastIndexOf(',')
    val lastDotIdx = cleaned.lastIndexOf('.')
    
    // Lógica: el último separador a 2-3 posiciones del final es decimal
    return when {
        // Patrón: "1.234,56" → punto=miles, coma=decimal
        lastCommaIdx > lastDotIdx && lastCommaIdx >= 0 &&
        cleaned.length - lastCommaIdx == 3 -> {
            cleaned.replace(".", "")
                .replace(",", ".")
                .toDoubleOrNull()
        }
        
        // Patrón: "1,234.56" → coma=miles, punto=decimal
        lastDotIdx > lastCommaIdx && lastDotIdx >= 0 &&
        cleaned.length - lastDotIdx == 3 -> {
            cleaned.replace(",", "")
                .toDoubleOrNull()
        }
        
        // Patrón: solo un separador, preferir coma como decimal
        lastCommaIdx >= 0 && lastDotIdx < 0 && cleaned.length - lastCommaIdx <= 3 -> {
            cleaned.replace(",", ".")
                .toDoubleOrNull()
        }
        
        // Patrón: solo punto, probablemente es decimal
        lastDotIdx >= 0 && lastCommaIdx < 0 && cleaned.length - lastDotIdx <= 3 -> {
            cleaned.toDoubleOrNull()
        }
        
        // Sin separadores identificables
        else -> cleaned.toDoubleOrNull()
    }.also {
        Log.d(TAG, "parseArgentineNumber('$text') → $it")
    }
}

/**
 * Valida y extrae CUIT argentino
 * 
 * El CUIT tiene siempre:
 * - Exactamente 11 dígitos
 * - Formato: XX-XXXXXXXX-X (dígito verificador incluido)
 * - No comienza con 0
 */
fun validateAndExtractCUIT(text: String): String? {
    if (text.isBlank()) return null
    
    // Múltiples patrones para extraer CUIT
    val cuitPatterns = listOf(
        // Patrón 1: "CUIT: 30-12345678-9" o "CUIT 30123456789"
        Regex(
            "(?:CUIT|C\\.U\\.I\\.T\\.)[\\s:]*[-\\s]*([0-9]{2})[-\\s]*([0-9]{8})[-\\s]*([0-9])",
            RegexOption.IGNORE_CASE
        ),
        // Patrón 2: "CUIT 30123456789" (sin separadores)
        Regex(
            "(?:CUIT|C\\.U\\.I\\.T\\.)[\\s:]*[-\\s]*([0-9]{11})",
            RegexOption.IGNORE_CASE
        ),
        // Patrón 3: Números solos que parezcan CUIT (al lado de texto clave)
        Regex(
            "(?:CUIT|C\\.U\\.I\\.T\\.|RESPONSABLE)[\\s:]*[-\\s]*([0-9]{2})[.\\-\\s]*([0-9]{8})[.\\-\\s]*([0-9])",
            RegexOption.IGNORE_CASE
        )
    )
    
    for (pattern in cuitPatterns) {
        val match = pattern.find(text.uppercase())
        if (match != null) {
            val cuitCandidate = when {
                match.groupValues.size == 4 -> {
                    // Formato con separadores: XX-XXXXXXXX-X
                    match.groupValues[1] + match.groupValues[2] + match.groupValues[3]
                }
                match.groupValues.size == 2 -> {
                    // Formato sin separadores: XXXXXXXXXXX
                    match.groupValues[1]
                }
                else -> continue
            }
            
            // Validar que tenga exactamente 11 dígitos
            if (cuitCandidate.length != 11) continue
            if (!cuitCandidate.matches(Regex("[0-9]{11}"))) continue
            
            // Validar que no comience con 0
            if (cuitCandidate[0] == '0') {
                Log.w(TAG, "CUIT inválido (comienza con 0): $cuitCandidate")
                continue
            }
            
            // Validar dígito verificador
            if (validateCUITChecksum(cuitCandidate)) {
                Log.d(TAG, "CUIT válido extraído: $cuitCandidate (patrón encontrado)")
                return cuitCandidate
            } else {
                Log.w(TAG, "CUIT inválido (checksum falló): $cuitCandidate")
            }
        }
    }
    
    Log.d(TAG, "No se encontró CUIT válido en el texto")
    return null
}

/**
 * Valida el dígito verificador del CUIT
 * 
 * Algoritmo CUIT argentino:
 * - Multiplicar cada dígito por: 5,4,3,2,7,6,5,4,3,2
 * - Sumar todos los resultados
 * - Restar de 11
 * - El resultado es el dígito verificador (11 o 10 → 0)
 */
private fun validateCUITChecksum(cuit: String): Boolean {
    if (cuit.length != 11) return false
    
    try {
        val multipliers = intArrayOf(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
        var sum = 0
        
        for (i in 0..9) {
            val digit = cuit[i].toString().toIntOrNull() ?: return false
            sum += digit * multipliers[i]
        }
        
        val expectedCheckDigit = (11 - (sum % 11)) % 11
        val actualCheckDigit = cuit[10].toString().toIntOrNull() ?: return false
        
        return expectedCheckDigit == actualCheckDigit
    } catch (e: Exception) {
        Log.e(TAG, "Error validando CUIT: ${e.message}")
        return false
    }
}

/**
 * Extrae datos de comprobante con patrones flexibles
 * 
 * Soporta variaciones como:
 * - "FACTURA A - 01-00123"
 * - "F. B Nº 002/456"
 * - "Tipo A Punto 01 Número 00123"
 */
fun extractComprobanteArgentino(text: String): ComprobanteData? {
    if (text.isBlank()) return null
    
    val textUpper = text.uppercase()
    
    // Patrones en orden de especificidad
    val patterns = listOf(
        // Formato estándar: FACTURA A - 01-00123
        Pair(
            Regex("(?:FACTURA|FACT\\.?|F\\.?)[\\s:]*([ABC])\\s*[-/]?\\s*0*(\\d{1,5})\\s*[-/]\\s*0*(\\d{1,8})", 
                  RegexOption.IGNORE_CASE),
            "estándar"
        ),
        
        // Formato flexible: Tipo A Punto 01 Número 00123
        Pair(
            Regex(
                "(?:Tipo|T\\.?)\\s*([ABC]).*?(?:Punto|Pto\\.?)\\s*0*(\\d{1,5}).*?(?:Número|Num\\.?)\\s*0*(\\d{1,8})",
                setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
            ),
            "flexible"
        ),
        
        // Formato minimal: A-01-123
        Pair(
            Regex("\\b([ABC])\\s*-\\s*0*(\\d{1,5})\\s*-\\s*0*(\\d{1,8})\\b"),
            "minimal"
        )
    )
    
    for ((pattern, patternName) in patterns) {
        pattern.find(textUpper)?.let { match ->
            val tipo = match.groupValues[1]
            val pv = match.groupValues[2]
            val num = match.groupValues[3]
            
            if (tipo.isNotEmpty() && pv.isNotEmpty() && num.isNotEmpty()) {
                return ComprobanteData(tipo, pv, num).also {
                    Log.d(TAG, "Comprobante encontrado ($patternName): $it")
                }
            }
        }
    }
    
    Log.w(TAG, "No se encontró patrón de comprobante válido")
    return null
}

data class ComprobanteData(
    val tipo: String,     // A, B o C
    val puntoVenta: String,
    val numero: String
)

/**
 * Verifica si una línea es encabezado de tabla
 * 
 * Detecta:
 * - "CANTIDAD", "CANT.", "QTY"
 * - "DESCRIPCIÓN", "DESC.", "PRODUCTO"
 * - "PRECIO", "PRECIO UNITARIO", "P.U."
 * - Líneas de separadores ("----")
 */
fun isHeaderLine(text: String): Boolean {
    if (text.isBlank()) return false
    
    val textUpper = text.uppercase()
    
    val headerPatterns = listOf(
        Regex("\\b(CANTIDAD|CANT\\.?|QTY|UNIDAD|UOM)\\b", RegexOption.IGNORE_CASE),
        Regex("\\b(DESCRIPCIÓN|DESC\\.?|PRODUCTO|ITEM)\\b", RegexOption.IGNORE_CASE),
        Regex("\\b(PRECIO|PRECIO UNITARIO|PRECIOUNITARIO|P\\.U\\.?|VALOR|UNITARIO)\\b", RegexOption.IGNORE_CASE),
        Regex("\\b(TOTAL|IMPORTE|MONTO|SUBTOTAL|SUB TOTAL)\\b", RegexOption.IGNORE_CASE),
        Regex("\\b(IVA|IMPUESTO|ALICUOTA|TASA)\\b", RegexOption.IGNORE_CASE),
        // Línea completa de separadores
        Regex("^[-=\\s_]+$")
    )
    
    val matches = headerPatterns.count { it.containsMatchIn(textUpper) }
    val isSeparatorLine = Regex("^[-=\\s_]{3,}$").matches(textUpper)
    
    return matches >= 2 || isSeparatorLine
}

/**
 * Parsea fecha argentina con validación
 * 
 * Formatos soportados:
 * - "15/03/2024" (DD/MM/YYYY) ✓
 * - "15-3-2024" (con guión) ✓
 * - "32/13/2024" ✗ (inválido, mes/día fuera de rango)
 * 
 * Retorna: "DD/MM/YYYY" normalizado o null si es inválido
 */
fun parseAndValidateDate(dateStr: String): String? {
    if (dateStr.isBlank()) return null
    
    val datePattern = Regex("(\\d{1,2})[/-](\\d{1,2})[/-](\\d{4})")
    val match = datePattern.find(dateStr) ?: return null
    
    val day = match.groupValues[1].toIntOrNull() ?: return null
    val month = match.groupValues[2].toIntOrNull() ?: return null
    val year = match.groupValues[3].toIntOrNull() ?: return null
    
    // Validar rangos (Argentina usa DD/MM/YYYY)
    if (day !in 1..31 || month !in 1..12 || year !in 2000..2100) {
        Log.w(TAG, "Fecha fuera de rango: día=$day, mes=$month, año=$year")
        return null
    }
    
    // Validar día para mes específico
    val daysInMonth = intArrayOf(31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    
    // Validar bisiesto
    if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) {
        daysInMonth[1] = 29
    }
    
    if (day > daysInMonth[month - 1]) {
        Log.w(TAG, "Día inválido para mes $month: $day")
        return null
    }
    
    return String.format("%02d/%02d/%04d", day, month, year).also {
        Log.d(TAG, "Fecha válida: $it")
    }
}

/**
 * Extrae números de una línea de producto
 * 
 * Retorna lista de números parseados como argentinos
 */
fun extractNumbersFromProductLine(text: String): List<Double> {
    if (text.isBlank()) return emptyList()
    
    val numberMatches = Regex("([0-9][0-9,.\\s]*[0-9.,]|[0-9])").findAll(text)
    
    return numberMatches
        .map { it.value.trim() }
        .mapNotNull { parseArgentineNumber(it) }
        .toList()
}

/**
 * Extrae información de línea de producto con estructura conocida
 * 
 * Intenta detectar:
 * - Descripción
 * - Cantidad
 * - Precio unitario
 * - Total
 */
data class ProductLineInfo(
    val description: String,
    val quantity: Double,
    val unitPrice: Double,
    val totalPrice: Double
)

fun parseProductLine(
    text: String, 
    lineIndex: Int = 0
): ProductLineInfo? {
    if (text.isBlank()) return null
    
    Log.d(TAG, "Analizando línea de producto: '$text'")
    
    // Separar descripción de números
    val parts = text.split(Regex("\\s{2,}|\\s*-\\s*|\\s+@\\s*|\\s+x\\s*"))
    
    if (parts.isEmpty()) return null
    
    // Primera parte es probablemente la descripción
    val description = parts[0].trim()
    
    // Extraer números del resto
    val numberText = parts.drop(1).joinToString(" ")
    val numbers = extractNumbersFromProductLine(numberText)
    
    Log.d(TAG, "Descripción: '$description', Números: $numbers")
    
    // Lógica para asignar números a cantidad/precio
    return when {
        // Caso ideal: 3+ números (cantidad, precio unitario, total)
        numbers.size >= 3 -> {
            ProductLineInfo(
                description = description,
                quantity = numbers[0],
                unitPrice = numbers[1],
                totalPrice = numbers[2]
            )
        }
        
        // Caso común: 2 números (cantidad y precio, calculamos total)
        numbers.size == 2 -> {
            // Heurística: si el segundo número es muy grande (>100), probablemente sea
            // precio y el primero cantidad
            val quantity = numbers[0]
            val unitPrice = numbers[1]
            val totalPrice = quantity * unitPrice
            
            Log.d(TAG, "2 números detectados: qty=$quantity, price=$unitPrice, total=$totalPrice")
            
            ProductLineInfo(
                description = description,
                quantity = quantity,
                unitPrice = unitPrice,
                totalPrice = totalPrice
            )
        }
        
        // Caso incompleto: solo 1 número
        numbers.size == 1 -> {
            Log.w(TAG, "Solo 1 número detectado, no se puede determinar cantidad/precio")
            null
        }
        
        else -> {
            Log.w(TAG, "No se detectaron números en línea de producto")
            null
        }
    }
}

/**
 * Extrae totales de IVA evitando duplicados y agrupando por alícuota
 */
fun extractIVATotals(text: String): Map<Double, Double> {
    if (text.isBlank()) return emptyMap()
    
    val ivaByRate = mutableMapOf<Double, Double>()
    
    // Patrón: IVA 21% - $1000.00 o IVA 21% $1000.00
    val ivaDetailPattern = Regex(
        "(?:IVA|I\\.V\\.A\\.)[\\s:]*([\\d.,]+)\\s*%?\\s*[-$:]*\\s*([\\d.,]+)",
        RegexOption.IGNORE_CASE
    )
    
    ivaDetailPattern.findAll(text).forEach { match ->
        val rateStr = match.groupValues[1]
        val amountStr = match.groupValues[2]
        
        val rate = parseArgentineNumber(rateStr) ?: return@forEach
        val amount = parseArgentineNumber(amountStr) ?: return@forEach
        
        // Agrupar por tasa: si ya existe, mantener el primero encontrado
        // (evita duplicados de OCR)
        if (!ivaByRate.containsKey(rate)) {
            ivaByRate[rate] = amount
            Log.d(TAG, "IVA encontrado: $rate% = \$$amount")
        } else {
            Log.d(TAG, "IVA duplicado ignorado: $rate% = \$$amount")
        }
    }
    
    return ivaByRate
}

/**
 * Extrae el nombre del proveedor de forma mejorada
 * 
 * Busca:
 * 1. Líneas que contengan palabras como "EMPRESA", "S.A.", "SRL", "LTDA"
 * 2. Primeras líneas después de filtrar encabezados y números
 * 3. Líneas con longitud entre 5 y 100 caracteres
 */
fun extractSupplierName(headerBlocks: List<com.google.mlkit.vision.text.Text.TextBlock>): String {
    val sortedBlocks = headerBlocks.sortedBy { it.boundingBox?.top ?: 0 }
    
    // Patrones que indican nombre de empresa
    val businessPatterns = listOf(
        Regex("\\b(S\\.?A\\.?|SRL|LTDA|LLC|SA\\.?CO\\.?|SPRL)\\b", RegexOption.IGNORE_CASE),
        Regex("\\b(EMPRESA|SOCIEDAD|COMERCIO|INDUSTRIA|DISTRIBUIDORA)\\b", RegexOption.IGNORE_CASE)
    )
    
    // Palabras a evitar en nombres (identificadores, números de documento, etc.)
    val excludePatterns = listOf(
        Regex("^(FACTURA|NOTA|CRÉDITO|DÉBITO|REMITO|FACTURA\\sA|AFC|COMPROBANTE)", RegexOption.IGNORE_CASE),
        Regex("^\\d{2,}([-/]|$)"), // Números al inicio (puede ser punto venta)
        Regex("^(IVA|CUIT|AFIP|RESPONSABLE|CAE|C\\.A\\.E\\.)", RegexOption.IGNORE_CASE), // Identificadores legales
        Regex("^(TOTAL|SUBTOTAL|NETO|IMPORTE)", RegexOption.IGNORE_CASE), // Palabras de totales
        Regex("(CAE|C\\.A\\.E\\.)[\\s:]?[Nº#]*\\s*\\d{14}"), // CAE Nº: 30123456789012
        Regex("(VENCIMIENTO|VENC\\.?)\\s*CAE"), // Vencimiento CAE
        Regex("^[Nº#]?\\s*\\d{14}\\s*$") // Solo 14 dígitos (CAE puro)
    )
    
    // Patrones que indican que es un monto/número
    val moneyPatterns = listOf(
        Regex("^\\s*\\$?\\s*[0-9.,\\s]+\\s*$"), // Solo dinero: "$1.234,56"
        Regex("(TOTAL|SUBTOTAL|NETO|IMPORTE)\\s*[:\\$]?\\s*[0-9.,]+"), // "TOTAL: $1000"
        Regex("^[0-9]{1,2}\\s*[,.]\\s*[0-9]{2}\\s*$"), // Números cortos: "21,5" (IVA alícuota)
        Regex("^\\$?\\s*[0-9]+([.,][0-9]+)?\\s*\\$?\\s*$") // Monto puro con símbolo de moneda
    )
    
    // Primero buscar líneas que claramente contengan tipo de empresa
    for (block in sortedBlocks) {
        val text = block.text.trim()
        if (text.isEmpty() || text.length < 5 || text.length > 100) continue
        
        val textUpper = text.uppercase()
        
        // Saltar líneas que obviamente no son nombres
        if (excludePatterns.any { it.containsMatchIn(textUpper) }) {
            Log.d(TAG, "Descartando (patrón excluido): '$text'")
            continue
        }
        if (isHeaderLine(text)) continue
        if (moneyPatterns.any { it.containsMatchIn(text) }) continue
        
        // Si contiene patrón de empresa, es probablemente el nombre
        if (businessPatterns.any { it.containsMatchIn(textUpper) }) {
            Log.d(TAG, "Proveedor encontrado (patrón empresa): '$text'")
            return text
        }
    }
    
    // Si no encontró patrón de empresa, buscar primera línea válida
    for (block in sortedBlocks) {
        val text = block.text.trim()
        if (text.isEmpty() || text.length < 5 || text.length > 100) continue
        
        val textUpper = text.uppercase()
        
        // Saltar líneas que obviamente no son nombres
        if (excludePatterns.any { it.containsMatchIn(textUpper) }) {
            Log.d(TAG, "Descartando (patrón excluido): '$text'")
            continue
        }
        if (isHeaderLine(text)) continue
        if (moneyPatterns.any { it.containsMatchIn(text) }) {
            Log.d(TAG, "Descartando posible monto: '$text'")
            continue
        }
        
        // Saltar si es solo números o símbolos
        if (Regex("^[0-9\\-/\\.]+$").matches(text)) continue
        
        // Saltar si es principalmente números (más del 40% dígitos)
        val digitCount = text.count { it.isDigit() }
        if (digitCount.toDouble() / text.length > 0.4) {
            Log.d(TAG, "Descartando (principalmente números): '$text'")
            continue
        }
        
        Log.d(TAG, "Proveedor encontrado (primera línea válida): '$text'")
        return text
    }
    
    return ""
}

/**
 * Función de test: valida la extracción de nombre de proveedor
 * Útil para debugging de OCR
 */
fun testExtractSupplierName(headerBlocks: List<com.google.mlkit.vision.text.Text.TextBlock>): String {
    Log.d(TAG, "\n" + "=".repeat(60))
    Log.d(TAG, "TEST EXTRACT SUPPLIER NAME")
    Log.d(TAG, "=".repeat(60))
    
    val sortedBlocks = headerBlocks.sortedBy { it.boundingBox?.top ?: 0 }
    Log.d(TAG, "Total bloques: ${sortedBlocks.size}")
    
    for ((idx, block) in sortedBlocks.withIndex()) {
        val text = block.text.trim()
        val length = text.length
        val y = block.boundingBox?.top ?: 0
        val isHeader = isHeaderLine(text)
        val isTooShort = length < 5
        val isTooLong = length > 100
        
        Log.d(TAG, "[$idx] Y=$y | Len=$length | Header=$isHeader | Short=$isTooShort | Long=$isTooLong")
        Log.d(TAG, "     Texto: '$text'")
        
        if (!isHeader && !isTooShort && !isTooLong) {
            Log.d(TAG, "     → CANDIDATO VÁLIDO")
        } else {
            var reason = ""
            if (isHeader) reason += "esEncabezado "
            if (isTooShort) reason += "muyCorto "
            if (isTooLong) reason += "muyLargo"
            Log.d(TAG, "     → DESCARTADO ($reason)")
        }
    }
    
    Log.d(TAG, "=".repeat(60))
    
    val result = extractSupplierName(headerBlocks)
    Log.d(TAG, "RESULTADO: '$result'")
    Log.d(TAG, "=".repeat(60) + "\n")
    
    return result
}

/**
 * Limpia bloques header removiendo montos y líneas irrelevantes
 * Solo mantiene info de emisor: nombre, CUIT, dirección, etc.
 * 
 * MÁS AGRESIVO: rechaza cualquier línea que parezca sospechosa
 */
fun cleanHeaderBlocks(blocks: List<com.google.mlkit.vision.text.Text.TextBlock>): List<com.google.mlkit.vision.text.Text.TextBlock> {
    val moneyPatterns = listOf(
        Regex("(TOTAL|SUBTOTAL|NETO|IMPORTE)[\\s:\\$]*[0-9.,]+"), // Totales
        Regex("^\\$?\\s*[0-9.,]+\\s*\\$?\\s*$"), // Solo número con símbolo
        Regex("(IVA|I\\.V\\.A\\.)\\s*[0-9.,]+"), // IVA value
        Regex("^[0-9]{1,2}\\s*[,.]\\s*[0-9]{2}\\s*$"), // Pequeños números (alícuotas)
        Regex("[0-9]{4,}"), // Números grandes (probablemente montos o CAE)
        Regex("^\\s*\\$") // Comienza con símbolo de moneda
    )
    
    return blocks.filter { block ->
        val text = block.text.trim()
        val textUpper = text.uppercase()
        
        // Descartar líneas que sean principalmente números/montos
        val isMoney = moneyPatterns.any { it.containsMatchIn(textUpper) }
        
        // Descartar líneas que sean mainly numbers
        val digitCount = text.count { it.isDigit() }
        val digitRatio = if (text.isNotEmpty()) digitCount.toDouble() / text.length else 0.0
        val isMostlyNumbers = digitRatio > 0.3
        
        if (isMoney) {
            Log.d(TAG, "cleanHeaderBlocks: removiendo (monto): '$text'")
            false
        } else if (isMostlyNumbers) {
            Log.d(TAG, "cleanHeaderBlocks: removiendo (mostly numbers ${"%.0f".format(digitRatio * 100)}%): '$text'")
            false
        } else {
            true
        }
    }
}

/**
 * Calcula total de IVA desde el mapa de alícuotas
 */
fun calculateTotalIVA(ivaByRate: Map<Double, Double>): Double {
    return ivaByRate.values.sum()
}
