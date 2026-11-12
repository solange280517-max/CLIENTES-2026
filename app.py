"""De La Scala Consultores - Control de honorarios. Aplicativo web en la nube (Flask + Supabase PostgreSQL)."""
import os, io, re, json, uuid, secrets, zipfile, shutil, time, tempfile
from collections import defaultdict
from datetime import date, datetime
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import (Flask, g, request, session, redirect, url_for, render_template, flash,
                   send_file, abort, jsonify)
from jinja2 import DictLoader
from markupsafe import Markup, escape
from werkzeug.security import generate_password_hash, check_password_hash
from templates import TEMPLATES

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('DLS_DATA', os.path.join(BASE, 'datos'))
RESP = os.path.join(DATA, 'respaldos')
LOGO = os.path.join(DATA, 'logo.png')
for d in (DATA, RESP): os.makedirs(d, exist_ok=True)

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

# ---------------------------------------------------------------- base de datos (Supabase / PostgreSQL)
def get_db():
    if 'db' not in g:
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            u = urlparse(db_url)
            g.db = psycopg2.connect(
                database=u.path[1:],
                user=u.username,
                password=u.password,
                host=u.hostname,
                port=u.port,
                cursor_factory=RealDictCursor
            )
        else:
            raise RuntimeError("Falta configurar la variable de entorno DATABASE_URL")
    return g.db

@app.teardown_appcontext
def close_db(_):
    db = g.pop('db', None)
    if db: db.close()

def cfg(k, d=None):
    r = get_db().execute('SELECT valor FROM config WHERE clave=%s', (k,)).fetchone()
    return r['valor'] if r else d

def set_cfg(k, v):
    db = get_db()
    db.execute('INSERT INTO config(clave, valor) VALUES(%s, %s) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor', (k, str(v)))
    db.commit()

def audit(entidad, registro, accion, detalle):
    db = get_db()
    db.execute('INSERT INTO auditoria(fecha,usuario,entidad,registro,accion,detalle) VALUES(%s,%s,%s,%s,%s,%s)',
               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session.get('user', '-'), entidad, registro, accion,
                detalle if isinstance(detalle, str) else json.dumps(detalle, ensure_ascii=False)))
    db.commit()

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
    db = get_db(); cur = mes_actual(); desde = cfg('control_desde', '2026-01'); lim = int(cfg('dia_limite', 10))
    cl = db.execute('SELECT * FROM clientes' + (' WHERE id=%s' if cid else ''), (cid,) if cid else ()).fetchall()
    ov = {(r['cliente_id'], r['periodo']): r['monto'] for r in db.execute('SELECT * FROM periodos')}
    pg = defaultdict(list)
    for p in db.execute('SELECT * FROM pagos' + (' WHERE cliente_id=%s' if cid else ''), (cid,) if cid else ()):
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
                           adjuntos=sum(1 for p in ps if p['imagen_url'])))
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
    if get_db().execute('SELECT COUNT(*) FROM usuarios').fetchone()['count'] == 0: return redirect(url_for('setup'))
    if not session.get('uid'): return redirect(url_for('login'))

@app.after_request
def headers(r):
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['X-Frame-Options'] = 'DENY'
    r.headers['Cache-Control'] = 'no-store'
    r.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    return r

