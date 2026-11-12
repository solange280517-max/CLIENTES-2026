CSS = """
:root{--nav:#1f2d3d;--nav2:#2b3d51;--ac:#2f6f8f;--bg:#f3f5f7;--tx:#1d2733;--mu:#6b7785;--bd:#dfe4ea;--ok:#1e7e4f;--pen:#8a6d1d;--par:#b25e09;--ven:#b3261e}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 "Segoe UI",system-ui,Arial,sans-serif;background:var(--bg);color:var(--tx)}
.app{display:flex;min-height:100vh}aside{width:230px;background:var(--nav);color:#cfd8e3;padding:18px 0;flex-shrink:0;position:sticky;top:0;height:100vh;display:flex;flex-direction:column}
aside h1{font-size:15px;color:#fff;margin:0 18px 2px}aside small{display:block;margin:0 18px 18px;color:#8fa3b8}
aside a{display:block;padding:10px 18px;color:#cfd8e3;text-decoration:none;border-left:3px solid transparent}aside a:hover{background:var(--nav2)}
aside a.on{background:var(--nav2);color:#fff;border-left-color:#6cc1e0}aside .u{margin-top:auto;padding:12px 18px;font-size:12px;color:#8fa3b8}
aside .u button{background:none;border:1px solid #4a5d72;color:#cfd8e3;padding:4px 10px;border-radius:5px;cursor:pointer;margin-top:6px}
main{flex:1;padding:24px 28px;min-width:0}h2{margin:0 0 16px;font-size:21px}h3{margin:0 0 10px;font-size:15px}
.card{background:#fff;border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:16px}
.grid{display:grid;gap:14px}.g4{grid-template-columns:repeat(4,1fr)}.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}
.kpi{background:#fff;border:1px solid var(--bd);border-radius:10px;padding:14px 16px}.kpi span{color:var(--mu);font-size:12px;text-transform:uppercase;letter-spacing:.4px}
.kpi b{display:block;font-size:24px;margin-top:4px}.kpi.ok b{color:var(--ok)}.kpi.ven b{color:var(--ven)}
table{width:100%;border-collapse:collapse}th{text-align:left;font-size:12px;color:var(--mu);text-transform:uppercase;padding:8px;border-bottom:2px solid var(--bd);white-space:nowrap}
td{padding:8px;border-bottom:1px solid var(--bd);vertical-align:middle}tr:hover td{background:#fafbfc}.r{text-align:right}.sc{overflow-x:auto}
.b{display:inline-block;padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap}
.b.ok{background:#e0f3e8;color:var(--ok)}.b.pen{background:#f6efd5;color:var(--pen)}.b.par{background:#fde8d0;color:var(--par)}.b.ven{background:#fbe0de;color:var(--ven)}.b.gr{background:#e8ecf0;color:#4a5866}
.btn{display:inline-block;background:var(--ac);color:#fff;border:0;padding:8px 14px;border-radius:7px;cursor:pointer;text-decoration:none;font-size:14px}
.btn.s{background:#fff;color:var(--ac);border:1px solid var(--ac)}.btn.d{background:var(--ven)}.btn.m{padding:3px 9px;font-size:12px}
label{display:block;font-size:12px;color:var(--mu);margin-bottom:3px}input,select,textarea{width:100%;padding:8px;border:1px solid #c6cdd6;border-radius:6px;font:inherit;background:#fff}
.f{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin-bottom:14px}.bar>div{min-width:120px}
.fl{padding:10px 14px;border-radius:8px;margin-bottom:12px}.fl.ok{background:#e0f3e8;color:#14532d}.fl.err{background:#fbe0de;color:#7f1d1d}.fl.warn{background:#f6efd5;color:#5c4a0c}
.mu{color:var(--mu)}.th{height:44px;width:44px;object-fit:cover;border-radius:6px;border:1px solid var(--bd);cursor:zoom-in}
.tr{display:flex;align-items:end;gap:8px;height:110px}.tr div{flex:1;text-align:center;font-size:11px;color:var(--mu)}.tr i{display:block;background:var(--ac);border-radius:4px 4px 0 0;margin-bottom:3px}
#zoom{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9;align-items:center;justify-content:center;flex-direction:column;gap:10px}
#zoom.on{display:flex}#zoom img{max-width:92vw;max-height:84vh;background:#fff}#zoom a{color:#fff}
details summary{cursor:pointer;font-weight:600}.auth{max-width:380px;margin:9vh auto;padding:0 16px}
@media(max-width:860px){.app{flex-direction:column}aside{width:100%;height:auto;position:static;flex-direction:row;flex-wrap:wrap;padding:8px}aside h1,aside small,aside .u{display:none}aside a{padding:8px 11px;border:0}
.g4,.g3,.g2{grid-template-columns:1fr 1fr}main{padding:14px}}@media(max-width:520px){.g4,.g3,.g2{grid-template-columns:1fr}}
"""

