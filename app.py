"""De La Scala Consultores - Control de honorarios. Aplicativo web en la nube (Flask + Supabase PostgreSQL)."""
import os, io, re, json, uuid, secrets, zipfile, shutil, time, tempfile
from collections import defaultdict
from datetime import date, datetime
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
            g.db = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
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
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('_csrf', ''), session.get('csrf',
