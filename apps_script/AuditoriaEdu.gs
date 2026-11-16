/**
 * Auditoría Edu — Puente Google Sheets → Supabase (directo, vía PostgREST).
 *
 * Archivo: SAA · Hoja: DATOS
 *
 * Configuración (una sola vez):
 *   1) En el editor, "Configuración del proyecto" (engranaje):
 *      Script Properties:
 *        SUPABASE_URL = https://srawajdbyfipekprtmvb.supabase.co
 *        SUPABASE_KEY = service_role key (Supabase → Settings → API)
 *   2) Activadores (reloj):
 *        Función: onFormSubmitTrigger
 *        Evento: Al enviar un formulario
 */

// ====== Config ======
const SHEET_NAME = 'DATOS';
const SUPABASE_TABLE = 'registro_movimiento';

// ====== Entry points ======
function onFormSubmitTrigger(e) {
  const sheet = e.range.getSheet();
  if (sheet.getName() !== SHEET_NAME) return;
  procesarFila_(sheet, e.range.getRow());
}

function onChangeTrigger(e) {
  if (!e || e.changeType !== 'INSERT_ROW') return;
  const sheet = _getSheet();
  if (SpreadsheetApp.getActiveSheet().getName() !== SHEET_NAME) return;
  procesarFila_(sheet, sheet.getLastRow());
}

function enviarUltimasNFilas(n) {
  n = n || 10;
  const sheet = _getSheet();
  const last = sheet.getLastRow();
  const from = Math.max(2, last - n + 1);
  for (let r = from; r <= last; r++) {
    procesarFila_(sheet, r);
    Utilities.sleep(150);
  }
}

// ====== Core ======
function procesarFila_(sheet, rowNumber) {
  if (rowNumber < 2) return; // skip header
  const values = sheet.getRange(rowNumber, 1, 1, 19).getValues()[0];

  // Validaciones mínimas antes de postear
  const tipo = _normTipo(values[3]);          // D
  const codigo = String(values[6] || '').trim();  // G
  const comprobante = String(values[12] || '').trim(); // M

  if (!tipo) {
    _logResultado(sheet, rowNumber, { code: 0, text: 'skip: tipo invalido' });
    return;
  }
  if (!codigo) {
    _logResultado(sheet, rowNumber, { code: 0, text: 'skip: sin codigo' });
    return;
  }

  // Payload con los nombres exactos de las columnas de Postgres
  const payload = {
    creado_en_origen:   _isoAR(values[0]),                        // A
    email_carga:        String(values[1] || '').slice(0, 160),    // B
    nombre_carga:       String(values[2] || '').slice(0, 120),    // C
    tipo:               tipo,                                      // D
    sector_salida:      String(values[4] || '').slice(0, 60),     // E
    sector_entrada:     String(values[5] || '').slice(0, 60),     // F
    codigo:             codigo.slice(0, 50),                       // G
    descripcion:        String(values[7] || '').slice(0, 160),    // H
    cantidad_bultos:    _toInt(values[8]),                         // I
    unidades_por_bulto: _toInt(values[9]),                         // J
    unidades_sueltas:   _toInt(values[10]),                        // K
    observaciones:      String(values[11] || ''),                  // L
    comprobante:        comprobante.slice(0, 30),                  // M
    // N (cantidad total): la BD lo recalcula como columna generada
    estado_concil:      String(values[14] || '').trim().toUpperCase().slice(0, 20),  // O
    estado_real:        String(values[15] || '').trim().toUpperCase().slice(0, 40),  // P
    obs_cande:          String(values[16] || ''),                  // Q
    flag_g3:            String(values[17] || '').slice(0, 30),    // R
    ref_bejerman:       String(values[18] || '').slice(0, 30),    // S
  };

  const resp = _postASupabase(payload);
  _logResultado(sheet, rowNumber, resp);
}

function _postASupabase(payload) {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty('SUPABASE_URL');
  const key = props.getProperty('SUPABASE_KEY');
  if (!url || !key) {
    throw new Error('Faltan SUPABASE_URL o SUPABASE_KEY en Script Properties.');
  }
  const endpoint = url.replace(/\/$/, '') + '/rest/v1/' + SUPABASE_TABLE;
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'apikey': key,
      'Authorization': 'Bearer ' + key,
      'Prefer': 'return=minimal',  // ahorra bytes
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };
  try {
    const response = UrlFetchApp.fetch(endpoint, options);
    return { code: response.getResponseCode(), text: response.getContentText() };
  } catch (err) {
    return { code: 0, text: 'fetch_failed: ' + err.message };
  }
}

// ====== Utilidades ======
function _isoAR(v) {
  if (v instanceof Date) {
    return Utilities.formatDate(v, 'America/Argentina/Buenos_Aires',
                                "yyyy-MM-dd'T'HH:mm:ssXXX");
  }
  return String(v || '');
}

function _toInt(v) {
  if (v === '' || v === null || v === undefined) return 0;
  const n = parseInt(v, 10);
  return isNaN(n) ? 0 : n;
}

function _normTipo(s) {
  const t = String(s || '').trim().toLowerCase();
  if (t.indexOf('env') === 0) return 'envio';
  if (t.indexOf('rec') === 0) return 'recibo';
  return null;
}

function _getSheet() {
  const s = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!s) throw new Error('No encuentro la hoja: ' + SHEET_NAME);
  return s;
}

function _logResultado(sheet, row, resp) {
  try {
    const col = 20; // columna T — log
    const stamp = Utilities.formatDate(new Date(), 'America/Argentina/Buenos_Aires',
                                       'yyyy-MM-dd HH:mm:ss');
    let marker = '';
    if (resp.code === 201) marker = 'OK';
    else if (resp.code === 409) marker = 'DUP';
    else if (resp.code === 0)   marker = resp.text.startsWith('skip:') ? 'SKIP' : 'ERR';
    else                        marker = 'ERR';
    const line = '[' + stamp + '] ' + marker + ' HTTP ' + resp.code
               + ' ' + (resp.text || '').slice(0, 200);
    sheet.getRange(row, col).setValue(line);
  } catch (e) { /* hoja protegida: no interrumpir */ }
}

// ====== Diagnóstico ======
function test_ping() {
  const resp = _postASupabase({
    creado_en_origen: new Date().toISOString(),
    email_carga: 'test@local',
    nombre_carga: 'PING',
    tipo: 'envio',
    sector_salida: 'Produccion',
    sector_entrada: 'G1-LOGISTICA',
    codigo: 'TEST-' + Date.now(),
    descripcion: 'ping de conectividad',
    cantidad_bultos: 0,
    unidades_por_bulto: 0,
    unidades_sueltas: 0,
    comprobante: 'PING-' + Date.now(),
  });
  Logger.log('HTTP %s · %s', resp.code, resp.text);
}