def sesion(u):
    session.clear(); session.permanent = True
    session.update(uid=u['id'], user=u['usuario'], nombre=u['nombre'] or u['usuario'])

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM usuarios').fetchone()['count']: return redirect(url_for('login'))
    if request.method == 'POST':
        us, nom, c1, c2 = (request.form.get(k, '').strip() for k in ('usuario', 'nombre', 'clave', 'clave2'))
        if not us or len(c1) < 8: flash('Usuario obligatorio y clave de al menos 8 caracteres.', 'err')
        elif c1 != c2: flash('Las claves no coinciden.', 'err')
        else:
            db.execute('INSERT INTO usuarios(usuario,nombre,clave) VALUES(%s,%s,%s)', (us, nom, generate_password_hash(c1)))
            db.commit()
            set_cfg('control_desde', '2026-01'); set_cfg('dia_limite', 10); set_cfg('alerta_meses', 2)
            flash('Usuario creado. Ya puede ingresar.', 'ok'); return redirect(url_for('login'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr; n, hasta = FALLOS.get(ip, (0, 0))
    if request.method == 'POST':
        if n >= 5 and time.time() < hasta:
            flash('Demasiados intentos. Espere 5 minutos.', 'err')
        else:
            u = get_db().execute('SELECT * FROM usuarios WHERE usuario=%s', (request.form.get('usuario', '').strip(),)).fetchone()
            if u and check_password_hash(u['clave'], request.form.get('clave', '')):
                FALLOS.pop(ip, None); sesion(u); return redirect(url_for('inicio'))
            FALLOS[ip] = (n + 1 if time.time() < hasta or n < 5 else 1, time.time() + 300)
            flash('Usuario o clave incorrectos.', 'err')
    return render_template('login.html')

@app.route('/salir', methods=['POST'])
def salir():
    session.clear(); return redirect(url_for('login'))

@app.route('/logo')
def logo():
    if not os.path.exists(LOGO): abort(404)
    r = send_file(LOGO, mimetype='image/png'); r.headers['Cache-Control'] = 'private, max-age=3600'; return r

@app.route('/configuracion/logo', methods=['POST'])
def logo_subir():
    if request.form.get('quitar'):
        if os.path.exists(LOGO): os.remove(LOGO)
        audit('config', 0, 'quitar logo', '-'); flash('Logo eliminado.', 'ok'); return redirect(url_for('config'))
    fs = request.files.get('archivo')
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(fs.read(8 * 1024 * 1024))); im = im.convert('RGBA'); im.thumbnail((700, 700))
        im.save(LOGO, 'PNG'); audit('config', 0, 'cambiar logo', '-'); flash('Logo guardado.', 'ok')
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
    k['sin_emitir'] = db.execute("SELECT COUNT(*) FROM pagos WHERE importado=0 AND COALESCE(rh,'')='' AND COALESCE(recibo_fisico,'')=''").fetchone()['count']
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
    if q: sql += ' AND (razon ILIKE %s OR ruc ILIKE %s)'; par += [f'%{q}%'] * 2
    if est: sql += ' AND estado=%s'; par.append(est)
    lista = get_db().execute(sql + ' ORDER BY razon', par).fetchall()
    deuda = {d['cid']: d['total'] for d in deudas(cuentas())}
    return render_template('clientes.html', lista=lista, deuda=deuda, q=q, est=est)

def form_cliente(cid=None):
    db = get_db(); f = request.form
    d = dict(ruc=re.sub(r'\D', '', f.get('ruc', '')), razon=f.get('razon', '').strip().upper(),
             representante=f.get('representante', '').strip(), celular=f.get('celular', '').strip(),
             honorario=num(f.get('honorario', '0')), fecha_inicio=pdate(f.get('fecha_inicio')),
             estado=f.get('estado', 'activo'), fecha_baja=pdate(f.get('fecha_baja')), obs=f.get('obs', '').strip())
    err = None
    if len(d['ruc']) != 11: err = 'El RUC debe tener 11 dígitos.'
    elif not d['razon']: err = 'Ingrese la razón social o nombre.'
    elif d['honorario'] is None or d['honorario'] < 0: err = 'Honorario mensual no válido.'
    elif not d['fecha_inicio']: err = 'Ingrese la fecha de inicio del servicio.'
    elif d['estado'] not in ('activo', 'inactivo'): err = 'Estado no válido.'
    elif db.execute('SELECT 1 FROM clientes WHERE ruc=%s AND id<>%s', (d['ruc'], cid or 0)).fetchone(): err = 'Ya existe un cliente con ese RUC.'
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
            db = get_db()
            cur = db.cursor()
            cur.execute('INSERT INTO clientes(ruc,razon,representante,celular,honorario,fecha_inicio,estado,fecha_baja,obs,creado) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
                (d['ruc'], d['razon'], d['representante'], d['celular'], d['honorario'], d['fecha_inicio'], d['estado'], d['fecha_baja'], d['obs'], hoy().isoformat()))
            new_id = cur.fetchone()['id']
            db.commit()
            audit('cliente', new_id, 'crear', d)
            flash('Cliente registrado.', 'ok')
            return redirect(url_for('cliente_ver', cid=new_id))
    return render_template('cliente_form.html', c=d, nuevo=True)

@app.route('/clientes/<int:cid>/editar', methods=['GET', 'POST'])
def cliente_editar(cid):
    db = get_db(); c = db.execute('SELECT * FROM clientes WHERE id=%s', (cid,)).fetchone() or abort(404)
    if request.method == 'POST':
        d, err = form_cliente(cid)
        if err: flash(err, 'err'); c = {**dict(c), **d}
        else:
            ch = diff(c, d, CAMPOS_CLI)
            db.execute('UPDATE clientes SET ruc=%s,razon=%s,representante=%s,celular=%s,honorario=%s,fecha_inicio=%s,estado=%s,fecha_baja=%s,obs=%s WHERE id=%s',
                       (*[d[k] for k in CAMPOS_CLI], cid))
            db.commit()
            if ch: audit('cliente', cid, 'editar', ch)
            flash('Datos actualizados.', 'ok'); return redirect(url_for('cliente_ver', cid=cid))
    return render_template('cliente_form.html', c=c, nuevo=False)

@app.route('/clientes/<int:cid>')
def cliente_ver(cid):
    db = get_db(); c = db.execute('SELECT * FROM clientes WHERE id=%s', (cid,)).fetchone() or abort(404)
    rows = cuentas(cid)
    pagos_ = db.execute('SELECT * FROM pagos WHERE cliente_id=%s ORDER BY periodo DESC, id DESC', (cid,)).fetchall()
    return render_template('cliente_ver.html', c=c, anios=sorted({r['periodo'][:4] for r in rows}, reverse=True), rows=rows[::-1], pagos=pagos_, deuda=sum(r['saldo'] for r in rows if es_deuda(r)))

# ---------------------------------------------------------------- pagos (con Supabase Storage para imágenes)
def subir_supabase_storage(fs):
    """Sube la imagen al bucket 'comprobantes' de Supabase y retorna la URL pública."""
    raw = fs.read()
    if len(raw) > 15 * 1024 * 1024: raise ValueError('El comprobante supera 15 MB.')
    
    if raw[:4] == b'%PDF': ext = 'pdf'; mime = 'application/pdf'
    elif raw[:3] == b'\xff\xd8\xff' or raw[:4] == b'\x89PNG' or (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP') or raw[:3] == b'GIF':
        try:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))); im.thumbnail((2000, 2000))
            buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=85); raw = buf.getvalue()
        except Exception: raise ValueError('La imagen no se pudo leer.')
        ext = 'jpg'; mime = 'image/jpeg'
    else: raise ValueError('Formato no permitido. Use JPG, PNG, WEBP o PDF.')

    nombre = uuid.uuid4().hex + '.' + ext
    
    # Subir usando la API REST de Supabase Storage integrada en las variables de entorno si están disponibles, 
    # o simulando el almacenamiento mediante un cliente de supabase si se prefiere. 
    # Nota: Asegúrate de tener SUPABASE_URL y SUPABASE_KEY en tus variables de entorno de Render, o usamos la subida por url.
    sup_url = os.environ.get('SUPABASE_URL')
    sup_key = os.environ.get('SUPABASE_KEY')
    
    if sup_url and sup_key:
        import urllib.request
        upload_url = f"{sup_url}/storage/v1/object/comprobantes/{nombre}"
        req = urllib.request.Request(upload_url, data=raw, method='POST')
        req.add_header('Authorization', f'Bearer {sup_key}')
        req.add_header('Content-Type', mime)
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return f"{sup_url}/storage/v1/object/public/comprobantes/{nombre}"
        except Exception:
            pass
            
    # Respaldo local temporal si no está configurada la llave de Supabase Storage en el entorno
    local_path = os.path.join(DATA, nombre)
    with open(local_path, 'wb') as f: f.write(raw)
    return url_for('comprobante_local', filename=nombre, _external=True)

