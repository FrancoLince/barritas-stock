from datetime import datetime, timedelta, timezone
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import db, init_db
from models import TipoCliente, Producto, PrecioProducto, Compra, Cliente, Venta, User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_key_super_secreta")

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
    # Seed de Tipos de Cliente iniciales
    tipos_defecto = ['Mayorista', 'Revendedor', 'Minorista']
    for nombre in tipos_defecto:
        if not TipoCliente.query.filter_by(nombre=nombre).first():
            db.session.add(TipoCliente(nombre=nombre))
    
    # Lista de usuarios a crear por defecto (Usuario, Contraseña)
    usuarios_iniciales = [
        ("admin", "AdminPassword123!"),
        ("vendedor1", "VentaPass2026!"),
        ("vendedor2", "VentaPass2026!"),
        ("deposito", "StockPass2026!")
    ]

    for username, password in usuarios_iniciales:
        if not User.query.filter_by(username=username).first():
            nuevo_usuario = User(username=username)
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
        
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
            login_user(user)
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

    total_cajas_stock = sum(p.stock_cajas for p in productos)
    total_ventas_dinero = sum(v.total for v in ventas_list)
    total_costos = sum(v.costo_total for v in ventas_list)
    total_ganancias = sum(v.ganancia for v in ventas_list)
    total_cajas_vendidas = sum(v.cantidad_cajas for v in ventas_list)

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
        'tipo_cliente': cliente.tipo_rel.nombre
    })


@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    if request.method == 'POST':
        cliente_id = int(request.form.get('cliente_id'))
        producto_id = int(request.form.get('producto_id'))
        cantidad_cajas = int(request.form.get('cantidad_cajas'))
        precio_por_caja = float(request.form.get('precio_por_caja'))
        observaciones = request.form.get('observaciones')

        producto = db.session.get(Producto, producto_id) or db.first_or_404(Producto, producto_id)

        if cantidad_cajas > producto.stock_cajas:
            return f"Error: No hay stock suficiente. Stock disponible: {producto.stock_cajas} cajas.", 400

        total_venta = cantidad_cajas * precio_por_caja
        costo_total_venta = cantidad_cajas * producto.costo_caja
        ganancia_venta = total_venta - costo_total_venta

        nueva_venta = Venta(
            cliente_id=cliente_id,
            producto_id=producto_id,
            cantidad_cajas=cantidad_cajas,
            precio_por_caja=precio_por_caja,
            total=total_venta,
            costo_total=costo_total_venta,
            ganancia=ganancia_venta,
            observaciones=f"Registrado por: {current_user.username}. " + (observaciones or "")
        )

        producto.stock_cajas -= cantidad_cajas

        db.session.add(nueva_venta)
        db.session.commit()

        return redirect(url_for('ventas'))

    lista_ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    clientes_list = Cliente.query.all()
    productos_list = Producto.query.filter(Producto.stock_cajas > 0).all()

    return render_template('ventas.html', ventas=lista_ventas, clientes=clientes_list, productos=productos_list)


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

    ingresos = sum(v.total for v in ventas_filtradas)
    costos = sum(v.costo_total for v in ventas_filtradas)
    ganancia = sum(v.ganancia for v in ventas_filtradas)

    return render_template(
        'balance.html',
        ingresos=ingresos,
        costos=costos,
        ganancia=ganancia,
        filtro_actual=filtro,
        ventas=ventas_filtradas
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
        movimientos.append({
            'fecha': v.fecha,
            'tipo': 'VENTA (- Stock)',
            'producto': f"{v.producto.nombre} ({v.producto.sabor})",
            'cajas': f"-{v.cantidad_cajas}",
            'detalle': f"Cliente: {v.cliente.nombre}",
            'monto': f"+${v.total:,.2f}"
        })

    movimientos.sort(key=lambda x: x['fecha'], reverse=True)

    return render_template('historial.html', movimientos=movimientos)


# ---------------------------------------------------------
# RUTAS DE ELIMINACIÓN
# ---------------------------------------------------------

@app.route('/productos/<int:producto_id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    prod = db.session.get(Producto, producto_id) or db.first_or_404(Producto, producto_id)
    PrecioProducto.query.filter_by(producto_id=prod.id).delete()
    db.session.delete(prod)
    db.session.commit()
    return redirect(url_for('productos'))


@app.route('/clientes/<int:cliente_id>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id) or db.first_or_404(Cliente, cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    return redirect(url_for('clientes'))


@app.route('/ventas/<int:venta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_venta(venta_id):
    venta = db.session.get(Venta, venta_id) or db.first_or_404(Venta, venta_id)
    producto = db.session.get(Producto, venta.producto_id)
    if producto:
        producto.stock_cajas += venta.cantidad_cajas

    db.session.delete(venta)
    db.session.commit()
    return redirect(url_for('ventas'))


@app.route('/compras/<int:compra_id>/eliminar', methods=['POST'])
@login_required
def eliminar_compra(compra_id):
    compra = db.session.get(Compra, compra_id) or db.first_or_404(Compra, compra_id)
    producto = db.session.get(Producto, compra.producto_id)
    if producto:
        producto.stock_cajas = max(0, producto.stock_cajas - compra.cantidad_cajas)

    db.session.delete(compra)
    db.session.commit()
    return redirect(url_for('compras'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
