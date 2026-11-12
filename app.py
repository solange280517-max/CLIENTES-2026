"""De La Scala Consultores - Control de honorarios. Aplicativo web local (Flask + SQLite)."""
import os, io, re, json, uuid, sqlite3, secrets, zipfile, shutil, time, tempfile
from collections import defaultdict
from datetime import date, datetime
from flask import (Flask, g, request, session, redirect, url_for, render_template, flash,
                   send_file, abort, jsonify)
from jinja2 import DictLoader
from markupsafe import Markup, escape
from werkzeug.security import generate_password_hash, check_password_hash
from templates import TEMPLATES

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('DLS_DATA', os.path.join(BASE, 'datos'))
DBF = os.path.join(DATA, 'app.db')
COMP = os.path.join(DATA, 'comprobantes')
RESP = os.path.join(DATA, 'respaldos')
LOGO = os.path.join(DATA, 'logo.png')
for d in (DATA, COMP, RESP): os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.jinja_loader = DictLoader(TEMPLATES)
app.config.update(MAX_CONTENT_LENGTH=600 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=8 * 3600)
KEYF = os.path.join(DATA, 'secret.key')
if not os.path.exists(KEYF):
    with open(KEYF, 'w') as f: f.write(secrets.token_hex(32))
app.secret_key = open(KEYF).read().strip()

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']
METODOS = ['Yape', 'Transferencia bancaria', 'Efectivo', 'Otro']
EPS = 0.005

# ---------------------------------------------------------------- base de datos
SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, nombre TEXT, clave TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY, ruc TEXT UNIQUE NOT NULL, razon TEXT NOT NULL, representante TEXT,
  celular TEXT, honorario REAL NOT NULL DEFAULT 0, fecha_inicio TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'activo',
  fecha_baja TEXT, obs TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS periodos(cliente_id INTEGER, periodo TEXT, monto REAL NOT NULL, PRIMARY KEY(cliente_id, periodo));
CREATE TABLE IF NOT EXISTS pagos(id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes(id), periodo TEXT NOT NULL,
  monto REAL NOT NULL, fecha_pago TEXT, metodo TEXT, recibo_fisico TEXT, rh TEXT, comprobante TEXT, obs TEXT,
  importado INTEGER DEFAULT 0, creado TEXT, usuario TEXT);