@app.route('/comprobantes-locales/<filename>')
def comprobante_local(filename):
    return send_file(os.path.join(DATA, filename))

def resolver_cliente(txt):
    m = re.match(r'\s*(\d{11})', txt or '')
    return get_db().execute('SELECT * FROM clientes WHERE ruc=%s', (m.group(1),)).fetchone() if m else None

def procesar_pago(pid=None):
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
    
    prev = db.execute('SELECT COALESCE(SUM(monto),0) AS total FROM pagos WHERE cliente_id=%s AND periodo=%s AND id<>%s', (c['id'], per, pid or 0)).fetchone()['total']
    saldo = round(acord - prev, 2)
    if saldo <= EPS: return None, f'{f_mes(per)} de este cliente ya está pagado por completo. No se puede duplicar el pago.'
    if monto > saldo + EPS: return None, f'El monto ({f_soles(monto)}) supera el saldo pendiente de {f_soles(saldo)}.'
    
    rf, rh = f.get('recibo_fisico', '').strip(), f.get('rh', '').strip()
    for col, val, nom in (('recibo_fisico', rf, 'recibo físico'), ('rh', rh, 'RH')):
        if val and db.execute(f'SELECT 1 FROM pagos WHERE {col}=%s AND cliente_id<>%s AND id<>%s', (val, c['id'], pid or 0)).fetchone():
            return None, f'El {nom} {val} ya está registrado en otro cliente.'
            
    old = db.execute('SELECT * FROM pagos WHERE id=%s', (pid,)).fetchone() if pid else None
    img_url = old['imagen_url'] if old else None
    try:
        fs = request.files.get('comprobante')
        if fs and fs.filename: img_url = subir_supabase_storage(fs)
        elif f.get('quitar_comp'): img_url = None
    except ValueError as e: return None, str(e)
    
    if per.endswith('-00') or abs(acord - c['honorario']) > EPS: 
        db.execute('INSERT INTO periodos (cliente_id, periodo, monto) VALUES (%s, %s, %s) ON CONFLICT (cliente_id, periodo) DO UPDATE SET monto = EXCLUDED.monto', (c['id'], per, acord))
    else: 
        db.execute('DELETE FROM periodos WHERE cliente_id=%s AND periodo=%s', (c['id'], per))
        
    d = dict(cliente_id=c['id'], periodo=per, monto=monto, fecha_pago=fecha, metodo=metodo, recibo_fisico=rf, rh=rh,
             imagen_url=img_url, obs=f.get('obs', '').strip())
    
    if pid:
        db.execute('UPDATE pagos SET cliente_id=%s,periodo=%s,monto=%s,fecha_pago=%s,metodo=%s,recibo_fisico=%s,rh=%s,imagen_url=%s,obs=%s,importado=0 WHERE id=%s', 
                   (d['cliente_id'], d['periodo'], d['monto'], d['fecha_pago'], d['metodo'], d['recibo_fisico'], d['rh'], d['imagen_url'], d['obs'], pid))
        db.commit()
        audit('pago', pid, 'editar', diff(old, d, list(d)))
    else:
        cur = db.cursor()
        cur.execute('INSERT INTO pagos(cliente_id,periodo,monto,fecha_pago,metodo,recibo_fisico,rh,imagen_url,obs,creado,usuario) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
                    (d['cliente_id'], d['periodo'], d['monto'], d['fecha_pago'], d['metodo'], d['recibo_fisico'], d['rh'], d['imagen_url'], d['obs'], hoy().isoformat(), session.get('user')))
        pid = cur.fetchone()['id']
        db.commit()
        audit('pago', pid, 'crear', {**d, 'cliente': c['razon']})
    return pid, None

