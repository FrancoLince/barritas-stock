from datetime import datetime, timedelta, timezone
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import db, init_db
from models import TipoCliente, Producto, PrecioProducto, Compra, Cliente, Venta, DetalleVenta, User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_key_super_secreta")

# Configuración de duración de sesión
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Por favor, inicia sesión para acceder."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- INICIALIZACIÓN DE DATOS (SEED) ---
with app.app_context():
    tipos_defecto = ['Mayorista', 'Revendedor', 'Minorista', 'Distribuidoras grandes']
    for nombre in tipos_defecto:
        if not TipoCliente.query.filter_by(nombre=nombre).first():
            db.session.add(TipoCliente(nombre=nombre))
    
    usuarios_iniciales = [
        ("admin", "admin"),
        ("Emilia", "Barritas123"),
        ("Analia", "Barritas123"),
        ("Cati", "Barritas123")
    ]

    for username, password in usuarios_iniciales:
        usuario = User.query.filter_by(username=username).first()
        if not usuario:
            nuevo_usuario = User(username=username)
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
        else:
            usuario.set_password(password)
        
    db.session.commit()


# ---------------------------------------------------------
# RUTAS DE AUTENTICACIÓN
# ---------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=False) 
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")
            
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------

@app.route('/')
@login_required
def index():
    productos = Producto.query.all()
    clientes_list = Cliente.query.all()
    ventas_list = Venta.query.all()

    ventas_cobradas = [
        v for v in ventas_list 
        if v.observaciones and ('Efectivo' in v.observaciones or 'Transferencia' in v.observaciones)
    ]

    total_cajas_stock = sum(p.stock_cajas for p in productos)
    total_ventas_dinero = sum(v.total for v in ventas_cobradas)
    total_costos = sum(v.costo_total for v in ventas_cobradas)
    total_ganancias = sum(v.ganancia for v in ventas_cobradas)
    
    total_cajas_vendidas = sum(
        sum(d.cantidad_cajas for d in v.detalles) if hasattr(v, 'detalles') and v.detalles else getattr(v, 'cantidad_cajas', 0)
        for v in ventas_list
    )

    alertas_stock = [p for p in productos if p.stock_cajas <= p.stock_minimo]

    return render_template(
        'dashboard.html',
        total_cajas_stock=total_cajas_stock,
        total_ventas_dinero=total_ventas_dinero,
        total_costos=total_costos,
        total_ganancias=total_ganancias,
        cant_clientes=len(clientes_list),
        total_cajas_vendidas=total_cajas_vendidas,
        alertas_stock=alertas_stock
    )


# ---------------------------------------------------------
# GESTIÓN DE PRODUCTOS Y PRECIOS
# ---------------------------------------------------------

@app.route('/productos', methods=['GET', 'POST'])
@login_required
def productos():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        marca = request.form.get('marca')
        sabor = request.form.get('sabor')
        contenido_caja = int(request.form.get('contenido_caja', 12))
        stock_cajas = int(request.form.get('stock_cajas', 0))
        stock_minimo = int(request.form.get('stock_minimo', 0))
        costo_caja = float(request.form.get('costo_caja', 0))

        nuevo_prod = Producto(
            nombre=nombre,
            marca=marca,
            sabor=sabor,
            contenido_caja=contenido_caja,
            stock_cajas=stock_cajas,
            stock_minimo=stock_minimo,
            costo_caja=costo_caja
        )
        db.session.add(nuevo_prod)
        db.session.commit()

        tipos = TipoCliente.query.all()
        for t in tipos:
            precio_val = request.form.get(f'precio_tipo_{t.id}')
            if precio_val:
                p_prod = PrecioProducto(
                    producto_id=nuevo_prod.id,
                    tipo_cliente_id=t.id,
                    precio_caja=float(precio_val)
                )
                db.session.add(p_prod)
        
        db.session.commit()
        return redirect(url_for('productos'))

    prods = Producto.query.all()
    tipos = TipoCliente.query.all()
    return render_template('productos.html', productos=prods, tipos_cliente=tipos)