CREATE TABLE IF NOT EXISTS auditoria(id INTEGER PRIMARY KEY, fecha TEXT, usuario TEXT, entidad TEXT, registro INTEGER, accion TEXT, detalle TEXT);
CREATE TABLE IF NOT EXISTS config(clave TEXT PRIMARY KEY, valor TEXT);
CREATE INDEX IF NOT EXISTS ix_pagos_cp ON pagos(cliente_id, periodo);
"""

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DBF)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(_):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    get_db().executescript(SCHEMA)
    get_db().commit()

def cfg(k, d=None):
    r = get_db().execute('SELECT valor FROM config WHERE clave=?', (k,)).fetchone()
    return r['valor'] if r else d

def set_cfg(k, v):
    get_db().execute('INSERT OR REPLACE INTO config VALUES(?,?)', (k, str(v)))

def audit(entidad, registro, accion, detalle):
    get_db().execute('INSERT INTO auditoria(fecha,usuario,entidad,registro,accion,detalle) VALUES(?,?,?,?,?,?)',
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session.get('user', '-'), entidad, registro, accion,
                      detalle if isinstance(detalle, str) else json.dumps(detalle, ensure_ascii=False)))

def diff(old, new, campos):
    out = {c: [old[c], new[c]] for c in campos if (old[c] or '') != (new[c] or '')}
    return out

# ---------------------------------------------------------------- utilidades
def hoy(): return date.today()
def mes_actual(): return hoy().strftime('%Y-%m')
def add_mes(p, n):
    y, m = int(p[:4]), int(p[5:7]) - 1 + n
    return f'{y + m // 12}-{m % 12 + 1:02d}'
def rango(a, b):
    while a <= b:
        yield a; a = add_mes(a, 1)
def lista_periodos():
    ini = min(cfg('control_desde', '2026-01'), '2025-01')
    return list(rango(ini, f'{hoy().year + 1}-12'))[::-1]
def lista_pagos():
    return lista_periodos() + [f'{y}-00' for y in range(hoy().year, 2023, -1)]
def num(s):
    try: return round(float(str(s).replace(',', '.').replace('S/', '').strip()), 2)
    except ValueError: return None
def pdate(s):
    try: return datetime.strptime(s, '%Y-%m-%d').strftime('%Y-%m-%d')
    except (ValueError, TypeError): return None

@app.template_filter('soles')
def f_soles(v): return 'S/ {:,.2f}'.format(v or 0)
@app.template_filter('mes_es')
def f_mes(p):
    if p and p.endswith('-00'): return f'DJ Anual {p[:4]}'
    return f'{MESES[int(p[5:7]) - 1]} {p[:4]}' if p and len(p) >= 7 else ''
@app.template_filter('fecha')
def f_fecha(s): return f'{s[8:10]}/{s[5:7]}/{s[:4]}' if s else '—'
@app.template_filter('badge')
def f_badge(estado):
    cls = {'PAGADO': 'ok', 'PENDIENTE': 'pen', 'PAGO PARCIAL': 'par', 'PAGO VENCIDO': 'ven'}.get(estado, 'pen')
    return Markup(f'<span class="b {cls}">{escape(estado)}</span>')

@app.context_processor
def ctx():
    return dict(estudio=cfg('estudio', 'De La Scala Consultores'), tiene_logo=os.path.exists(LOGO), logo_v=int(os.path.getmtime(LOGO)) if os.path.exists(LOGO) else 0, MESES=MESES, METODOS=METODOS, csrf_token=csrf_token,
                hoy=hoy().isoformat(), mes_actual=mes_actual(), periodos=lista_periodos() if session.get('uid') else [], periodos_pago=lista_pagos() if session.get('uid') else [])

def csrf_token():
    if 'csrf' not in session: session['csrf'] = secrets.token_hex(16)
    return session['csrf']

# ---------------------------------------------------------------- cálculo de cuentas
def cuentas(cid=None):
    """Devuelve una fila por cliente y periodo con acordado, pagado, saldo y estado."""
    db = get_db(); cur = mes_actual(); desde = cfg('control_desde', '2026-01'); lim = int(cfg('dia_limite', 10))
    cl = db.execute('SELECT * FROM clientes' + (' WHERE id=?' if cid else ''), (cid,) if cid else ()).fetchall()
    ov = {(r['cliente_id'], r['periodo']): r['monto'] for r in db.execute('SELECT * FROM periodos')}
    pg = defaultdict(list)
    for p in db.execute('SELECT * FROM pagos' + (' WHERE cliente_id=?' if cid else ''), (cid,) if cid else ()):
        pg[(p['cliente_id'], p['periodo'])].append(p)
    porcli = defaultdict(set)
    for (c, p) in list(pg): porcli[c].add(p)
    for (c, p) in ov:
        if p.endswith('-00'): porcli[c].add(p)
    rows = []
    for c in cl:
        ini = max(c['fecha_inicio'][:7], desde); fin = cur
        if c['estado'] == 'inactivo' and c['fecha_baja']: fin = min(cur, add_mes(c['fecha_baja'][:7], -1))
        pers = set(rango(ini, fin)) | porcli[c['id']] if ini <= fin else set(porcli[c['id']])
        for per in sorted(pers):
            ps = pg.get((c['id'], per), [])
            acord = ov.get((c['id'], per), 0 if per.endswith('-00') else c['honorario'])
            pagado = round(sum(p['monto'] for p in ps), 2)
            if acord <= 0 and pagado <= 0: continue
            saldo = round(max(acord - pagado, 0), 2)
            dl = date(int(per[:4]) + 1, 4, 30) if per.endswith('-00') else date(int(per[:4]), int(per[5:7]), min(lim, 28))
            vencido = saldo > EPS and hoy() > dl
            estado = 'PAGADO' if saldo <= EPS else 'PAGO PARCIAL' if pagado > EPS else 'PAGO VENCIDO' if vencido else 'PENDIENTE'
            fechas = [p['fecha_pago'] for p in ps if p['fecha_pago']]
            rows.append(dict(cid=c['id'], ruc=c['ruc'], razon=c['razon'], celular=c['celular'], periodo=per, acordado=acord,
                             pagado=pagado, saldo=saldo, estado=estado, vencido=vencido, limite=dl.isoformat(),
                             fecha=max(fechas) if fechas else '', npagos=len(ps),
                             metodos=', '.join(sorted({p['metodo'] for p in ps if p['metodo']})),
                             recibos=', '.join(p['recibo_fisico'] for p in ps if p['recibo_fisico']),
                             rhs=', '.join(p['rh'] for p in ps if p['rh']),
                             adjuntos=sum(1 for p in ps if p['comprobante'])))
    return rows

def es_deuda(r):
    if r['saldo'] <= EPS: return False
    return int(r['periodo'][:4]) < hoy().year if r['periodo'].endswith('-00') else r['periodo'] <= mes_actual()

def deudas(rows):
    por = {}
    for r in rows:
        if es_deuda(r):
            d = por.setdefault(r['cid'], dict(cid=r['cid'], ruc=r['ruc'], razon=r['razon'], celular=r['celular'], total=0, items=[]))
            d['total'] = round(d['total'] + r['saldo'], 2); d['items'].append(r)
    return sorted(por.values(), key=lambda d: -d['total'])

# ---------------------------------------------------------------- seguridad
FALLOS = {}

@app.before_request
def guard():
    if request.endpoint in (None, 'static'): return
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('_csrf', ''), session.get('csrf', '-')):
        abort(400)
    if request.endpoint in ('login', 'setup', 'logo'): return
    if get_db().execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0: return redirect(url_for('setup'))
    if not session.get('uid'): return redirect(url_for('login'))
    respaldo_auto()

@app.after_request
def headers(r):
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['X-Frame-Options'] = 'DENY'
    r.headers['Cache-Control'] = 'no-store'
    r.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    return r

def sesion(u):
    session.clear(); session.permanent = True
    session.update(uid=u['id'], user=u['usuario'], nombre=u['nombre'] or u['usuario'])

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]: return redirect(url_for('login'))
    if request.method == 'POST':
        us, nom, c1, c2 = (request.form.get(k, '').strip() for k in ('usuario', 'nombre', 'clave', 'clave2'))
        if not us or len(c1) < 8: flash('Usuario obligatorio y clave de al menos 8 caracteres.', 'err')
        elif c1 != c2: flash('Las claves no coinciden.', 'err')
        else:
            db.execute('INSERT INTO usuarios(usuario,nombre,clave) VALUES(?,?,?)', (us, nom, generate_password_hash(c1)))
            set_cfg('control_desde', '2026-01'); set_cfg('dia_limite', 10); set_cfg('alerta_meses', 2)
            db.commit(); flash('Usuario creado. Ya puede ingresar.', 'ok'); return redirect(url_for('login'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr; n, hasta = FALLOS.get(ip, (0, 0))
    if request.method == 'POST':
        if n >= 5 and time.time() < hasta:
            flash('Demasiados intentos. Espere 5 minutos.', 'err')
        else:
            u = get_db().execute('SELECT * FROM usuarios WHERE usuario=?', (request.form.get('usuario', '').strip(),)).fetchone()
            if u and check_password_hash(u['clave'], request.form.get('clave', '')):
                FALLOS.pop(ip, None); sesion(u); return redirect(url_for('inicio'))
            FALLOS[ip] = (n + 1 if time.time() < hasta or n < 5 else 1, time.time() + 300)
            flash('Usuario o clave incorrectos.', 'err')
    return render_template('login.html')

@app.route('/salir', methods=['POST'])
def salir():
    session.clear(); return redirect(url_for('login'))

def logo_pdf(maxw=130, maxh=60):
    if not os.path.exists(LOGO): return None
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(LOGO).getSize(); k = min(maxw / w, maxh / h)
    img = RLImage(LOGO, width=w * k, height=h * k); img.hAlign = 'LEFT'
    return img

@app.route('/logo')
def logo():
    if not os.path.exists(LOGO): abort(404)
    r = send_file(LOGO, mimetype='image/png'); r.headers['Cache-Control'] = 'private, max-age=3600'; return r

@app.route('/configuracion/logo', methods=['POST'])
def logo_subir():
    if request.form.get('quitar'):
        if os.path.exists(LOGO): os.remove(LOGO)
        audit('config', 0, 'quitar logo', '-'); get_db().commit(); flash('Logo eliminado.', 'ok'); return redirect(url_for('config'))
    fs = request.files.get('archivo')
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(fs.read(8 * 1024 * 1024))); im = im.convert('RGBA'); im.thumbnail((700, 700))
        im.save(LOGO, 'PNG'); audit('config', 0, 'cambiar logo', '-'); get_db().commit(); flash('Logo guardado.', 'ok')
    except Exception: flash('No se pudo leer la imagen. Use un archivo PNG o JPG.', 'err')
    return redirect(url_for('config'))

# ---------------------------------------------------------------- inicio
@app.route('/')
def inicio():
    mes = request.args.get('mes', mes_actual()); db = get_db(); rows = cuentas(); cur = mes_actual()
    m = [r for r in rows if r['periodo'] == mes]
    por_cobrar = round(sum(r['acordado'] for r in m), 2); recaudado = round(sum(r['pagado'] for r in m), 2)
    pendiente = round(sum(r['saldo'] for r in m), 2)
    k = dict(por_cobrar=por_cobrar, recaudado=recaudado, pendiente=pendiente,
             pagaron=sum(r['estado'] == 'PAGADO' for r in m), sin_registrar=sum(r['pagado'] <= EPS for r in m),
             pct=round(100 * recaudado / por_cobrar, 1) if por_cobrar else 0)
    dd = deudas(rows); k['con_deuda'] = len(dd)
    k['sin_emitir'] = db.execute("SELECT COUNT(*) FROM pagos WHERE importado=0 AND COALESCE(rh,'')='' AND COALESCE(recibo_fisico,'')=''").fetchone()[0]
    alertas = []; lim = int(cfg('dia_limite', 10)); am = int(cfg('alerta_meses', 2))
    venc = [r for r in rows if r['periodo'] == cur and r['vencido']]
    if venc: alertas.append(('err', f'{len(venc)} clientes tienen el honorario de {f_mes(cur)} vencido (límite día {lim}).'))
    elif 0 <= lim - hoy().day <= 3 and k['sin_registrar']:
        alertas.append(('warn', f'El plazo del mes vence en {lim - hoy().day} día(s) y hay {k["sin_registrar"]} cobros sin registrar.'))
    acum = [d for d in dd if len(d['items']) >= am]
    if acum: alertas.append(('err', f'{len(acum)} clientes acumulan {am} o más meses de deuda.'))
    if k['sin_emitir']: alertas.append(('warn', f'{k["sin_emitir"]} pagos recibidos aún no tienen RH ni recibo físico emitido.'))
    tendencia = []
    for p in list(rango(add_mes(cur, -5), cur)):
        mm = [r for r in rows if r['periodo'] == p]; a = sum(r['acordado'] for r in mm)
        tendencia.append((p, round(100 * sum(r['pagado'] for r in mm) / a) if a else 0))
    recientes = db.execute('SELECT p.*, c.razon, c.ruc FROM pagos p JOIN clientes c ON c.id=p.cliente_id ORDER BY p.id DESC LIMIT 8').fetchall()
    return render_template('inicio.html', k=k, mes=mes, alertas=alertas, tendencia=tendencia, recientes=recientes, deudores=dd[:8])

# ---------------------------------------------------------------- clientes
CAMPOS_CLI = ['ruc', 'razon', 'representante', 'celular', 'honorario', 'fecha_inicio', 'estado', 'fecha_baja', 'obs']

@app.route('/clientes')
def clientes():
    q = request.args.get('q', '').strip(); est = request.args.get('estado', '')
    sql, par = 'SELECT * FROM clientes WHERE 1=1', []
    if q: sql += ' AND (razon LIKE ? OR ruc LIKE ?)'; par += [f'%{q}%'] * 2
    if est: sql += ' AND estado=?'; par.append(est)
    lista = get_db().execute(sql + ' ORDER BY razon', par).fetchall()
    deuda = {d['cid']: d['total'] for d in deudas(cuentas())}
    return render_template('clientes.html', lista=lista, deuda=deuda, q=q, est=est)

def form_cliente(cid=None):
    db = get_db(); f = request.form
    d = dict(ruc=re.sub(r'\D', '', f.get('ruc', '')), razon=f.get('razon', '').strip().upper(),
             representante=f.get('representante', '').strip(), celular=f.get('celular', '').strip(),
             honorario=num(f.get('honorario', '0')), fecha_inicio=pdate(f.get('fecha_inicio')),
             estado=f.get('estado', 'activo'), fecha_baja=pdate(f.get('fecha_baja')) , obs=f.get('obs', '').strip())
    err = None
    if len(d['ruc']) != 11: err = 'El RUC debe tener 11 dígitos.'
    elif not d['razon']: err = 'Ingrese la razón social o nombre.'
    elif d['honorario'] is None or d['honorario'] < 0: err = 'Honorario mensual no válido.'
    elif not d['fecha_inicio']: err = 'Ingrese la fecha de inicio del servicio.'
    elif d['estado'] not in ('activo', 'inactivo'): err = 'Estado no válido.'
    elif db.execute('SELECT 1 FROM clientes WHERE ruc=? AND id<>?', (d['ruc'], cid or 0)).fetchone(): err = 'Ya existe un cliente con ese RUC.'
    if d['estado'] == 'activo': d['fecha_baja'] = None
    elif not d['fecha_baja']: d['fecha_baja'] = hoy().replace(day=1).isoformat()
    return d, err

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def cliente_nuevo():
    d = dict(estado='activo', fecha_inicio=hoy().replace(day=1).isoformat(), honorario='')
    if request.method == 'POST':
        d, err = form_cliente()
        if err: flash(err, 'err')
        else:
            db = get_db(); c = db.execute('INSERT INTO clientes(ruc,razon,representante,celular,honorario,fecha_inicio,estado,fecha_baja,obs,creado) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (d['ruc'], d['razon'], d['representante'], d['celular'], d['honorario'], d['fecha_inicio'], d['estado'], d['fecha_baja'], d['obs'], hoy().isoformat()))
            audit('cliente', c.lastrowid, 'crear', d); db.commit(); flash('Cliente registrado.', 'ok')
            return redirect(url_for('cliente_ver', cid=c.lastrowid))
    return render_template('cliente_form.html', c=d, nuevo=True)

@app.route('/clientes/<int:cid>/editar', methods=['GET', 'POST'])
def cliente_editar(cid):
    db = get_db(); c = db.execute('SELECT * FROM clientes WHERE id=?', (cid,)).fetchone() or abort(404)
    if request.method == 'POST':
        d, err = form_cliente(cid)
        if err: flash(err, 'err'); c = {**dict(c), **d}
        else:
            ch = diff(c, d, CAMPOS_CLI)
            db.execute('UPDATE clientes SET ruc=?,razon=?,representante=?,celular=?,honorario=?,fecha_inicio=?,estado=?,fecha_baja=?,obs=? WHERE id=?',
                       (*[d[k] for k in CAMPOS_CLI], cid))
            if ch: audit('cliente', cid, 'editar', ch)
            db.commit(); flash('Datos actualizados.', 'ok'); return redirect(url_for('cliente_ver', cid=cid))
    return render_template('cliente_form.html', c=c, nuevo=False)

def img_pdf(nombre, maxw=170, maxh=190):
    from PIL import Image
    from reportlab.platypus import Image as RLImage
    im = Image.open(os.path.join(COMP, os.path.basename(nombre))); im.thumbnail((900, 900))
    buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=80); buf.seek(0)
    w, h = im.size; k = min(maxw / w, maxh / h)
    return RLImage(buf, width=w * k, height=h * k)

@app.route('/clientes/<int:cid>/estado')
def estado_cuenta(cid):
    """PDF para enviar al cliente. Por defecto solo deuda; ?completo=1 historial; ?detalle=1 con pagos, recibos y comprobantes; ?anio=AAAA filtra."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    db = get_db(); c = db.execute('SELECT * FROM clientes WHERE id=?', (cid,)).fetchone() or abort(404)
    detalle = request.args.get('detalle') == '1'; completo = detalle or request.args.get('completo') == '1'
    anio = request.args.get('anio', '') if re.fullmatch(r'\d{4}', request.args.get('anio', '')) else ''
    rows = cuentas(cid)
    sel = [r for r in rows if (completo or es_deuda(r)) and (not anio or r['periodo'][:4] == anio)]
    st = getSampleStyleSheet(); sm = ParagraphStyle('sm', parent=st['Normal'], fontSize=8, leading=10); buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36)
    deuda = round(sum(r['saldo'] for r in rows if es_deuda(r)), 2)
    if detalle:
        cab = ['Periodo', 'Acordado', 'Pagado', 'Saldo', 'Estado', 'Recibo / RH']
        data = [cab] + [[f_mes(r['periodo']), f'S/ {r["acordado"]:,.2f}', f'S/ {r["pagado"]:,.2f}', f'S/ {r["saldo"]:,.2f}', r['estado'],
                         Paragraph(' · '.join(x for x in (('Recibo ' + r['recibos']) if r['recibos'] else '', ('RH ' + r['rhs']) if r['rhs'] else '') if x) or '—', sm)] for r in sel]
        data.append(['TOTAL', f'S/ {sum(r["acordado"] for r in sel):,.2f}', f'S/ {sum(r["pagado"] for r in sel):,.2f}', f'S/ {sum(r["saldo"] for r in sel if es_deuda(r)):,.2f}', '', ''])
        cw = [78, 62, 62, 62, 82, 177]
    else:
        data = [['Periodo', 'Acordado', 'Pagado', 'Saldo', 'Estado']] + [[f_mes(r['periodo']), f'S/ {r["acordado"]:,.2f}', f'S/ {r["pagado"]:,.2f}',
                f'S/ {r["saldo"]:,.2f}', r['estado']] for r in sel]
        data.append(['TOTAL' if completo else 'TOTAL ADEUDADO', f'S/ {sum(r["acordado"] for r in sel):,.2f}' if completo else '',
                     f'S/ {sum(r["pagado"] for r in sel):,.2f}' if completo else '', f'S/ {deuda if not anio else sum(r["saldo"] for r in sel if es_deuda(r)):,.2f}', ''])
        cw = [130, 90, 90, 90, 110]
    t = Table(data, repeatRows=1, colWidths=cw)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2D3D')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), .25, colors.grey), ('ALIGN', (1, 1), (3, -1), 'RIGHT'), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8ECF0')), ('FONTSIZE', (0, 0), (-1, -1), 8.5), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    lg = logo_pdf()
    titulo = 'Estado de cuenta de honorarios' + (' — con detalle de pagos' if detalle else ' (historial completo)' if completo else '') + (f' {anio}' if anio else '')
    cuerpo = ([lg, Spacer(1, 6)] if lg else []) + [Paragraph(f"<b>{cfg('estudio', 'De La Scala Consultores')}</b>", st['Title']), Paragraph(titulo, st['Heading2']),
              Paragraph(f'<b>Cliente:</b> {c["razon"]}<br/><b>RUC:</b> {c["ruc"]}<br/><b>Fecha de emisión:</b> {hoy():%d/%m/%Y}', st['Normal']), Spacer(1, 12)]
    cuerpo.append(t if sel else Paragraph('El cliente no registra deuda pendiente a la fecha.', st['Normal']))
    if detalle:
        pgs = [p for p in db.execute('SELECT * FROM pagos WHERE cliente_id=? ORDER BY periodo, COALESCE(fecha_pago, ""), id', (cid,)) if not anio or p['periodo'][:4] == anio]
        cuerpo += [Spacer(1, 16), Paragraph('Detalle de pagos recibidos', st['Heading3'])]
        if not pgs: cuerpo.append(Paragraph('No hay pagos registrados.', st['Normal']))
        for p in pgs:
            lineas = [f'<b>{f_mes(p["periodo"])}</b> — S/ {p["monto"]:,.2f}', f'Fecha de pago: {f_fecha(p["fecha_pago"])}', f'Método: {p["metodo"] or "—"}',
                      f'N° de recibo: {p["recibo_fisico"] or "—"}', f'N° de RH: {p["rh"] or "—"}']
            if p['obs'] and not p['importado']: lineas.append(f'Obs.: {escape(p["obs"])[:160]}')
            img = None
            if p['comprobante']:
                try:
                    img = img_pdf(p['comprobante']) if not p['comprobante'].endswith('.pdf') else Paragraph('Comprobante guardado en PDF (no se muestra aquí).', sm)
                except Exception: img = Paragraph('Comprobante no disponible.', sm)
            fila_ = Table([[Paragraph('<br/>'.join(lineas), sm), img or Paragraph('<i>Sin imagen de comprobante</i>', sm)]], colWidths=[290, 220])
            fila_.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'CENTER')]))
            cuerpo += [KeepTogether([fila_]), Spacer(1, 5)]
    cuerpo += [Spacer(1, 12), Paragraph('Montos expresados en soles (S/). Si ya realizó algún pago no reflejado, por favor envíenos su comprobante.', st['Italic'])]
    doc.build(cuerpo); buf.seek(0)
    nombre = re.sub(r'[^\w]+', '_', c['razon'])[:40]
    return send_file(buf, as_attachment=True, download_name=f'Estado_de_cuenta_{nombre}{"_" + anio if anio else ""}.pdf', mimetype='application/pdf')