@app.route('/pagos/nuevo', methods=['GET', 'POST'])
def pago_nuevo():
    p = dict(periodo=request.args.get('periodo', mes_actual()), fecha_pago=hoy().isoformat(), metodo='Yape')
    cl = request.args.get('cliente')
    if cl and cl.isdigit():
        c = get_db().execute('SELECT ruc, razon FROM clientes WHERE id=%s', (cl,)).fetchone()
        if c: p['cliente'] = f"{c['ruc']} — {c['razon']}"
    if request.method == 'POST':
        pid, err = procesar_pago()
        if not err: flash('Pago registrado correctamente.', 'ok'); return redirect(url_for('pagos'))
        flash(err, 'err'); p = request.form.to_dict()
    clist = get_db().execute("SELECT ruc, razon FROM clientes WHERE estado='activo' ORDER BY razon").fetchall()
    return render_template('pago_form.html', p=p, clist=clist, nuevo=True)

@app.route('/pagos/<int:pid>/editar', methods=['GET', 'POST'])
def pago_editar(pid):
    db = get_db(); r = db.execute('SELECT p.*, c.ruc, c.razon, c.honorario FROM pagos p JOIN clientes c ON c.id=p.cliente_id WHERE p.id=%s', (pid,)).fetchone() or abort(404)
    if request.method == 'POST':
        _, err = procesar_pago(pid)
        if not err: flash('Pago actualizado.', 'ok'); return redirect(url_for('pagos'))
        flash(err, 'err'); p = {**request.form.to_dict(), 'id': pid, 'imagen_url': r['imagen_url']}
    else:
        ov = db.execute('SELECT monto FROM periodos WHERE cliente_id=%s AND periodo=%s', (r['cliente_id'], r['periodo'])).fetchone()
        p = {**dict(r), 'cliente': f"{r['ruc']} — {r['razon']}", 'acordado': ov['monto'] if ov else r['honorario']}
    clist = db.execute('SELECT ruc, razon FROM clientes ORDER BY razon').fetchall()
    return render_template('pago_form.html', p=p, clist=clist, nuevo=False)