@app.route('/productos/<int:producto_id>/ajustar-stock', methods=['POST'])
@login_required
def ajustar_stock(producto_id):
    nuevo_stock = int(request.form.get('nuevo_stock', 0))
    prod = db.session.get(Producto, producto_id) or db.first_or_404(Producto, producto_id)
    if nuevo_stock >= 0:
        prod.stock_cajas = nuevo_stock
        db.session.commit()
    return redirect(url_for('stock'))


@app.route('/productos/<int:producto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    prod = db.session.get(Producto, producto_id) or db.first_or_404(Producto, producto_id)
    tipos = TipoCliente.query.all()

    if request.method == 'POST':
        prod.nombre = request.form.get('nombre')
        prod.marca = request.form.get('marca')
        prod.sabor = request.form.get('sabor')
        prod.contenido_caja = int(request.form.get('contenido_caja', 12))
        prod.stock_cajas = int(request.form.get('stock_cajas', 0))
        prod.stock_minimo = int(request.form.get('stock_minimo', 5))
        prod.costo_caja = float(request.form.get('costo_caja', 0))

        for t in tipos:
            precio_val = request.form.get(f'precio_tipo_{t.id}')
            if precio_val:
                precio_obj = PrecioProducto.query.filter_by(
                    producto_id=prod.id, 
                    tipo_cliente_id=t.id
                ).first()

                if precio_obj:
                    precio_obj.precio_caja = float(precio_val)
                else:
                    nuevo_precio = PrecioProducto(
                        producto_id=prod.id,
                        tipo_cliente_id=t.id,
                        precio_caja=float(precio_val)
                    )
                    db.session.add(nuevo_precio)

        db.session.commit()
        return redirect(url_for('productos'))

    precios_map = {p.tipo_cliente_id: p.precio_caja for p in prod.precios}
    return render_template('editar_producto.html', producto=prod, tipos_cliente=tipos, precios_map=precios_map)


# ---------------------------------------------------------
# CONTROL DE STOCK
# ---------------------------------------------------------

@app.route('/stock')
@login_required
def stock():
    prods = Producto.query.all()
    tipos = TipoCliente.query.all()
    
    matriz_precios = {}
    for p in prods:
        matriz_precios[p.id] = {}
        for precio_obj in p.precios:
            if precio_obj.tipo_rel:
                matriz_precios[p.id][precio_obj.tipo_rel.nombre] = precio_obj.precio_caja

    return render_template('stock.html', productos=prods, tipos_cliente=tipos, precios=matriz_precios)


# ---------------------------------------------------------
# INGRESO DE COMPRAS
# ---------------------------------------------------------

@app.route('/compras', methods=['GET', 'POST'])
@login_required
def compras():
    if request.method == 'POST':
        producto_id = int(request.form.get('producto_id'))
        cantidad_cajas = int(request.form.get('cantidad_cajas'))
        costo_por_caja = float(request.form.get('costo_por_caja'))
        proveedor = request.form.get('proveedor')
        observaciones = request.form.get('observaciones')

        costo_total = cantidad_cajas * costo_por_caja

        nueva_compra = Compra(
            producto_id=producto_id,
            cantidad_cajas=cantidad_cajas,
            costo_por_caja=costo_por_caja,
            costo_total=costo_total,
            proveedor=proveedor,
            observaciones=observaciones
        )
        
        prod = db.session.get(Producto, producto_id)
        if prod:
            prod.stock_cajas += cantidad_cajas
            prod.costo_caja = costo_por_caja

        db.session.add(nueva_compra)
        db.session.commit()

        return redirect(url_for('compras'))

    lista_compras = Compra.query.order_by(Compra.fecha.desc()).all()
    prods = Producto.query.all()
    return render_template('compras.html', compras=lista_compras, productos=prods)


# ---------------------------------------------------------
# GESTIÓN DE CLIENTES
# ---------------------------------------------------------

@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def clientes():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        direccion = request.form.get('direccion')
        tipo_cliente_id = int(request.form.get('tipo_cliente_id'))

        nuevo_cliente = Cliente(
            nombre=nombre,
            telefono=telefono,
            email=email,
            direccion=direccion,
            tipo_cliente_id=tipo_cliente_id
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('clientes'))

    lista_clientes = Cliente.query.all()
    tipos = TipoCliente.query.all()
    return render_template('clientes.html', clientes=lista_clientes, tipos_cliente=tipos)


# ---------------------------------------------------------
# API AUTOCOMPLETADO Y VENTAS
# ---------------------------------------------------------

@app.route('/api/obtener-precio', methods=['GET'])
@login_required
def obtener_precio_api():
    cliente_id = request.args.get('cliente_id', type=int)
    producto_id = request.args.get('producto_id', type=int)

    if not cliente_id or not producto_id:
        return jsonify({'precio_sugerido': 0.0, 'stock_disponible': 0})

    cliente = db.session.get(Cliente, cliente_id)
    producto = db.session.get(Producto, producto_id)

    if not cliente or not producto:
        return jsonify({'precio_sugerido': 0.0, 'stock_disponible': 0})

    precio_obj = PrecioProducto.query.filter_by(
        producto_id=producto.id,
        tipo_cliente_id=cliente.tipo_cliente_id
    ).first()

    precio_sugerido = precio_obj.precio_caja if precio_obj else 0.0

    return jsonify({
        'precio_sugerido': precio_sugerido,
        'stock_disponible': producto.stock_cajas,
        'tipo_cliente': cliente.tipo_rel.nombre if cliente.tipo_rel else ''
    })


@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    if request.method == 'POST':
        cliente_id = int(request.form.get('cliente_id'))
        observaciones = request.form.get('observaciones')
        
        carrito_raw = request.form.get('carrito_json')
        items = json.loads(carrito_raw) if carrito_raw else []

        if not items:
            flash("Debe agregar al menos un producto a la venta.", "danger")
            return redirect(url_for('ventas'))

        # Validar stock antes de crear
        for item in items:
            prod = db.session.get(Producto, item['producto_id'])
            if not prod or item['cantidad'] > prod.stock_cajas:
                nombre = prod.nombre if prod else "Desconocido"
                disponible = prod.stock_cajas if prod else 0
                flash(f"Error: Stock insuficiente para {nombre}. Disponible: {disponible}", "danger")
                return redirect(url_for('ventas'))

        total_venta = 0.0
        costo_total_venta = 0.0

        nueva_venta = Venta(
            cliente_id=cliente_id,
            observaciones=observaciones,
            total=0, costo_total=0, ganancia=0,
            monto_efectivo=0.0,
            monto_transferencia=0.0
        )
        db.session.add(nueva_venta)
        db.session.flush()

        for item in items:
            prod = db.session.get(Producto, item['producto_id'])
            cant = int(item['cantidad'])
            precio = float(item['precio'])
            
            subtotal = cant * precio
            costo_sub = cant * (prod.costo_caja or 0)

            detalle = DetalleVenta(
                venta_id=nueva_venta.id,
                producto_id=prod.id,
                cantidad_cajas=cant,
                precio_por_caja=precio,
                subtotal=subtotal,
                costo_subtotal=costo_sub
            )
            
            prod.stock_cajas -= cant
            
            total_venta += subtotal
            costo_total_venta += costo_sub
            db.session.add(detalle)

        # Asignar los montos de pago según el método elegido
        nueva_venta.total = total_venta
        nueva_venta.costo_total = costo_total_venta
        nueva_venta.ganancia = total_venta - costo_total_venta

        if observaciones == 'Mixto':
            monto_ef = float(request.form.get('monto_efectivo') or 0)
            monto_tr = float(request.form.get('monto_transferencia') or 0)
            
            # Validación de seguridad backend
            if abs((monto_ef + monto_tr) - total_venta) > 0.01:
                db.session.rollback()
                flash("Error: La suma de efectivo y transferencia no coincide con el total de la venta.", "danger")
                return redirect(url_for('ventas'))

            nueva_venta.monto_efectivo = monto_ef
            nueva_venta.monto_transferencia = monto_tr
        elif observaciones == 'Efectivo':
            nueva_venta.monto_efectivo = total_venta
            nueva_venta.monto_transferencia = 0.0
        elif observaciones == 'Transferencia':
            nueva_venta.monto_efectivo = 0.0
            nueva_venta.monto_transferencia = total_venta
        else:
            nueva_venta.monto_efectivo = 0.0
            nueva_venta.monto_transferencia = 0.0

        db.session.commit()
        flash('Venta registrada con éxito.', 'success')
        return redirect(url_for('ventas'))

    # GET
    estado_filtro = request.args.get('estado', 'todos')
    todas_las_ventas = Venta.query.order_by(Venta.fecha.desc()).all()

    if estado_filtro != 'todos':
        ventas_filtradas = [v for v in todas_las_ventas if v.observaciones and estado_filtro in v.observaciones]
    else:
        ventas_filtradas = todas_las_ventas

    clientes = Cliente.query.all()
    productos = Producto.query.filter(Producto.stock_cajas > 0).all()

    # Cálculo de los subtotales globales (incluyendo desgloses de pagos mixtos)
    totales = {
        'Efectivo': sum((v.monto_efectivo or (v.total if v.observaciones == 'Efectivo' else 0)) for v in todas_las_ventas),
        'Transferencia': sum((v.monto_transferencia or (v.total if v.observaciones == 'Transferencia' else 0)) for v in todas_las_ventas),
        'Debiendo': sum(v.total for v in todas_las_ventas if v.observaciones and 'Debiendo' in v.observaciones),
        'En Proceso': sum(v.total for v in todas_las_ventas if v.observaciones and 'En Proceso' in v.observaciones),
    }

    return render_template(
        'ventas.html',
        ventas=ventas_filtradas,
        totales=totales,
        clientes=clientes,
        productos=productos,
        estado_filtro=estado_filtro
    )
# ---------------------------------------------------------
# BALANCE Y HISTORIAL
# ---------------------------------------------------------

@app.route('/balance')
@login_required
def balance():
    filtro = request.args.get('filtro', 'mes')
    hoy = datetime.now(timezone.utc).date()

    query = Venta.query

    if filtro == 'hoy':
        query = query.filter(db.func.date(Venta.fecha) == hoy)
    elif filtro == 'semana':
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        query = query.filter(db.func.date(Venta.fecha) >= inicio_semana)
    elif filtro == 'mes':
        query = query.filter(db.extract('month', Venta.fecha) == hoy.month, db.extract('year', Venta.fecha) == hoy.year)
    elif filtro == 'anio':
        query = query.filter(db.extract('year', Venta.fecha) == hoy.year)

    ventas_filtradas = query.order_by(Venta.fecha.desc()).all()

    ventas_cobradas = [
        v for v in ventas_filtradas 
        if v.observaciones and ('Efectivo' in v.observaciones or 'Transferencia' in v.observaciones)
    ]

    ingresos = sum(v.total for v in ventas_cobradas)
    costos = sum(v.costo_total for v in ventas_cobradas)
    ganancia = sum(v.ganancia for v in ventas_cobradas)

    return render_template(
        'balance.html',
        ingresos=ingresos,
        costos=costos,
        ganancia=ganancia,
        filtro_actual=filtro,
        ventas=ventas_cobradas
    )


@app.route('/historial')
@login_required
def historial():
    compras_list = Compra.query.all()
    ventas_list = Venta.query.all()

    movimientos = []

    for c in compras_list:
        movimientos.append({
            'fecha': c.fecha,
            'tipo': 'COMPRA (+ Stock)',
            'producto': f"{c.producto.nombre} ({c.producto.sabor})",
            'cajas': f"+{c.cantidad_cajas}",
            'detalle': f"Proveedor: {c.proveedor or '-'}",
            'monto': f"-${c.costo_total:,.2f}"
        })

    for v in ventas_list:
        detalles_prod = ", ".join([f"{d.producto.nombre} x{d.cantidad_cajas}" for d in v.detalles]) if hasattr(v, 'detalles') and v.detalles else "Venta"
        movimientos.append({
            'fecha': v.fecha,
            'tipo': 'VENTA (- Stock)',
            'producto': detalles_prod,
            'cajas': f"-{sum(d.cantidad_cajas for d in v.detalles) if hasattr(v, 'detalles') and v.detalles else 0}",
            'detalle': f"Cliente: {v.cliente.nombre}",
            'monto': f"+${v.total:,.2f}"
        })

    movimientos.sort(key=lambda x: x['fecha'], reverse=True)

    return render_template('historial.html', movimientos=movimientos)


# ---------------------------------------------------------
# RUTAS DE ELIMINACIÓN Y EDICIÓN
# ---------------------------------------------------------

@app.route('/productos/<int:producto_id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    prod = db.session.get(Producto, producto_id) or db.first_or_404(Producto, producto_id)
    db.session.delete(prod)
    db.session.commit()
    flash("Producto eliminado correctamente.", "info")
    return redirect(url_for('productos'))


@app.route('/compras/<int:compra_id>/eliminar', methods=['POST'])
@login_required
def eliminar_compra(compra_id):
    compra = db.session.get(Compra, compra_id) or db.first_or_404(Compra, compra_id)
    producto = db.session.get(Producto, compra.producto_id)
    
    if producto:
        producto.stock_cajas = max(0, producto.stock_cajas - compra.cantidad_cajas)

    db.session.delete(compra)
    db.session.commit()
    flash("Compra eliminada y stock descontado correctamente.", "info")
    return redirect(url_for('compras'))


@app.route('/clientes/<int:cliente_id>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id) or db.first_or_404(Cliente, cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente eliminado correctamente.", "info")
    return redirect(url_for('clientes'))


@app.route('/ventas/<int:venta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_venta(venta_id):
    venta = db.session.get(Venta, venta_id) or db.first_or_404(Venta, venta_id)
    
    if hasattr(venta, 'detalles') and venta.detalles:
        for detalle in venta.detalles:
            producto = db.session.get(Producto, detalle.producto_id)
            if producto:
                producto.stock_cajas += detalle.cantidad_cajas

    db.session.delete(venta)
    db.session.commit()
    flash("Venta eliminada y stock devuelto correctamente.", "info")
    return redirect(url_for('ventas'))


@app.route('/ventas/<int:venta_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_venta(venta_id):
    venta = db.session.get(Venta, venta_id) or db.first_or_404(Venta, venta_id)

    if request.method == 'POST':
        venta.cliente_id = int(request.form.get('cliente_id'))
        venta.observaciones = request.form.get('observaciones')

        nuevo_total = 0.0
        nuevo_costo_total = 0.0

        for d in venta.detalles:
            nueva_cant = int(request.form.get(f'cantidad_{d.id}', d.cantidad_cajas))
            nuevo_precio = float(request.form.get(f'precio_{d.id}', d.precio_por_caja))

            producto = db.session.get(Producto, d.producto_id)
            if producto:
                stock_disponible = producto.stock_cajas + d.cantidad_cajas
                if nueva_cant > stock_disponible:
                    flash(f"Error: Stock insuficiente para {producto.nombre}. Disponible: {stock_disponible}", "danger")
                    return redirect(url_for('editar_venta', venta_id=venta.id))

                diferencia = nueva_cant - d.cantidad_cajas
                producto.stock_cajas -= diferencia

            d.cantidad_cajas = nueva_cant
            d.precio_por_caja = nuevo_precio
            d.subtotal = nueva_cant * nuevo_precio
            d.costo_subtotal = nueva_cant * (producto.costo_caja or 0 if producto else 0)

            nuevo_total += d.subtotal
            nuevo_costo_total += d.costo_subtotal

        venta.total = nuevo_total
        venta.costo_total = nuevo_costo_total
        venta.ganancia = nuevo_total - nuevo_costo_total

        db.session.commit()
        flash("Venta modificada con éxito.", "success")
        return redirect(url_for('ventas'))

    clientes = Cliente.query.all()
    return render_template('editar_venta.html', venta=venta, clientes=clientes)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
