"""Importa clientes y pagos desde los Excel anuales (hojas 'CLAVE 0'..'CLAVE 9').
Lee de cada celda de mes: el monto, y de la NOTA de la celda: N° de recibo (R.I.), fecha y método de pago."""
import re, os, collections
from datetime import date, datetime
from openpyxl import load_workbook

MES = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SETIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']

def anio_de(nombre):
    m = re.search(r'(?<!\d)(20\d\d)(?!\d)', os.path.basename(nombre))
    return int(m.group(1)) if m else None

def _nota(c):
    if not c.comment: return ''
    t = c.comment.text or ''
    if 'Comentario:' in t: t = t.split('Comentario:')[-1]
    t = t.replace('\r', '')
    lineas = [l.strip() for l in t.split('\n') if l.strip()]
    if lineas and lineas[0].endswith(':') and len(lineas[0]) < 28: lineas = lineas[1:]   # quita "USER:", "Ger:"...
    return ' | '.join(lineas)

def _datos_nota(nota, anio):
    ri = re.search(r'(?:\bR\s*\.?\s*I\b\.?|\bI\s*\.)\s*:?\s*0*(\d{3,7})', nota)
    fe = None
    for d, m, y in re.findall(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', nota):
        y = int(y) if len(y) == 4 else (2000 + int(y) if len(y) == 2 else anio)
        try: fe = date(y, int(m), int(d)).isoformat(); break
        except ValueError: continue
    u = nota.upper()
    if 'YAPE' in u: met = 'Yape'
    elif re.search(r'INTERBANK|BCP|BBVA|SCOTIA|TRANSFER|DEPOS|CCI|BANCO|IBK', u): met = 'Transferencia bancaria'
    elif 'EFECTIVO' in u: met = 'Efectivo'
    else: met = 'Otro'
    return (f'{int(ri.group(1)):06d}' if ri else ''), fe, met

def _inicio(obs, primer):
    m = re.search(r'INGRESO\s+(\d{1,2})[-/](\d{1,2})?[-/]?(\d{2,4})', obs or '')
    if m:
        g = [x for x in m.groups() if x]; mes = int(g[0]) if len(g) == 2 else int(g[1]); yy = int(g[-1]); yy += 2000 if yy < 100 else 0
        if 1 <= mes <= 12: return f'{yy}-{mes:02d}'
    return primer

def _mes_prev(p, n=1):
    y, m = int(p[:4]), int(p[5:7]) - 1 + n
    return f'{y + m // 12}-{m % 12 + 1:02d}'

def leer(path, anio):
    """Devuelve {ruc: registro} de un Excel anual."""
    wb = load_workbook(path, data_only=True); out = {}; res = dict(anuales=0, textos=0)
    for ws in wb:
        if not ws.title.startswith('CLAVE'): continue
        rows = list(ws.iter_rows(min_row=1, max_row=150))
        hi = next((i for i, r in enumerate(rows) if any(str(c.value).strip() == 'NOMBRE' for c in r if c.value)), None)
        if hi is None: continue
        h = {str(c.value).strip(): c.column - 1 for c in rows[hi] if c.value}
        if 'RUC' not in h or any(m not in h for m in MES): continue
        for r in rows[hi + 1:]:
            ruc = re.sub(r'\D', '', str(r[h['RUC']].value or ''))
            nom = r[h['NOMBRE']].value
            if not nom or len(ruc) != 11: continue
            obs = str(r[h['OBS']].value).strip() if 'OBS' in h and r[h['OBS']].value else ''
            nnom = _nota(r[h['NOMBRE']])
            pagos = {}
            for k, m in enumerate(MES):
                c = r[h[m]]
                if isinstance(c.value, (int, float)) and c.value > 0:
                    nota = _nota(c); ri, fe, met = _datos_nota(nota, anio)
                    pagos[k + 1] = dict(monto=float(c.value), ri=ri, fecha=fe, metodo=met, nota=nota)
                elif isinstance(c.value, str) and re.search(r'\d', c.value) and not re.search(r'NO CANCELA|- - -', c.value): res['textos'] += 1
            ca = h.get('ANUAL ' + str(anio)) or next((v for k, v in h.items() if k.startswith('ANUAL')), None)
            anual = None   # columna ANUAL = Declaración Jurada Anual del año de la hoja
            if ca is not None and isinstance(r[ca].value, (int, float)) and r[ca].value > 0:
                nota = _nota(r[ca]); ri, fe, met = _datos_nota(nota, anio + 1); res['anuales'] += 1
                anual = dict(monto=float(r[ca].value), ri=ri, fecha=fe, metodo=met, nota=nota)
            texto = ' '.join(str(r[h[m]].value) for m in MES if isinstance(r[h[m]].value, str)) + ' ' + obs + ' ' + nnom
            out[ruc] = dict(ruc=ruc, nombre=str(nom).strip(), obs=obs, nota_nombre=nnom, pagos=pagos, anual=anual, hoja=ws.title, texto=texto, anio=anio)
    return out, res

def importar_excel(archivos, db, usuario='importación'):
    """archivos: lista de (ruta, año). Se procesan de menor a mayor año."""
    archivos = sorted(archivos, key=lambda x: x[1])
    hoy = date.today().isoformat(); cli = {}; res = dict(clientes=0, nuevos=0, actualizados=0, pagos=0, con_recibo=0, con_fecha=0,
                                                         duplicados=[], sin_honorario=0, inactivos=0, anuales=0, dj=0, textos=0, anios=[a for _, a in archivos])
    for path, anio in archivos:
        datos, r = leer(path, anio); res['anuales'] += r['anuales']; res['textos'] += r['textos']
        for ruc, d in datos.items():
            c = cli.setdefault(ruc, dict(ruc=ruc, años={}, anual={}, obs=[], nota=[], textos=[]))
            if anio in c['años']: res['duplicados'].append(f'{ruc} {d["nombre"]} ({anio})'); continue
            c['años'][anio] = d['pagos']
            if d['anual']: c['anual'][anio] = d['anual']
            c['nombre'] = d['nombre']; c['textos'].append(d['texto'])
            if d['obs']: c['obs'].append(d['obs'])
            if d['nota_nombre']: c['nota'].append(d['nota_nombre'])
            c['ultimo_anio_archivo'] = anio; c['hoja'] = d['hoja']
    ult = max(a for _, a in archivos)
    for ruc, c in cli.items():
        pers = sorted(f'{a}-{m:02d}' for a, pg in c['años'].items() for m in pg)
        modo = {}
        for a, pg in c['años'].items():
            if pg:
                cnt = collections.Counter(v['monto'] for v in pg.values()); top = max(cnt.values())
                modo[a] = [v for _, v in sorted(((m, x['monto']) for m, x in pg.items()), reverse=True) if cnt[v] == top][0]
        honor = modo[max(modo)] if modo else 0.0
        if 'NO COBRAR' in ' '.join(c['nota']).upper(): honor = 0.0
        txt = ' '.join(c['textos']).upper()
        inactivo = bool(re.search(r'RETIRADO|DIO DE BAJA', txt)); baja = None
        if c['ultimo_anio_archivo'] < ult and pers: inactivo = True; baja = _mes_prev(pers[-1], 1) + '-01'
        elif c['ultimo_anio_archivo'] < ult: inactivo = True; baja = f"{c['ultimo_anio_archivo'] + 1}-01-01"
        elif inactivo:
            mm = next((k + 1 for k, m in enumerate(MES) if any(m in o.upper() for o in c['obs'])), 1)
            baja = f"{ult}-{mm:02d}-01"
        inicio = min([_inicio(o, None) for o in c['obs'] if _inicio(o, None)] + pers[:1] or [f'{min(c["años"])}-01'])
        nota = ' | '.join(dict.fromkeys(c['obs'] + c['nota'])) or ''
        row = db.execute('SELECT * FROM clientes WHERE ruc=?', (ruc,)).fetchone()
        if row:
            cid = row['id']; res['actualizados'] += 1
            db.execute('UPDATE clientes SET fecha_inicio=?, honorario=CASE WHEN honorario=0 THEN ? ELSE honorario END WHERE id=?', (min(row['fecha_inicio'][:7], inicio) + '-01', honor, cid))
            db.execute('DELETE FROM pagos WHERE cliente_id=? AND importado=1', (cid,)); honor_cli = row['honorario'] or honor
        else:
            cid = db.execute('INSERT INTO clientes(ruc,razon,honorario,fecha_inicio,estado,fecha_baja,obs,creado) VALUES(?,?,?,?,?,?,?,?)',
                (ruc, c['nombre'], honor, inicio + '-01', 'inactivo' if inactivo else 'activo', baja, nota, hoy)).lastrowid
            res['nuevos'] += 1; honor_cli = honor
            if inactivo: res['inactivos'] += 1
        res['clientes'] += 1
        if not honor_cli: res['sin_honorario'] += 1
        manuales = {r_[0] for r_ in db.execute('SELECT periodo FROM pagos WHERE cliente_id=? AND importado=0', (cid,))}
        fin = ((baja or '')[:7] and _mes_prev(baja[:7], -1)) or f'{ult}-12'
        for a, pg in sorted(c['años'].items()):
            for m in range(1, 13):
                per = f'{a}-{m:02d}'
                if per in manuales: continue
                p = pg.get(m)
                esperado = modo.get(a, honor_cli)
                if p:
                    if abs(p['monto'] - honor_cli) > 0.005: db.execute('INSERT OR REPLACE INTO periodos VALUES(?,?,?)', (cid, per, p['monto']))
                    else: db.execute('DELETE FROM periodos WHERE cliente_id=? AND periodo=?', (cid, per))
                    nota_p = f"Excel {a}: {p['nota']}" if p['nota'] else f'Importado del Excel {a}'
                    db.execute('INSERT INTO pagos(cliente_id,periodo,monto,fecha_pago,metodo,recibo_fisico,obs,importado,creado,usuario) VALUES(?,?,?,?,?,?,?,1,?,?)',
                               (cid, per, p['monto'], p['fecha'], p['metodo'], p['ri'], nota_p, hoy, usuario))
                    res['pagos'] += 1; res['con_recibo'] += bool(p['ri']); res['con_fecha'] += bool(p['fecha'])
                elif honor_cli and abs(esperado - honor_cli) > 0.005 and inicio <= per <= fin:
                    db.execute('INSERT OR REPLACE INTO periodos VALUES(?,?,?)', (cid, per, esperado))
        for a, p in c['anual'].items():
            per = f'{a}-00'
            if per in manuales: continue
            db.execute('INSERT OR REPLACE INTO periodos VALUES(?,?,?)', (cid, per, p['monto']))
            db.execute('INSERT INTO pagos(cliente_id,periodo,monto,fecha_pago,metodo,recibo_fisico,obs,importado,creado,usuario) VALUES(?,?,?,?,?,?,?,1,?,?)',
                       (cid, per, p['monto'], p['fecha'], p['metodo'], p['ri'], f"Declaración Jurada Anual {a}. " + (f"Excel: {p['nota']}" if p['nota'] else ''), hoy, usuario))
            res['dj'] += 1; res['con_recibo'] += bool(p['ri']); res['con_fecha'] += bool(p['fecha'])
    ini = f'{min(a for _, a in archivos)}-01'
    db.execute("INSERT OR REPLACE INTO config VALUES('control_desde',?)", (ini,))
    db.commit(); res['control_desde'] = ini
    return res

if __name__ == '__main__':
    import sys, app
    with app.app.app_context():
        app.init_db()
        print(importar_excel([(p, anio_de(p)) for p in sys.argv[1:]], app.get_db()))
