# Control de honorarios — De La Scala Consultores

## 1. Instalación (una sola vez)
1. Instale **Python 3.10 o superior** desde python.org (marque *Add Python to PATH*).
2. Descomprima esta carpeta en la PC del estudio (ej. `C:\HonorariosDLS`).
3. Haga doble clic en **iniciar.bat**. La primera vez descarga lo necesario (requiere internet) y abre el navegador en `http://127.0.0.1:5000`.
4. Cree su usuario y clave (mínimo 8 caracteres). Para los siguientes usos basta con doble clic en `iniciar.bat`; no cierre la ventana negra mientras trabaja.

**Uso desde el celular u otra PC del estudio:** abra `iniciar_en_red_local.bat`, averigüe la IP de la PC (`ipconfig`, ej. 192.168.1.20) y entre desde el celular (mismo WiFi) a `http://192.168.1.20:5000`. Úselo solo en una red privada de confianza.

## 2. Migrar sus Excel (2024, 2025 y 2026)
*Configuración → Importar Excel anterior* → seleccione **a la vez** los tres archivos (el nombre de cada uno debe llevar el año, ej. `CUENTAS CLIENTES 2025.xlsx`; con Ctrl+clic se eligen varios).
Se cargan los clientes de las hojas CLAVE 0 a 9 y, de cada celda de mes, el **monto** y, leyendo la **nota** de la celda, el **N° de recibo (R.I.)**, la **fecha de pago** y el **método** (Yape, banco, efectivo) cuando figura. La nota completa queda en Observaciones del pago.
La columna **ANUAL** de cada Excel se carga como la **Declaración Jurada Anual** de ese año (aparece como «DJ Anual 2024», «DJ Anual 2025»…).
Se puede repetir la importación sin duplicar: reemplaza solo lo importado y respeta lo que usted registre a mano.
Después revise: clientes con «Completar» (sin honorario), clientes marcados inactivos (los que ya no aparecen en el Excel más reciente) y las deudas de 2024-2025. Si prefiere que las deudas cuenten solo desde 2026, cambie «Controlar cobranza desde» en Configuración a `2026-01`.

## 3. Registrar un cliente
*Clientes → + Nuevo cliente*: RUC (11 dígitos), razón social, honorario mensual, fecha de inicio y estado. Representante y celular son opcionales. Use *Editar* para corregir; para retirar a un cliente cámbielo a **Inactivo** (deja de generar cobros desde la fecha de baja y conserva su historial).

## 4. Registrar un pago
*Registrar pago*: escriba el RUC o nombre y elíjalo de la lista → periodo → monto pagado, fecha y método. El sistema muestra honorario, lo ya pagado y el saldo.
- **Declaración Jurada Anual:** en *Periodo o concepto* elija «DJ Anual 2026» (o el año que corresponda) y escriba el honorario acordado de esa declaración, que varía por año. Si queda saldo, aparece como deuda desde que termina ese año (fecha límite: 30 de abril del año siguiente).
- **Abono parcial:** ingrese menos del saldo; luego registre otro pago del mismo mes. No permite pagar de más ni duplicar un mes ya cancelado.
- **Si el honorario de ese mes fue distinto**, cambie el campo *Honorario del periodo*.
- **RH y recibo físico son opcionales:** si aún no los emite, deje vacío; el pago queda con la etiqueta **Por emitir** y aparece en el Inicio. Luego entre a *Historial de pagos → Editar* y complete el número.
- **Comprobante (foto):** botón *Seleccionar archivo*; desde el celular puede tomar la foto directamente. Se guarda vinculada al pago. Haga clic en la miniatura para verla ampliada.

## 5. Consultar, deudas y reportes
- **Historial de pagos:** filtros por razón social, RUC, mes, año, estado, método, N° de recibo, N° de RH y si el comprobante está emitido.
- **Clientes con deuda:** detalle por mes y total acumulado; botón para registrar el pago o recordar por WhatsApp.
- **Reportes:** mensual o anual → *Generar* → **⬇ Excel** o **⬇ PDF**.
- **Estados:** PAGADO · PENDIENTE (aún dentro del plazo) · PAGO PARCIAL · PAGO VENCIDO (pasó el día límite sin pago; se configura en *Configuración*, por defecto día 10).

## 6. Logo y estado de cuenta
- *Configuración → Logo del estudio*: suba su logo (PNG o JPG). Aparece en el menú, el ingreso, los PDF y los Excel.
- En *Clientes con deuda* o en la ficha de cada cliente: botón **Estado de cuenta PDF** (solo deuda o historial completo) para enviarle. En la ficha del cliente también está **Estado de cuenta con recibos y comprobantes** (elija el año): lista cada pago con fecha, método, N° de recibo, RH y la imagen del comprobante.

## 7. Seguridad y respaldos
- Acceso con usuario y clave, bloqueo tras 5 intentos fallidos y cierre de sesión a las 8 horas. Los comprobantes solo se ven con sesión iniciada.
- Todos los datos están en la carpeta `datos` (base de datos + imágenes). **Copie esa carpeta** a un USB o nube privada con regularidad; o use *Configuración → Descargar respaldo completo*.
- Se hace una copia automática diaria de la base de datos en `datos/respaldos`.
- *Restaurar* reemplaza los datos actuales por los del respaldo (antes guarda una copia de lo existente).
- Recomendado: activar **BitLocker** (cifrado del disco) en la PC y usar una clave larga.
- *Configuración → Historial de modificaciones* muestra quién cambió o eliminó cada cliente o pago.
