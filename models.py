from datetime import datetime, timezone, timedelta
from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Función auxiliar para la hora local de Argentina (UTC-3)
def obtener_fecha_argentina():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TipoCliente(db.Model):
    __tablename__ = 'tipo_cliente'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    
    clientes = db.relationship('Cliente', backref='tipo_rel', lazy=True)
    precios = db.relationship('PrecioProducto', backref='tipo_rel', lazy=True)

    def __repr__(self):
        return f"<TipoCliente {self.nombre}>"


class Producto(db.Model):
    __tablename__ = 'producto'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    sabor = db.Column(db.String(50), nullable=False)
    contenido_caja = db.Column(db.Integer, nullable=False)
    stock_cajas = db.Column(db.Integer, default=0, nullable=False)
    stock_minimo = db.Column(db.Integer, default=5, nullable=False)
    # Cambio a Numeric para evitar imprecisiones decimales
    costo_caja = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)

    precios = db.relationship('PrecioProducto', backref='producto', cascade="all, delete-orphan", lazy=True)
    detalles_compra = db.relationship('DetalleCompra', backref='producto', cascade="all, delete-orphan", lazy=True)
    detalles_venta = db.relationship('DetalleVenta', backref='producto', cascade="all, delete-orphan", lazy=True)

    @property
    def estado_stock(self):
        if self.stock_cajas == 0:
            return "AGOTADO"
        elif self.stock_cajas <= self.stock_minimo:
            return "STOCK BAJO"
        return "OK"


class PrecioProducto(db.Model):
    __tablename__ = 'precio_producto'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo_cliente_id = db.Column(db.Integer, db.ForeignKey('tipo_cliente.id'), nullable=False)
    precio_caja = db.Column(db.Numeric(10, 2), nullable=False)

    __table_args__ = (db.UniqueConstraint('producto_id', 'tipo_cliente_id', name='_prod_tipo_uc'),)


class Cliente(db.Model):
    __tablename__ = 'cliente'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    direccion = db.Column(db.String(150), nullable=True)
    tipo_cliente_id = db.Column(db.Integer, db.ForeignKey('tipo_cliente.id'), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    fecha_alta = db.Column(db.DateTime, default=obtener_fecha_argentina)

    ventas = db.relationship('Venta', backref='cliente', lazy=True)


class Compra(db.Model):
    __tablename__ = 'compra'

    id = db.Column(db.Integer, primary_key=True)
    proveedor = db.Column(db.String(100), nullable=True)
    fecha = db.Column(db.DateTime, default=obtener_fecha_argentina)
    costo_total = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    medio_pago = db.Column(db.String(50))
    monto_efectivo = db.Column(db.Numeric(10, 2), default=0.0)
    monto_transferencia = db.Column(db.Numeric(10, 2), default=0.0)

    detalles = db.relationship('DetalleCompra', backref='compra', cascade="all, delete-orphan", lazy=True)


class DetalleCompra(db.Model):
    __tablename__ = 'detalle_compra'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compra.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad_cajas = db.Column(db.Integer, nullable=False)
    costo_por_caja = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)


class Venta(db.Model):
    __tablename__ = 'venta'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=obtener_fecha_argentina)
    total = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    costo_total = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    ganancia = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    detalles = db.relationship('DetalleVenta', backref='venta', cascade="all, delete-orphan", lazy=True)
    monto_efectivo = db.Column(db.Numeric(10, 2), default=0.0)
    monto_transferencia = db.Column(db.Numeric(10, 2), default=0.0)


class DetalleVenta(db.Model):
    __tablename__ = 'detalle_venta'
    
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad_cajas = db.Column(db.Integer, nullable=False)
    precio_por_caja = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    costo_subtotal = db.Column(db.Numeric(10, 2), nullable=False)


class Caja(db.Model):
    __tablename__ = 'caja'

    id = db.Column(db.Integer, primary_key=True)
    saldo_efectivo = db.Column(db.Numeric(10, 2), default=0.0)
    saldo_transferencia = db.Column(db.Numeric(10, 2), default=0.0)
    
    @property
    def total(self):
        efectivo = float(self.saldo_efectivo) if self.saldo_efectivo is not None else 0.0
        transferencia = float(self.saldo_transferencia) if self.saldo_transferencia is not None else 0.0
        return efectivo + transferencia