@app.route('/pagos/<int:pid>/eliminar', methods=['POST'])
def pago_eliminar(pid):
    db = get_db(); r = db.execute('SELECT * FROM pagos WHERE id=%s', (pid,)).fetchone() or abort(404)
    audit('pago', pid, 'eliminar', dict(r))
    db.execute('DELETE FROM pagos WHERE id=%s', (pid,)); db.commit()
    flash('Pago eliminado.', 'ok'); return redirect(url_for('pagos'))

@app.route('/api/cuenta')
def api_cuenta():
    c = resolver_cliente(request.args.get('cliente')); per = request.args.get('periodo', '')
    if not c: return jsonify(ok=False)
    ov = get_db().execute('SELECT monto FROM periodos WHERE cliente_id=%s AND periodo=%s', (c['id'], per)).fetchone()
    acord = ov['monto'] if ov else (0 if per.endswith('-00') else c['honorario'])
    prev = get_db().execute('SELECT COALESCE(SUM(monto),0) AS total FROM pagos WHERE cliente_id=%s AND periodo=%s AND id<>%s',
                            (c['id'], per, request.args.get('excluir', 0))).fetchone()['total']
    return jsonify(ok=True, acordado=acord, pagado=round(prev, 2), saldo=round(max(acord - prev, 0), 2))
