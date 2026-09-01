from datetime import datetime
from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
    nombre = db.Column(db.String(50), unique=True, nullable=False) # ej: Mayorista, Revendedor, Minorista
    
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
    contenido_caja = db.Column(db.Integer, nullable=False) # Unidades por caja (solo informativo)
    stock_cajas = db.Column(db.Integer, default=0, nullable=False)
    stock_minimo = db.Column(db.Integer, default=5, nullable=False)
    costo_caja = db.Column(db.Float, default=0.0, nullable=False)

    # Relaciones
    precios = db.relationship('PrecioProducto', backref='producto', cascade="all, delete-orphan", lazy=True)
    compras = db.relationship('Compra', backref='producto', lazy=True)
    ventas = db.relationship('Venta', backref='producto', lazy=True)

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
    precio_caja = db.Column(db.Float, nullable=False)

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
    fecha_alta = db.Column(db.DateTime, default=datetime.utcnow)

    ventas = db.relationship('Venta', backref='cliente', lazy=True)


class Compra(db.Model):
    __tablename__ = 'compra'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad_cajas = db.Column(db.Integer, nullable=False)
    costo_por_caja = db.Column(db.Float, nullable=False)
    costo_total = db.Column(db.Float, nullable=False)
    proveedor = db.Column(db.String(100), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text, nullable=True)


class Venta(db.Model):
    __tablename__ = 'venta'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad_cajas = db.Column(db.Integer, nullable=False)
    precio_por_caja = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    costo_total = db.Column(db.Float, nullable=False)
    ganancia = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text, nullable=True)