@app.route('/clientes/<int:cid>')
def cliente_ver(cid):
    db = get_db(); c = db.execute('SELECT * FROM clientes WHERE id=?', (cid,)).fetchone() or abort(404)
    rows = cuentas(cid)
    pagos_ = db.execute('SELECT * FROM pagos WHERE cliente_id=? ORDER BY periodo DESC, id DESC', (cid,)).fetchall()
    return render_template('cliente_ver.html', c=c, anios=sorted({r['periodo'][:4] for r in rows}, reverse=True), rows=rows[::-1], pagos=pagos_, deuda=sum(r['saldo'] for r in rows if es_deuda(r)))

# ---------------------------------------------------------------- pagos
def guardar_comprobante(fs):
    """Valida y guarda imagen/PDF. Devuelve nombre de archivo o lanza ValueError."""
    raw = fs.read()
    if len(raw) > 15 * 1024 * 1024: raise ValueError('El comprobante supera 15 MB.')
    if raw[:4] == b'%PDF': nombre = uuid.uuid4().hex + '.pdf'; data = raw
    elif raw[:3] == b'\xff\xd8\xff' or raw[:4] == b'\x89PNG' or (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP') or raw[:3] == b'GIF':
        try:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))); im.thumbnail((2000, 2000))
            buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=85); data = buf.getvalue()
        except Exception: raise ValueError('La imagen no se pudo leer.')
        nombre = uuid.uuid4().hex + '.jpg'
    else: raise ValueError('Formato no permitido. Use JPG, PNG, WEBP o PDF.')
    with open(os.path.join(COMP, nombre), 'wb') as f: f.write(data)
    return nombre