NAV = [('inicio', 'Inicio', ('inicio',)), ('clientes', 'Clientes', ('clientes', 'cliente_nuevo', 'cliente_editar', 'cliente_ver')),
       ('pago_nuevo', 'Registrar pago', ('pago_nuevo', 'pago_editar')), ('pagos', 'Historial de pagos', ('pagos',)),
       ('deudas_view', 'Clientes con deuda', ('deudas_view',)), ('reportes', 'Reportes', ('reportes',)),
       ('config', 'Configuración', ('config', 'auditoria'))]

PER = """{% macro per(name, val, auto=False) %}<select name="{{name}}" {% if auto %}onchange="this.form.submit()"{% endif %}>{% for p in periodos %}<option value="{{p}}" {{'selected' if p==val}}>{{p|mes_es}}</option>{% endfor %}</select>{% endmacro %}"""
FLASH = """{% for c,m in get_flashed_messages(with_categories=true) %}<div class="fl {{c}}">{{m}}</div>{% endfor %}"""
CSRF = """<input type="hidden" name="_csrf" value="{{ csrf_token() }}">"""

TEMPLATES = {
'base.html': """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'Inicio' }} · {{ estudio }}</title><style>""" + CSS + """</style></head><body><div class="app"><aside>{% if tiene_logo %}<img src="{{ url_for('logo') }}?v={{ logo_v }}" alt="Logo" style="display:block;max-width:170px;max-height:64px;margin:0 18px 10px;background:#fff;padding:5px;border-radius:6px">{% endif %}<h1>{{ estudio }}</h1><small>Control de honorarios</small>
""" + "".join(f"""<a href="{{{{ url_for('{ep}') }}}}" class="{{{{ 'on' if request.endpoint in {eps!r} }}}}">{lb}</a>""" for ep, lb, eps in NAV) + """
<div class="u">{{ session.nombre }}<form method="post" action="{{ url_for('salir') }}">""" + CSRF + """<button>Cerrar sesión</button></form></div></aside>
<main>""" + FLASH + """{% block c %}{% endblock %}</main></div>
<div id="zoom" data-close="1"><img alt="Comprobante"><a target="_blank" rel="noopener">Abrir en pestaña nueva ↗</a><a href="#" data-close="1">Cerrar ✕</a></div>
<script>document.addEventListener('click',function(e){var a=e.target.closest('[data-zoom]'),z=document.getElementById('zoom');
if(a){e.preventDefault();z.querySelector('img').src=a.dataset.zoom;z.querySelector('a').href=a.dataset.zoom;z.classList.add('on')}
else if(e.target.dataset.close){e.preventDefault();z.classList.remove('on')}});</script></body></html>""",

'auth.html': """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ estudio }}</title><style>""" + CSS + """</style></head>
<body><div class="auth"><div class="card">{% if tiene_logo %}<img src="{{ url_for('logo') }}?v={{ logo_v }}" alt="Logo" style="display:block;max-width:200px;max-height:80px;margin:0 0 10px">{% endif %}<h2>{{ estudio }}</h2><p class="mu">Control de honorarios</p>""" + FLASH + """{% block a %}{% endblock %}</div></div></body></html>""",

'login.html': """{% extends 'auth.html' %}{% block a %}<form method="post">""" + CSRF + """<label>Usuario</label><input name="usuario" autofocus required><br><br>
<label>Clave</label><input type="password" name="clave" required><br><br><button class="btn" style="width:100%">Ingresar</button></form>{% endblock %}""",

'setup.html': """{% extends 'auth.html' %}{% block a %}<p>Primer uso: cree el usuario administrador.</p><form method="post">""" + CSRF + """
<label>Nombre completo</label><input name="nombre"><br><br><label>Usuario</label><input name="usuario" required><br><br>
<label>Clave (mínimo 8 caracteres)</label><input type="password" name="clave" required><br><br><label>Repetir clave</label><input type="password" name="clave2" required><br><br>
<button class="btn" style="width:100%">Crear usuario</button></form>{% endblock %}""",

'inicio.html': """{% extends 'base.html' %}{% block c %}<h2>Inicio</h2>""" + PER + """
<form class="bar" method="get"><div><label>Periodo</label>{{ per('mes', mes, True) }}</div></form>
{% for t,m in alertas %}<div class="fl {{ 'err' if t=='err' else 'warn' }}">⚠ {{ m }}</div>{% endfor %}
<div class="grid g4"><div class="kpi"><span>Por cobrar en el mes</span><b>{{ k.por_cobrar|soles }}</b></div><div class="kpi ok"><span>Recaudado</span><b>{{ k.recaudado|soles }}</b></div>
<div class="kpi ven"><span>Pendiente de cobro</span><b>{{ k.pendiente|soles }}</b></div><div class="kpi"><span>Cobranza del mes</span><b>{{ k.pct }}%</b></div>
<div class="kpi"><span>Clientes que pagaron</span><b>{{ k.pagaron }}</b></div><div class="kpi"><span>Clientes con deuda (acumulada)</span><b>{{ k.con_deuda }}</b></div>
<div class="kpi"><span>Pagos pendientes de registrar</span><b>{{ k.sin_registrar }}</b></div><div class="kpi"><span>Pagos sin RH / recibo emitido</span><b>{{ k.sin_emitir }}</b></div></div><br>
<div class="grid g2"><div class="card"><h3>Cobranza últimos 6 meses</h3><div class="tr">{% for p,v in tendencia %}<div><i style="height:{{ v }}px"></i>{{ v }}%<br>{{ p[5:] }}/{{ p[2:4] }}</div>{% endfor %}</div></div>
<div class="card"><h3>Clientes con mayor deuda</h3><div class="sc"><table>{% for d in deudores %}<tr><td><a href="{{ url_for('cliente_ver', cid=d.cid) }}">{{ d.razon }}</a><br><span class="mu">{{ d['items']|length }} mes(es)</span></td><td class="r"><b>{{ d.total|soles }}</b></td></tr>
{% else %}<tr><td class="mu">Sin deudas 🎉</td></tr>{% endfor %}</table></div><p><a href="{{ url_for('deudas_view') }}">Ver todos →</a></p></div></div>
<div class="card"><h3>Pagos recientes</h3><div class="sc"><table><tr><th>Fecha</th><th>Cliente</th><th>Periodo</th><th class="r">Monto</th><th>Método</th></tr>
{% for p in recientes %}<tr><td>{{ p.fecha_pago|fecha }}</td><td>{{ p.razon }}</td><td>{{ p.periodo|mes_es }}</td><td class="r">{{ p.monto|soles }}</td><td>{{ p.metodo }}</td></tr>
{% else %}<tr><td colspan="5" class="mu">Aún no hay pagos registrados.</td></tr>{% endfor %}</table></div></div>{% endblock %}""",

'clientes.html': """{% extends 'base.html' %}{% block c %}<h2>Clientes <a class="btn" style="float:right" href="{{ url_for('cliente_nuevo') }}">+ Nuevo cliente</a></h2>
<form class="bar" method="get"><div style="flex:1"><label>Buscar por razón social o RUC</label><input name="q" value="{{ q }}"></div>
<div><label>Estado</label><select name="estado"><option value="">Todos</option><option value="activo" {{'selected' if est=='activo'}}>Activos</option><option value="inactivo" {{'selected' if est=='inactivo'}}>Inactivos</option></select></div><button class="btn">Filtrar</button></form>
<div class="card sc"><table><tr><th>RUC</th><th>Razón social</th><th>Representante</th><th>Celular</th><th class="r">Honorario</th><th>Inicio</th><th>Estado</th><th class="r">Deuda</th><th></th></tr>
{% for c in lista %}<tr><td>{{ c.ruc }}</td><td><a href="{{ url_for('cliente_ver', cid=c.id) }}">{{ c.razon }}</a></td><td>{{ c.representante or '' }}</td><td>{{ c.celular or '' }}</td>
<td class="r">{% if c.honorario %}{{ c.honorario|soles }}{% else %}<span class="b pen">Completar</span>{% endif %}</td><td>{{ c.fecha_inicio|fecha }}</td>
<td><span class="b {{ 'ok' if c.estado=='activo' else 'gr' }}">{{ c.estado|upper }}</span></td><td class="r">{{ deuda.get(c.id,0)|soles if deuda.get(c.id) else '—' }}</td>
<td><a class="btn s m" href="{{ url_for('cliente_editar', cid=c.id) }}">Editar</a></td></tr>
{% else %}<tr><td colspan="9" class="mu">No hay clientes. Use «Nuevo cliente» o importe su Excel en Configuración.</td></tr>{% endfor %}</table><p class="mu">{{ lista|length }} cliente(s)</p></div>{% endblock %}""",

'cliente_form.html': """{% extends 'base.html' %}{% block c %}<h2>{{ 'Nuevo cliente' if nuevo else 'Editar cliente' }}</h2><form method="post" class="card">""" + CSRF + """<div class="f">
<div><label>RUC *</label><input name="ruc" maxlength="11" inputmode="numeric" value="{{ c.ruc or '' }}" required></div>
<div style="grid-column:span 2"><label>Razón social o nombre *</label><input name="razon" value="{{ c.razon or '' }}" required></div>
<div><label>Representante (opcional)</label><input name="representante" value="{{ c.representante or '' }}"></div>
<div><label>Celular (opcional)</label><input name="celular" inputmode="tel" value="{{ c.celular or '' }}"></div>
<div><label>Honorario mensual (S/) *</label><input name="honorario" inputmode="decimal" value="{{ c.honorario if c.honorario != '' else '' }}" required></div>
<div><label>Fecha de inicio del servicio *</label><input type="date" name="fecha_inicio" value="{{ c.fecha_inicio }}" required></div>
<div><label>Estado</label><select name="estado"><option value="activo" {{'selected' if c.estado=='activo'}}>Activo</option><option value="inactivo" {{'selected' if c.estado=='inactivo'}}>Inactivo</option></select></div>
<div><label>Fecha de baja (si está inactivo)</label><input type="date" name="fecha_baja" value="{{ c.fecha_baja or '' }}"></div>
<div style="grid-column:1/-1"><label>Observaciones</label><textarea name="obs" rows="2">{{ c.obs or '' }}</textarea></div></div><br>
<button class="btn">Guardar</button> <a class="btn s" href="{{ url_for('clientes') }}">Cancelar</a>
<p class="mu">Al cambiar el honorario, los meses sin pago se calcularán con el nuevo monto; los meses ya pagados con otro monto se conservan.</p></form>{% endblock %}""",

'cliente_ver.html': """{% extends 'base.html' %}{% block c %}<h2>{{ c.razon }} <a class="btn s m" href="{{ url_for('cliente_editar', cid=c.id) }}">Editar</a>
<a class="btn m" href="{{ url_for('pago_nuevo', cliente=c.id) }}">+ Registrar pago</a></h2>
<p><a class="btn s m" href="{{ url_for('estado_cuenta', cid=c.id) }}">⬇ Estado de cuenta (solo deuda) PDF</a> <a class="btn s m" href="{{ url_for('estado_cuenta', cid=c.id, completo=1) }}">⬇ Historial completo PDF</a></p>
<form method="get" action="{{ url_for('estado_cuenta', cid=c.id) }}" class="bar"><input type="hidden" name="detalle" value="1"><div style="max-width:140px"><label>Año</label><select name="anio"><option value="">Todos</option>{% for y in anios %}<option>{{ y }}</option>{% endfor %}</select></div>
<button class="btn m">⬇ Estado de cuenta con recibos y comprobantes (PDF)</button></form>
<div class="grid g4"><div class="kpi"><span>RUC</span><b style="font-size:18px">{{ c.ruc }}</b></div><div class="kpi"><span>Honorario mensual</span><b>{{ c.honorario|soles }}</b></div>
<div class="kpi"><span>Inicio · Estado</span><b style="font-size:18px">{{ c.fecha_inicio|fecha }} · {{ c.estado|upper }}</b></div><div class="kpi ven"><span>Deuda total</span><b>{{ deuda|soles }}</b></div></div>
<p class="mu">{{ c.representante or '' }} {{ '· ' ~ c.celular if c.celular }} {{ '· ' ~ c.obs if c.obs }}</p>
<div class="card sc"><h3>Estado de cuenta por periodo</h3><table><tr><th>Periodo</th><th class="r">Acordado</th><th class="r">Pagado</th><th class="r">Saldo</th><th>Estado</th><th></th></tr>
{% for r in rows %}<tr><td>{{ r.periodo|mes_es }}</td><td class="r">{{ r.acordado|soles }}</td><td class="r">{{ r.pagado|soles }}</td><td class="r">{{ r.saldo|soles }}</td><td>{{ r.estado|badge }}</td>
<td>{% if r.saldo>0 %}<a class="btn s m" href="{{ url_for('pago_nuevo', cliente=c.id, periodo=r.periodo) }}">Pagar</a>{% endif %}</td></tr>{% endfor %}</table></div>
<div class="card sc"><h3>Historial completo de pagos</h3><table><tr><th>Fecha</th><th>Periodo</th><th class="r">Monto</th><th>Método</th><th>Recibo</th><th>RH</th><th>Comprobante</th><th></th></tr>
{% for p in pagos %}<tr><td>{{ p.fecha_pago|fecha }}</td><td>{{ p.periodo|mes_es }}</td><td class="r">{{ p.monto|soles }}</td><td>{{ p.metodo }}</td><td>{{ p.recibo_fisico or '—' }}</td><td>{{ p.rh or '—' }}</td>
<td>{% if p.comprobante %}<img class="th" src="{{ url_for('comprobante', pid=p.id) }}" data-zoom="{{ url_for('comprobante', pid=p.id) }}" alt="">{% else %}—{% endif %}</td>
<td><a class="btn s m" href="{{ url_for('pago_editar', pid=p.id) }}">Editar</a></td></tr>{% else %}<tr><td colspan="8" class="mu">Sin pagos registrados.</td></tr>{% endfor %}</table></div>{% endblock %}""",

'pago_form.html': """{% extends 'base.html' %}{% block c %}<h2>{{ 'Registrar pago' if nuevo else 'Editar pago' }}</h2>
<form method="post" enctype="multipart/form-data" class="card" id="fp">""" + CSRF + """<div class="f">
<div style="grid-column:span 2"><label>Cliente (escriba RUC o nombre) *</label><input name="cliente" list="cl" value="{{ p.cliente or '' }}" autocomplete="off" required>
<datalist id="cl">{% for c in clist %}<option value="{{ c.ruc }} — {{ c.razon }}">{% endfor %}</datalist></div>
<div><label>Periodo o concepto *</label><select name="periodo">{% for x in periodos_pago %}<option value="{{x}}" {{'selected' if x==p.periodo}}>{{ x|mes_es }}</option>{% endfor %}</select></div>
<div><label>Honorario acordado (S/) *</label><input name="acordado" inputmode="decimal" value="{{ p.acordado or '' }}" required></div>
<div><label>Monto pagado ahora (S/) *</label><input name="monto" inputmode="decimal" value="{{ p.monto or '' }}" required></div>
<div><label>Fecha de pago *</label><input type="date" name="fecha_pago" value="{{ p.fecha_pago or '' }}" required></div>
<div><label>Método de pago *</label><select name="metodo">{% for m in METODOS %}<option {{'selected' if m==p.metodo}}>{{ m }}</option>{% endfor %}</select></div></div>
<p id="info" class="mu"></p><hr style="border:0;border-top:1px solid var(--bd)"><h3>Comprobante emitido <span class="mu">(puede completarse después)</span></h3><div class="f">
<div><label>N° recibo físico</label><input name="recibo_fisico" value="{{ p.recibo_fisico or '' }}"></div><div><label>N° recibo por honorarios electrónico (RH)</label><input name="rh" value="{{ p.rh or '' }}"></div></div><br>
<h3>Foto o imagen del comprobante (Yape / transferencia)</h3>
{% if p.comprobante %}<p><img class="th" style="height:90px;width:auto" src="{{ url_for('comprobante', pid=p.id) }}" data-zoom="{{ url_for('comprobante', pid=p.id) }}" alt=""> <label style="display:inline"><input type="checkbox" name="quitar_comp" style="width:auto"> Quitar comprobante actual</label></p>{% endif %}
<input type="file" name="comprobante" accept="image/*,application/pdf" id="fc"><img id="pv" style="display:none;max-height:160px;margin-top:8px;border-radius:6px" alt="">
<br><br><label>Observaciones</label><textarea name="obs" rows="2">{{ p.obs or '' }}</textarea><br>
<button class="btn">Guardar pago</button> <a class="btn s" href="{{ url_for('pagos') }}">Cancelar</a>
{% if not nuevo %}<button class="btn d" style="float:right" formaction="{{ url_for('pago_eliminar', pid=p.id) }}" formnovalidate onclick="return confirm('¿Eliminar este pago? Quedará registrado en el historial de modificaciones.')">Eliminar</button>{% endif %}</form>
<script>var f=document.getElementById('fp'),first=true;function q(){var c=f.cliente.value,p=f.periodo.value;if(!/^\\d{11}/.test(c))return;
fetch('{{ url_for("api_cuenta") }}?cliente='+encodeURIComponent(c)+'&periodo='+p+'&excluir={{ p.id or 0 }}').then(r=>r.json()).then(d=>{if(!d.ok)return;
if(!{{ 'true' if nuevo else 'false' }}&&first){first=false}else{f.acordado.value=d.acordado;if(!f.monto.value||{{ 'true' if nuevo else 'false' }})f.monto.value=d.saldo||''}
document.getElementById('info').innerHTML='Honorario <b>S/ '+d.acordado.toFixed(2)+'</b> · ya pagado <b>S/ '+d.pagado.toFixed(2)+'</b> · saldo <b>S/ '+d.saldo.toFixed(2)+'</b>'+(d.saldo<=0?' — <span style="color:#b3261e">este periodo ya está pagado</span>':'')})}
f.cliente.addEventListener('change',q);f.periodo.addEventListener('change',q);q();
document.getElementById('fc').onchange=function(){var x=this.files[0],i=document.getElementById('pv');if(x&&x.type.indexOf('image')==0){i.src=URL.createObjectURL(x);i.style.display='block'}else i.style.display='none'}</script>{% endblock %}""",

'pagos.html': """{% extends 'base.html' %}{% block c %}<h2>Historial de pagos</h2><form class="bar" method="get">
<div style="flex:1"><label>Razón social o RUC</label><input name="q" value="{{ a.q or '' }}"></div>
<div><label>Mes</label><select name="mes"><option value="">Todos</option>{% for m in MESES %}<option value="{{ '%02d'|format(loop.index) }}" {{'selected' if a.mes=='%02d'|format(loop.index)}}>{{ m }}</option>{% endfor %}</select></div>
<div><label>Año</label><select name="anio"><option value="">Todos</option>{% for y in anios %}<option {{'selected' if a.anio==y|string}}>{{ y }}</option>{% endfor %}</select></div>
<div><label>Estado</label><select name="estado"><option value="">Todos</option>{% for e in ['PAGADO','PAGO PARCIAL','PENDIENTE','PAGO VENCIDO'] %}<option {{'selected' if a.estado==e}}>{{ e }}</option>{% endfor %}</select></div>
<div><label>Método</label><select name="metodo"><option value="">Todos</option>{% for m in METODOS %}<option {{'selected' if a.metodo==m}}>{{ m }}</option>{% endfor %}</select></div>
<div><label>N° recibo</label><input name="recibo" value="{{ a.recibo or '' }}"></div><div><label>N° RH</label><input name="rh" value="{{ a.rh or '' }}"></div>
<div><label>Comprobante</label><select name="emision"><option value="">Todos</option><option value="sin" {{'selected' if a.emision=='sin'}}>Por emitir</option><option value="con" {{'selected' if a.emision=='con'}}>Emitido</option></select></div>
<button class="btn">Buscar</button> <a class="btn s" href="{{ url_for('pagos') }}">Limpiar</a></form>
<div class="card sc"><table><tr><th>Fecha</th><th>Cliente</th><th>Periodo</th><th class="r">Monto</th><th>Método</th><th>Recibo</th><th>RH</th><th>Imagen</th><th>Estado del periodo</th><th></th></tr>
{% for p,e in items %}<tr><td>{{ p.fecha_pago|fecha }}</td><td><a href="{{ url_for('cliente_ver', cid=p.cliente_id) }}">{{ p.razon }}</a><br><span class="mu">{{ p.ruc }}</span></td><td>{{ p.periodo|mes_es }}</td><td class="r">{{ p.monto|soles }}</td><td>{{ p.metodo }}</td>
<td>{{ p.recibo_fisico or '' }}</td><td>{{ p.rh or '' }}{% if not p.importado and not p.rh and not p.recibo_fisico %}<span class="b pen">Por emitir</span>{% endif %}</td>
<td>{% if p.comprobante %}<img class="th" src="{{ url_for('comprobante', pid=p.id) }}" data-zoom="{{ url_for('comprobante', pid=p.id) }}" alt="">{% endif %}</td>
<td>{{ e.estado|badge if e }}</td><td><a class="btn s m" href="{{ url_for('pago_editar', pid=p.id) }}">Editar</a></td></tr>
{% else %}<tr><td colspan="10" class="mu">No se encontraron pagos.</td></tr>{% endfor %}</table>
<p class="mu">{{ total }} pago(s) · Total {{ suma|soles }} {% if pag>1 %}· <a href="?{{ qs }}&pag={{ pag-1 }}">← Anterior</a>{% endif %} {% if pag*n<total %}· <a href="?{{ qs }}&pag={{ pag+1 }}">Siguiente →</a>{% endif %}</p></div>{% endblock %}""",

'deudas.html': """{% extends 'base.html' %}{% block c %}<h2>Clientes con deuda</h2><form class="bar" method="get"><div style="flex:1"><label>Buscar</label><input name="q" value="{{ q }}"></div><button class="btn">Buscar</button></form>
<div class="kpi ven" style="margin-bottom:14px"><span>{{ dd|length }} cliente(s) · deuda total acumulada</span><b>{{ total|soles }}</b></div>
{% for d in dd %}<div class="card"><details {{ 'open' if d['items']|length>=am }}><summary>{{ d.razon }} <span class="mu">({{ d.ruc }})</span> — <span style="color:var(--ven)">{{ d.total|soles }}</span> · {{ d['items']|length }} mes(es)
{% if d['items']|length>=am %}<span class="b ven">Deuda acumulada</span>{% endif %}</summary><div class="sc"><table><tr><th>Periodo</th><th class="r">Acordado</th><th class="r">Pagado</th><th class="r">Saldo</th><th>Estado</th><th></th></tr>
{% for r in d['items'] %}<tr><td>{{ r.periodo|mes_es }}</td><td class="r">{{ r.acordado|soles }}</td><td class="r">{{ r.pagado|soles }}</td><td class="r">{{ r.saldo|soles }}</td><td>{{ r.estado|badge }}</td>
<td><a class="btn s m" href="{{ url_for('pago_nuevo', cliente=d.cid, periodo=r.periodo) }}">Registrar pago</a></td></tr>{% endfor %}</table></div>
<p><a class="btn s m" href="{{ url_for('estado_cuenta', cid=d.cid) }}">⬇ Estado de cuenta PDF</a></p>{% if d.celular %}<p><a class="btn s m" target="_blank" rel="noopener" href="https://wa.me/51{{ d.celular|replace(' ','')|replace('+51','') }}?text={{ ('Estimado cliente, le recordamos que mantiene un saldo pendiente de honorarios de ' ~ (d.total|soles) ~ '. Gracias.')|urlencode }}">Recordar por WhatsApp</a></p>{% endif %}</details></div>
{% else %}<div class="card mu">No hay clientes con deuda.</div>{% endfor %}{% endblock %}""",

'reportes.html': """{% extends 'base.html' %}{% block c %}<h2>Reportes</h2><form class="bar" method="get">
<div><label>Tipo</label><select name="tipo" onchange="this.form.submit()"><option value="mensual" {{'selected' if a.tipo!='anual'}}>Mensual</option><option value="anual" {{'selected' if a.tipo=='anual'}}>Anual</option></select></div>
{% if a.tipo=='anual' %}<div><label>Año</label><select name="anio">{% for y in anios %}<option {{'selected' if a.anio==y|string or (not a.anio and y==hoy[:4]|int)}}>{{ y }}</option>{% endfor %}</select></div>
{% else %}<div><label>Mes</label><select name="mes">{% for x in periodos %}<option value="{{x}}" {{'selected' if x==(a.mes or mes_actual)}}>{{ x|mes_es }}</option>{% endfor %}</select></div>{% endif %}
<div><label>Estado</label><select name="estado"><option value="">Todos</option>{% for e in ['PAGADO','PAGO PARCIAL','PENDIENTE','PAGO VENCIDO'] %}<option {{'selected' if a.estado==e}}>{{ e }}</option>{% endfor %}</select></div>
<div style="flex:1"><label>Cliente / RUC</label><input name="q" value="{{ a.q or '' }}"></div><button class="btn">Generar</button>
<a class="btn s" href="{{ url_for('exportar') }}?{{ qs }}&fmt=xlsx">⬇ Excel</a><a class="btn s" href="{{ url_for('exportar') }}?{{ qs }}&fmt=pdf">⬇ PDF</a></form>
<div class="card sc"><h3>{{ titulo }}</h3><table><tr><th>Cliente</th><th>Periodo</th><th class="r">Acordado</th><th class="r">Pagado</th><th class="r">Saldo</th><th>Fecha pago</th><th>Método</th><th>Recibo</th><th>RH</th><th>Compr.</th><th>Estado</th></tr>
{% for r in rows %}<tr><td><a href="{{ url_for('cliente_ver', cid=r.cid) }}">{{ r.razon }}</a></td><td>{{ r.periodo|mes_es }}</td><td class="r">{{ r.acordado|soles }}</td><td class="r">{{ r.pagado|soles }}</td><td class="r">{{ r.saldo|soles }}</td>
<td>{{ r.fecha|fecha }}</td><td>{{ r.metodos }}</td><td>{{ r.recibos }}</td><td>{{ r.rhs }}</td><td>{{ 'Sí' if r.adjuntos else 'No' }}</td><td>{{ r.estado|badge }}</td></tr>
{% else %}<tr><td colspan="11" class="mu">Sin datos para este filtro.</td></tr>{% endfor %}
<tr><td><b>TOTAL</b></td><td></td><td class="r"><b>{{ tot[0]|soles }}</b></td><td class="r"><b>{{ tot[1]|soles }}</b></td><td class="r"><b>{{ tot[2]|soles }}</b></td><td colspan="5"></td></tr></table></div>{% endblock %}""",

'config.html': """{% extends 'base.html' %}{% block c %}<h2>Configuración</h2><div class="grid g2"><div>
<form method="post" class="card">""" + CSRF + """<h3>General</h3><label>Nombre del estudio</label><input name="estudio" value="{{ c.estudio }}"><br><br>
<label>Día límite de pago de cada mes (1-28)</label><input type="number" name="dia_limite" min="1" max="28" value="{{ c.dia_limite }}"><br><br>
<label>Alertar deuda acumulada desde (meses)</label><input type="number" name="alerta_meses" min="1" value="{{ c.alerta_meses }}"><br><br>
<label>Controlar cobranza desde (AAAA-MM)</label><input name="control_desde" pattern="\\d{4}-\\d{2}" value="{{ c.control_desde }}"><br><br><button class="btn">Guardar</button></form>
<form method="post" action="{{ url_for('importar') }}" enctype="multipart/form-data" class="card">""" + CSRF + """<h3>Importar Excel anterior</h3><p class="mu">Seleccione de una vez los Excel de 2024, 2025 y 2026 (el nombre debe llevar el año). Lee monto, N° de recibo, fecha y método desde las notas de cada celda. Se puede repetir sin duplicar.</p>
<input type="file" name="archivo" accept=".xlsx" multiple required><br><br><button class="btn s">Importar</button></form>
<form method="post" action="{{ url_for('logo_subir') }}" enctype="multipart/form-data" class="card">""" + CSRF + """<h3>Logo del estudio</h3>
{% if tiene_logo %}<p><img src="{{ url_for('logo') }}?v={{ logo_v }}" alt="Logo" style="max-height:70px;border:1px solid var(--bd);padding:4px"></p>{% endif %}
<p class="mu">Aparece en el menú, la pantalla de ingreso, los PDF y los Excel. Use PNG o JPG (mejor si tiene fondo transparente).</p>
<input type="file" name="archivo" accept="image/png,image/jpeg"><br><br><button class="btn s">Guardar logo</button>
{% if tiene_logo %}<button class="btn d" name="quitar" value="1" formnovalidate>Quitar logo</button>{% endif %}</form>
<div class="card"><h3>Historial de modificaciones</h3><p><a href="{{ url_for('auditoria') }}">Ver quién cambió qué y cuándo →</a></p></div></div><div>
<div class="card"><h3>Respaldo y recuperación</h3><form method="post" action="{{ url_for('respaldo') }}">""" + CSRF + """<button class="btn">⬇ Descargar respaldo completo (datos + comprobantes)</button></form>
<p class="mu">Guarde el archivo en un USB o nube privada. Copias automáticas diarias de la base de datos en la carpeta «datos/respaldos»: {{ resp|join(', ') or 'aún ninguna' }}.</p><hr>
<form method="post" action="{{ url_for('restaurar') }}" enctype="multipart/form-data">""" + CSRF + """<label>Restaurar desde un respaldo (.zip)</label><input type="file" name="archivo" accept=".zip" required><br><br>
<label>Escriba RESTAURAR para confirmar (reemplaza los datos actuales)</label><input name="confirmar" autocomplete="off"><br><br><button class="btn d">Restaurar</button></form></div>
<form method="post" action="{{ url_for('cambiar_clave') }}" class="card">""" + CSRF + """<h3>Cambiar mi clave</h3><label>Clave actual</label><input type="password" name="actual" required><br><br>
<label>Nueva clave (8+ caracteres)</label><input type="password" name="nueva" required><br><br><label>Repetir nueva clave</label><input type="password" name="nueva2" required><br><br><button class="btn s">Cambiar</button></form>
<form method="post" action="{{ url_for('nuevo_usuario') }}" class="card">""" + CSRF + """<h3>Usuarios ({{ usuarios|map(attribute='usuario')|join(', ') }})</h3><div class="f"><div><label>Usuario</label><input name="usuario" required></div>
<div><label>Nombre</label><input name="nombre"></div><div><label>Clave (8+)</label><input type="password" name="clave" required></div></div><br><button class="btn s">Agregar usuario</button></form></div></div>{% endblock %}""",

'auditoria.html': """{% extends 'base.html' %}{% block c %}<h2>Historial de modificaciones</h2><form class="bar" method="get"><div><label>Tipo de registro</label><select name="entidad" onchange="this.form.submit()">
<option value="">Todos</option>{% for e in ['cliente','pago','config','usuario','sistema'] %}<option {{'selected' if a==e}}>{{ e }}</option>{% endfor %}</select></div></form>
<div class="card sc"><table><tr><th>Fecha y hora</th><th>Usuario</th><th>Registro</th><th>Acción</th><th>Detalle</th></tr>{% for l in lst %}<tr><td>{{ l.fecha }}</td><td>{{ l.usuario }}</td><td>{{ l.entidad }} #{{ l.registro }}</td><td>{{ l.accion }}</td>
<td style="font-size:12px;word-break:break-word">{{ l.detalle }}</td></tr>{% else %}<tr><td colspan="5" class="mu">Sin movimientos.</td></tr>{% endfor %}</table><p class="mu">Se muestran los últimos 300 movimientos.</p></div>{% endblock %}""",
}