def resolver_cliente(txt):
    m = re.match(r'\s*(\d{11})', txt or '')
    return get_db().execute('SELECT * FROM clientes WHERE ruc=?', (m.group(1),)).fetchone() if m else None

def procesar_pago(pid=None):
    """Valida el formulario y guarda. Devuelve (id, error)."""
    db = get_db(); f = request.form
    c = resolver_cliente(f.get('cliente'))
    per = f.get('periodo', ''); monto = num(f.get('monto')); acord = num(f.get('acordado'))
    fecha = pdate(f.get('fecha_pago')); metodo = f.get('metodo')
    if not c: return None, 'Seleccione un cliente de la lista.'
    if not re.fullmatch(r'\d{4}-\d{2}', per): return None, 'Seleccione el periodo.'
    if not acord or acord <= 0: return None, 'Ingrese el honorario del periodo.'
    if not monto or monto <= 0: return None, 'Ingrese el monto pagado.'
    if not fecha: return None, 'Ingrese la fecha de pago.'
    if metodo not in METODOS: return None, 'Seleccione el método de pago.'
    prev = db.execute('SELECT COALESCE(SUM(monto),0) FROM pagos WHERE cliente_id=? AND periodo=? AND id<>?', (c['id'], per, pid or 0)).fetchone()[0]
    saldo = round(acord - prev, 2)
    if saldo <= EPS: return None, f'{f_mes(per)} de este cliente ya está pagado por completo. No se puede duplicar el pago.'
    if monto > saldo + EPS: return None, f'El monto ({f_soles(monto)}) supera el saldo pendiente de {f_soles(saldo)}.'
    rf, rh = f.get('recibo_fisico', '').strip(), f.get('rh', '').strip()
    for col, val, nom in (('recibo_fisico', rf, 'recibo físico'), ('rh', rh, 'RH')):
        if val and db.execute(f'SELECT 1 FROM pagos WHERE {col}=? AND cliente_id<>? AND id<>?', (val, c['id'], pid or 0)).fetchone():
            return None, f'El {nom} {val} ya está registrado en otro cliente.'
    old = db.execute('SELECT * FROM pagos WHERE id=?', (pid,)).fetchone() if pid else None
    comp = old['comprobante'] if old else None
    try:
        fs = request.files.get('comprobante')
        if fs and fs.filename: comp = guardar_comprobante(fs)
        elif f.get('quitar_comp'): comp = None
    except ValueError as e: return None, str(e)
    if per.endswith('-00') or abs(acord - c['honorario']) > EPS: db.execute('INSERT OR REPLACE INTO periodos VALUES(?,?,?)', (c['id'], per, acord))
    else: db.execute('DELETE FROM periodos WHERE cliente_id=? AND periodo=?', (c['id'], per))
    d = dict(cliente_id=c['id'], periodo=per, monto=monto, fecha_pago=fecha, metodo=metodo, recibo_fisico=rf, rh=rh,
             comprobante=comp, obs=f.get('obs', '').strip())
    if pid:
        db.execute('UPDATE pagos SET cliente_id=?,periodo=?,monto=?,fecha_pago=?,metodo=?,recibo_fisico=?,rh=?,comprobante=?,obs=?,importado=0 WHERE id=?', (*d.values(), pid))
        audit('pago', pid, 'editar', diff(old, d, list(d)))
    else:
        pid = db.execute('INSERT INTO pagos(cliente_id,periodo,monto,fecha_pago,metodo,recibo_fisico,rh,comprobante,obs,creado,usuario) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                         (*d.values(), hoy().isoformat(), session.get('user'))).lastrowid
        audit('pago', pid, 'crear', {**d, 'cliente': c['razon']})
    db.commit()
    return pid, None

@app.route('/pagos/nuevo', methods=['GET', 'POST'])
def pago_nuevo():
    p = dict(periodo=request.args.get('periodo', mes_actual()), fecha_pago=hoy().isoformat(), metodo='Yape')
    cl = request.args.get('cliente')
    if cl and cl.isdigit():
        c = get_db().execute('SELECT ruc, razon FROM clientes WHERE id=?', (cl,)).fetchone()
        if c: p['cliente'] = f"{c['ruc']} — {c['razon']}"
    if request.method == 'POST':
        pid, err = procesar_pago()
        if not err: flash('Pago registrado correctamente.', 'ok'); return redirect(url_for('pagos'))
        flash(err, 'err'); p = request.form.to_dict()
    clist = get_db().execute("SELECT ruc, razon FROM clientes WHERE estado='activo' ORDER BY razon").fetchall()
    return render_template('pago_form.html', p=p, clist=clist, nuevo=True)

@app.route('/pagos/<int:pid>/editar', methods=['GET', 'POST'])
def pago_editar(pid):
    db = get_db(); r = db.execute('SELECT p.*, c.ruc, c.razon, c.honorario FROM pagos p JOIN clientes c ON c.id=p.cliente_id WHERE p.id=?', (pid,)).fetchone() or abort(404)
    if request.method == 'POST':
        _, err = procesar_pago(pid)
        if not err: flash('Pago actualizado.', 'ok'); return redirect(url_for('pagos'))
        flash(err, 'err'); p = {**request.form.to_dict(), 'id': pid, 'comprobante': r['comprobante']}
    else:
        ov = db.execute('SELECT monto FROM periodos WHERE cliente_id=? AND periodo=?', (r['cliente_id'], r['periodo'])).fetchone()
        p = {**dict(r), 'cliente': f"{r['ruc']} — {r['razon']}", 'acordado': ov['monto'] if ov else r['honorario']}
    clist = db.execute('SELECT ruc, razon FROM clientes ORDER BY razon').fetchall()
    return render_template('pago_form.html', p=p, clist=clist, nuevo=False)

@app.route('/pagos/<int:pid>/eliminar', methods=['POST'])
def pago_eliminar(pid):
    db = get_db(); r = db.execute('SELECT * FROM pagos WHERE id=?', (pid,)).fetchone() or abort(404)
    audit('pago', pid, 'eliminar', dict(r)); db.execute('DELETE FROM pagos WHERE id=?', (pid,)); db.commit()
    flash('Pago eliminado (queda registrado en el historial de modificaciones).', 'ok'); return redirect(url_for('pagos'))

@app.route('/api/cuenta')
def api_cuenta():
    c = resolver_cliente(request.args.get('cliente')); per = request.args.get('periodo', '')
    if not c: return jsonify(ok=False)
    ov = get_db().execute('SELECT monto FROM periodos WHERE cliente_id=? AND periodo=?', (c['id'], per)).fetchone()
    acord = ov['monto'] if ov else (0 if per.endswith('-00') else c['honorario'])
    prev = get_db().execute('SELECT COALESCE(SUM(monto),0) FROM pagos WHERE cliente_id=? AND periodo=? AND id<>?',
                            (c['id'], per, request.args.get('excluir', 0))).fetchone()[0]
    return jsonify(ok=True, acordado=acord, pagado=round(prev, 2), saldo=round(max(acord - prev, 0), 2))

@app.route('/comprobante/<int:pid>')
def comprobante(pid):
    r = get_db().execute('SELECT comprobante FROM pagos WHERE id=?', (pid,)).fetchone()
    if not r or not r['comprobante']: abort(404)
    return send_file(os.path.join(COMP, os.path.basename(r['comprobante'])))

@app.route('/pagos')
def pagos():
    a = request.args; db = get_db()
    sql = 'SELECT p.*, c.razon, c.ruc FROM pagos p JOIN clientes c ON c.id=p.cliente_id WHERE 1=1'; par = []
    if a.get('q'): sql += ' AND (c.razon LIKE ? OR c.ruc LIKE ?)'; par += [f"%{a['q'].strip()}%"] * 2
    if a.get('mes'): sql += ' AND substr(p.periodo,6,2)=?'; par.append(a['mes'])
    if a.get('anio'): sql += ' AND substr(p.periodo,1,4)=?'; par.append(a['anio'])
    if a.get('metodo'): sql += ' AND p.metodo=?'; par.append(a['metodo'])
    if a.get('recibo'): sql += ' AND p.recibo_fisico LIKE ?'; par.append(f"%{a['recibo'].strip()}%")
    if a.get('rh'): sql += ' AND p.rh LIKE ?'; par.append(f"%{a['rh'].strip()}%")
    if a.get('emision') == 'sin': sql += " AND p.importado=0 AND COALESCE(p.rh,'')='' AND COALESCE(p.recibo_fisico,'')=''"
    if a.get('emision') == 'con': sql += " AND (COALESCE(p.rh,'')<>'' OR COALESCE(p.recibo_fisico,'')<>'')"
    lista = db.execute(sql + " ORDER BY COALESCE(p.fecha_pago,'0') DESC, p.id DESC", par).fetchall()
    est = {(r['cid'], r['periodo']): r for r in cuentas()}
    items = [(p, est.get((p['cliente_id'], p['periodo']))) for p in lista]
    if a.get('estado'): items = [i for i in items if i[1] and i[1]['estado'] == a['estado']]
    pag = max(int(a.get('pag', 1)) if a.get('pag', '1').isdigit() else 1, 1); n = 50
    qs = '&'.join(f'{k}={v}' for k, v in a.items() if k != 'pag' and v)
    return render_template('pagos.html', items=items[(pag - 1) * n:pag * n], total=len(items), pag=pag, n=n, a=a, qs=qs,
                           suma=sum(i[0]['monto'] for i in items), anios=range(2024, hoy().year + 2))

@app.route('/deudas')
def deudas_view():
    dd = deudas(cuentas()); q = request.args.get('q', '').strip().upper()
    if q: dd = [d for d in dd if q in d['razon'] or q in d['ruc']]
    return render_template('deudas.html', dd=dd, total=sum(d['total'] for d in dd), q=q, am=int(cfg('alerta_meses', 2)))

# ---------------------------------------------------------------- reportes
def reporte_rows(a):
    tipo = a.get('tipo', 'mensual'); rows = cuentas()
    if tipo == 'anual':
        anio = a.get('anio', str(hoy().year)); rows = [r for r in rows if r['periodo'][:4] == anio]; titulo = f'Reporte anual {anio}'
    else:
        mes = a.get('mes', mes_actual()); rows = [r for r in rows if r['periodo'] == mes]; titulo = f'Reporte mensual — {f_mes(mes)}'
    if a.get('estado'): rows = [r for r in rows if r['estado'] == a['estado']]
    if a.get('q'): rows = [r for r in rows if a['q'].upper() in r['razon'] or a['q'] in r['ruc']]
    rows.sort(key=lambda r: (r['periodo'], r['razon']))
    return titulo, rows

COLS = ['RUC', 'Cliente', 'Periodo', 'Monto acordado', 'Monto pagado', 'Saldo pendiente', 'Fecha de pago', 'Método',
        'Recibo físico', 'N° RH', 'Comprobante', 'Estado']
def fila(r): return [r['ruc'], r['razon'], f_mes(r['periodo']), r['acordado'], r['pagado'], r['saldo'], f_fecha(r['fecha']) if r['fecha'] else '',
                     r['metodos'], r['recibos'], r['rhs'], 'Sí' if r['adjuntos'] else 'No', r['estado']]

@app.route('/reportes')
def reportes():
    a = request.args.to_dict(); titulo, rows = reporte_rows(a)
    tot = [sum(r[k] for r in rows) for k in ('acordado', 'pagado', 'saldo')]
    return render_template('reportes.html', rows=rows, titulo=titulo, tot=tot, a=a, anios=range(2024, hoy().year + 2),
                           qs='&'.join(f'{k}={v}' for k, v in a.items() if v))

@app.route('/reportes/exportar')
def exportar():
    a = request.args.to_dict(); titulo, rows = reporte_rows(a); fmt = a.get('fmt', 'xlsx')
    nombre = re.sub(r'[^\w]+', '_', titulo).strip('_')
    tot = ['', 'TOTAL', '', *[round(sum(r[k] for r in rows), 2) for k in ('acordado', 'pagado', 'saldo')], '', '', '', '', '', '']
    if fmt == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = Workbook(); ws = wb.active; ws.title = 'Reporte'
        ws.append([f"{cfg('estudio', 'De La Scala Consultores')} — {titulo}"]); ws['A1'].font = Font(bold=True, size=14); ws.append([])
        if os.path.exists(LOGO):
            from openpyxl.drawing.image import Image as XLImage
            xi = XLImage(LOGO); k = 48 / xi.height; xi.height, xi.width = 48, int(xi.width * k); ws.add_image(xi, 'H1'); ws.row_dimensions[1].height = 38
        ws.append(COLS)
        for c in ws[3]: c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='1F2D3D'); c.alignment = Alignment(horizontal='center')
        for r in rows: ws.append(fila(r))
        ws.append(tot)
        for c in ws[ws.max_row]: c.font = Font(bold=True)
        for row in ws.iter_rows(min_row=4, min_col=4, max_col=6):
            for c in row: c.number_format = '"S/" #,##0.00'
        for i, w in enumerate([13, 42, 16, 14, 14, 14, 13, 20, 14, 18, 13, 15], 1): ws.column_dimensions[chr(64 + i)].width = w
        ws.freeze_panes = 'A4'; ws.auto_filter.ref = f'A3:L{ws.max_row - 1}'
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f'{nombre}.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    buf = io.BytesIO(); doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=28, bottomMargin=24)
    st = getSampleStyleSheet(); cell = ParagraphStyle('c', fontSize=6.5, leading=8)
    data = [COLS[1:]] + [[Paragraph(str(v), cell) if i in (0, 6, 7, 8) else (f'{v:,.2f}' if isinstance(v, float) else v)
                          for i, v in enumerate(fila(r)[1:])] for r in rows]
    data.append(tot[1:])
    t = Table(data, repeatRows=1, colWidths=[150, 52, 52, 52, 52, 48, 60, 50, 60, 42, 62])
    t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 6.5), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2D3D')),
                           ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID', (0, 0), (-1, -1), .25, colors.grey),
                           ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
                           ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F3F5F7')])]))
    lg = logo_pdf(110, 45)
    doc.build(([lg, Spacer(1, 4)] if lg else []) + [Paragraph(f"<b>{cfg('estudio', 'De La Scala Consultores')}</b> — {titulo}", st['Title']),
               Paragraph(f'Emitido el {hoy().strftime("%d/%m/%Y")} · Montos en soles (S/)', st['Normal']), Spacer(1, 8), t])
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f'{nombre}.pdf', mimetype='application/pdf')

# ---------------------------------------------------------------- configuración, respaldos
def respaldar(ruta, con_comprobantes):
    tmp = tempfile.mktemp(suffix='.db'); src = sqlite3.connect(DBF); dst = sqlite3.connect(tmp)
    src.backup(dst); dst.close(); src.close()
    with zipfile.ZipFile(ruta, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(tmp, 'app.db')
        if con_comprobantes:
            for fn in os.listdir(COMP): z.write(os.path.join(COMP, fn), f'comprobantes/{fn}')
    os.remove(tmp)

def respaldo_auto():
    nombre = os.path.join(RESP, f'auto_{hoy():%Y%m%d}.zip')
    if not os.path.exists(nombre):
        respaldar(nombre, False)
        for f in sorted(os.listdir(RESP))[:-30]:
            if f.startswith('auto_'): os.remove(os.path.join(RESP, f))

@app.route('/configuracion', methods=['GET', 'POST'])
def config():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        set_cfg('estudio', f.get('estudio', '').strip() or 'De La Scala Consultores')
        set_cfg('dia_limite', min(max(int(f.get('dia_limite') or 10), 1), 28)); set_cfg('alerta_meses', max(int(f.get('alerta_meses') or 2), 1))
        if re.fullmatch(r'\d{4}-\d{2}', f.get('control_desde', '')): set_cfg('control_desde', f['control_desde'])
        audit('config', 0, 'editar', dict(f)); db.commit(); flash('Configuración guardada.', 'ok'); return redirect(url_for('config'))
    usuarios = db.execute('SELECT usuario, nombre FROM usuarios').fetchall()
    resp = sorted(os.listdir(RESP))[-5:]
    return render_template('config.html', c={k: cfg(k, d) for k, d in (('estudio', 'De La Scala Consultores'), ('dia_limite', 10), ('alerta_meses', 2), ('control_desde', '2026-01'))}, usuarios=usuarios, resp=resp)

@app.route('/configuracion/clave', methods=['POST'])
def cambiar_clave():
    db = get_db(); f = request.form; u = db.execute('SELECT * FROM usuarios WHERE id=?', (session['uid'],)).fetchone()
    if not check_password_hash(u['clave'], f.get('actual', '')): flash('La clave actual es incorrecta.', 'err')
    elif len(f.get('nueva', '')) < 8 or f['nueva'] != f.get('nueva2'): flash('La nueva clave debe tener 8+ caracteres y coincidir.', 'err')
    else:
        db.execute('UPDATE usuarios SET clave=? WHERE id=?', (generate_password_hash(f['nueva']), u['id'])); audit('usuario', u['id'], 'cambiar clave', '-')
        db.commit(); flash('Clave actualizada.', 'ok')
    return redirect(url_for('config'))

@app.route('/configuracion/usuario', methods=['POST'])
def nuevo_usuario():
    f = request.form; db = get_db()
    if not f.get('usuario', '').strip() or len(f.get('clave', '')) < 8: flash('Usuario y clave (8+ caracteres) obligatorios.', 'err')
    elif db.execute('SELECT 1 FROM usuarios WHERE usuario=?', (f['usuario'].strip(),)).fetchone(): flash('Ese usuario ya existe.', 'err')
    else:
        db.execute('INSERT INTO usuarios(usuario,nombre,clave) VALUES(?,?,?)', (f['usuario'].strip(), f.get('nombre', '').strip(), generate_password_hash(f['clave'])))
        audit('usuario', 0, 'crear', f['usuario']); db.commit(); flash('Usuario creado.', 'ok')
    return redirect(url_for('config'))

@app.route('/configuracion/respaldo', methods=['POST'])
def respaldo():
    tmp = tempfile.mktemp(suffix='.zip'); respaldar(tmp, True)
    audit('sistema', 0, 'respaldo', 'Descarga de respaldo completo'); get_db().commit()
    return send_file(tmp, as_attachment=True, download_name=f'respaldo_honorarios_{datetime.now():%Y%m%d_%H%M}.zip')

@app.route('/configuracion/restaurar', methods=['POST'])
def restaurar():
    fs = request.files.get('archivo')
    if not fs or not fs.filename.endswith('.zip') or request.form.get('confirmar') != 'RESTAURAR':
        flash('Seleccione el archivo .zip y escriba RESTAURAR para confirmar.', 'err'); return redirect(url_for('config'))
    tmp = tempfile.mktemp(suffix='.zip'); fs.save(tmp)
    try:
        with zipfile.ZipFile(tmp) as z:
            if 'app.db' not in z.namelist(): raise ValueError('El archivo no es un respaldo válido.')
            chk = tempfile.mktemp(suffix='.db')
            with open(chk, 'wb') as o: o.write(z.read('app.db'))
            t = sqlite3.connect(chk); t.execute('SELECT COUNT(*) FROM clientes').fetchone(); t.execute('SELECT COUNT(*) FROM pagos').fetchone(); t.close()
            respaldar(os.path.join(RESP, f'antes_de_restaurar_{datetime.now():%Y%m%d_%H%M%S}.zip'), True)
            get_db().close(); g.pop('db', None); shutil.copyfile(chk, DBF)
            for n in z.namelist():
                if n.startswith('comprobantes/') and not n.endswith('/'):
                    with open(os.path.join(COMP, os.path.basename(n)), 'wb') as o: o.write(z.read(n))
    except Exception as e:
        flash(f'No se pudo restaurar: {e}', 'err'); return redirect(url_for('config'))
    session.clear(); flash('Información restaurada. Vuelva a ingresar.', 'ok'); return redirect(url_for('login'))

@app.route('/configuracion/importar', methods=['POST'])
def importar():
    from importar import importar_excel, anio_de
    fl = [f for f in request.files.getlist('archivo') if f.filename]
    if not fl or any(not f.filename.lower().endswith('.xlsx') for f in fl): flash('Seleccione uno o más Excel (.xlsx).', 'err'); return redirect(url_for('config'))
    if any(anio_de(f.filename) is None for f in fl): flash('El nombre de cada archivo debe incluir el año (ej. CUENTAS CLIENTES 2025.xlsx).', 'err'); return redirect(url_for('config'))
    lista = []
    for f in fl:
        tmp = tempfile.mktemp(suffix='.xlsx'); f.save(tmp); lista.append((tmp, anio_de(f.filename)))
    try:
        r = importar_excel(lista, get_db(), usuario=session['user']); audit('sistema', 0, 'importar excel', r); get_db().commit()
        flash(f"Años {', '.join(map(str, r['anios']))}: {r['nuevos']} clientes nuevos, {r['actualizados']} actualizados, {r['pagos']} pagos mensuales y {r['dj']} Declaraciones Anuales "
              f"({r['con_fecha']} con fecha, {r['con_recibo']} con N° de recibo). Sin honorario definido: {r['sin_honorario']}. Control de cobranza desde {r['control_desde']}.", 'ok')
    except Exception as e: flash(f'No se pudo importar: {e}', 'err')
    return redirect(url_for('clientes'))

@app.route('/configuracion/modificaciones')
def auditoria():
    a = request.args.get('entidad', '')
    lst = get_db().execute('SELECT * FROM auditoria' + (' WHERE entidad=?' if a else '') + ' ORDER BY id DESC LIMIT 300', (a,) if a else ()).fetchall()
    return render_template('auditoria.html', lst=lst, a=a)

with app.app_context(): init_db()

if __name__ == '__main__':
    host = os.environ.get('DLS_HOST', '127.0.0.1'); port = int(os.environ.get('DLS_PORT', 5000))
    print(f'\n  Control de honorarios en  http://{"127.0.0.1" if host == "0.0.0.0" else host}:{port}\n  (cierre esta ventana para detener el programa)\n')
    from waitress import serve
    serve(app, host=host, port=port, threads=4)
