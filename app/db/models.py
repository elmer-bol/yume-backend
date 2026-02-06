from sqlalchemy import Column, Integer, String, Float, Numeric, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Importamos la Base del archivo de conexión
from .database import Base

# ==============================================================================
# MÓDULO DE SEGURIDAD Y AUDITORÍA (INTACTO)
# ==============================================================================

class Rol(Base):
    __tablename__ = 'rol'
    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)
    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = 'usuario'
    id_usuario = Column(Integer, primary_key=True, index=True)
    id_persona = Column(Integer, ForeignKey('persona.id_persona'), nullable=False)
    id_rol = Column(Integer, ForeignKey('rol.id_rol'), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=True)
    auth_provider = Column(String(20), default='local')
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    persona = relationship("Persona", back_populates="usuario_sistema")
    rol = relationship("Rol", back_populates="usuarios")
    transacciones_creadas = relationship("TransaccionIngreso", back_populates="usuario_creador")
    egresos_creados = relationship("Egreso", back_populates="usuario_creador")
    depositos_creados = relationship("Deposito", back_populates="usuario_creador")
    logs_auditoria = relationship("AuditLog", back_populates="usuario")

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id_log = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id_usuario'))
    fecha = Column(DateTime, default=datetime.utcnow)
    accion = Column(String(20), nullable=False)
    tabla = Column(String(50), nullable=False)
    id_registro_afectado = Column(String(50))
    valores_anteriores = Column(JSON, nullable=True)
    valores_nuevos = Column(JSON, nullable=True)
    motivo = Column(String(255), nullable=True)
    ip_origen = Column(String(50), nullable=True)
    usuario = relationship("Usuario", back_populates="logs_auditoria")

# ==============================================================================
# MÓDULO CONTABLE Y CATÁLOGOS (AQUÍ ESTÁN LOS CAMBIOS GRANDES)
# ==============================================================================

class Categoria(Base):
    __tablename__ = 'catalogo'
    id_catalogo = Column(Integer, primary_key=True, index=True)
    
    # ### NUEVO ###
    # Código jerárquico (Ej: '1.1.01', '5.2.01')
    codigo = Column(String(20), unique=True, nullable=False)
    
    nombre_cuenta = Column(String(100), nullable=False) # Aumenté tamaño a 100
    tipo = Column(String(20), nullable=False) # 'ACTIVO', 'PASIVO', 'INGRESO', 'EGRESO'
    
    # ### NUEVO ###
    # Define si es un título agrupador (True) o una cuenta imputable (False)
    es_rubro = Column(Boolean, default=False)
    
    activo = Column(Boolean, default=True)

    egresos = relationship("Egreso", back_populates="catalogo")
    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="categoria")

class TipoEgreso(Base):
    __tablename__ = 'tipo_egreso'
    id_tipo_egreso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    requiere_num_doc = Column(Boolean, default=False)
    # Enlace al RUBRO PADRE contable (Ej: 5.2.1.00 Servicios Básicos)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=True)
    activo = Column(Boolean, default=True)
    egresos = relationship("Egreso", back_populates="tipo_egreso")
 
    # Relación para acceder a los datos del rubro desde el código
    rubro_contable = relationship("Categoria")

class MedioIngreso(Base):
    # CONCEPTUALMENTE: BILLETERAS O TESORERÍA (Activos Líquidos)
    __tablename__ = 'medio_ingreso'
    id_medio_ingreso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    tipo = Column(String(20), nullable=False) # 'Efectivo', 'Banco'
    
    # Enlace a la cuenta contable de ACTIVO (Ej: 1.1.01 Caja)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=False)
    
    requiere_referencia = Column(Boolean, default=False)
    
    # ### NUEVO (Para tu lógica de 1000 Bs) ###
    limite_maximo = Column(Numeric(10, 2), default=0.00) # 0 = Sin límite
    
    activo = Column(Boolean, default=True)

    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="medio_ingreso")
    cuenta_contable = relationship("Categoria")

# --- PERSONAS Y UNIDADES DE SERVICIO (INTACTO) ---

class Persona(Base):
    __tablename__ = 'persona'
    id_persona = Column(Integer, primary_key=True, index=True)
    nombres = Column(String(50), nullable=False)
    apellidos = Column(String(50), nullable=False)
    telefono = Column(String(15), nullable=False)
    celular = Column(String(15), nullable=False)
    email = Column(String(100))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    usuario_sistema = relationship("Usuario", back_populates="persona", uselist=False)
    roles = relationship("RelacionCliente", back_populates="persona")
    items_facturables = relationship("ItemFacturable", back_populates="persona")
    planes_pago = relationship("PlanPago", back_populates="persona")

class UnidadServicio(Base):
    __tablename__ = 'unidad_servicio'
    id_unidad = Column(Integer, primary_key=True, index=True)
    identificador_unico = Column(String(50), nullable=False, unique=True)
    tipo_unidad = Column(String(50))
    descripcion = Column(String(200), nullable=True)
    estado = Column(String(20))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    relaciones = relationship("RelacionCliente", back_populates="unidad")
    items_facturables = relationship("ItemFacturable", back_populates="unidad")

class RelacionCliente(Base):
    __tablename__ = 'relacion_cliente'
    id_relacion = Column(Integer, primary_key=True, index=True)
    id_persona = Column(Integer, ForeignKey('persona.id_persona'))
    id_unidad = Column(Integer, ForeignKey('unidad_servicio.id_unidad'))
    tipo_relacion = Column(String(20), nullable=False)  
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    estado = Column(String(20), default="Activo", nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    saldo_favor = Column(Numeric(10, 2), default=0.00, nullable=False)
    monto_mensual = Column(Numeric(10, 2), default=0.00)
    persona = relationship("Persona", back_populates="roles")
    unidad = relationship("UnidadServicio", back_populates="relaciones")

# --- FLUJO DE CAJA Y FACTURACIÓN (ACTUALIZADO) ---

class ConceptoDeuda(Base):
    __tablename__ = 'concepto_deuda'
    id_concepto = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True) 
    descripcion = Column(String(200))
    
    # ### NUEVO ###
    # Enlace a la cuenta contable de INGRESO (Ej: 4.1.01 Expensas)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=True)
    
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    items_facturables = relationship("ItemFacturable", back_populates="concepto")
    cuenta_contable = relationship("Categoria") # Nueva relación

class ItemFacturable(Base):
    __tablename__ = 'item_facturable'
    __table_args__ = (
        UniqueConstraint('id_unidad', 'id_concepto', 'periodo', 'id_persona', name='uq_item_facturable_periodo'),
        Index('ix_item_facturable_persona_unidad', 'id_persona', 'id_unidad'),
        Index('ix_item_estado_vencimiento', 'estado', 'fecha_vencimiento'),
    )
    id_item = Column(Integer, primary_key=True, index=True)
    id_unidad = Column(Integer, ForeignKey('unidad_servicio.id_unidad'))
    id_concepto = Column(Integer, ForeignKey('concepto_deuda.id_concepto'))
    id_persona = Column(Integer, ForeignKey('persona.id_persona'))
    id_plan = Column(Integer, ForeignKey('plan_pago.id_plan'), nullable=True)
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=True)
    id_usuario_modificacion = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=True)

    monto_base = Column(Numeric(10, 2), nullable=False)
    monto_abonado = Column(Numeric(10, 2), default=0.00)
    periodo = Column(String(50), nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(String(20), default='pendiente')
    saldo_pendiente = Column(Numeric(10, 2), nullable=False)
    año = Column(Integer)  
    mes = Column(Integer)  
    bloqueo_pago_automatico = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unidad = relationship("UnidadServicio", back_populates="items_facturables")
    concepto = relationship("ConceptoDeuda", back_populates="items_facturables")
    persona = relationship("Persona", back_populates="items_facturables")
    detalles_pago = relationship("TransaccionIngresoDetalle", back_populates="item_facturable")
    plan = relationship("PlanPago", back_populates="items")

class Egreso(Base):
    __tablename__ = 'egreso'
    id_egreso = Column(Integer, primary_key=True, index=True)
    id_tipo_egreso = Column(Integer, ForeignKey('tipo_egreso.id_tipo_egreso'), nullable=False)
    
    # CUENTA CONTABLE (DEBE) - En qué gasté
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'))
    
    # ORIGEN DE FONDOS (HABER) - De qué caja salió
    id_medio_pago = Column(Integer, ForeignKey('medio_ingreso.id_medio_ingreso'), nullable=False)
    
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'))
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    beneficiario = Column(String(100), nullable=False)
    num_comprobante = Column(String(50))
    descripcion = Column(String(200))
    estado = Column(String(20), default='registrado') 
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tipo_egreso = relationship("TipoEgreso", back_populates="egresos")
    catalogo = relationship("Categoria", back_populates="egresos")
    usuario_creador = relationship("Usuario", back_populates="egresos_creados")
    medio_pago = relationship("MedioIngreso")
class Deposito(Base):
    __tablename__ = 'deposito'
    id_deposito = Column(Integer, primary_key=True, index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    num_referencia = Column(String(50))
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'))
    banco = Column(String(50))
    cuenta_destino = Column(String(50))
    estado = Column(String(20), default='pendiente')  
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_creador = relationship("Usuario", back_populates="depositos_creados")
    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="deposito")

class TransaccionIngreso(Base):
    __tablename__ = 'transaccion_ingreso'
    id_transaccion = Column(Integer, primary_key=True, index=True)
    id_relacion = Column(Integer, ForeignKey('relacion_cliente.id_relacion'), nullable=False)
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=False)
    id_medio_ingreso = Column(Integer, ForeignKey('medio_ingreso.id_medio_ingreso'), nullable=False)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=False)
    id_deposito = Column(Integer, ForeignKey('deposito.id_deposito'), nullable=True)
    monto_total = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False, index=True) 
    num_documento = Column(String(50))
    estado = Column(String(20), default='registrado') 
    descripcion = Column(String(200))
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fecha_anulacion = Column(DateTime, nullable=True) 
    monto_billetera_usado = Column(Numeric(10, 2), default=0.00)

    medio_ingreso = relationship("MedioIngreso", back_populates="transacciones_ingreso")
    categoria = relationship("Categoria", back_populates="transacciones_ingreso")
    deposito = relationship("Deposito", back_populates="transacciones_ingreso")
    usuario_creador = relationship("Usuario", back_populates="transacciones_creadas")
    relacion_cliente = relationship("RelacionCliente") 
    detalles = relationship("TransaccionIngresoDetalle", back_populates="transaccion")

class TransaccionIngresoDetalle(Base):
    __tablename__ = 'transaccion_ingreso_detalle'
    id_detalle = Column(Integer, primary_key=True, index=True)
    id_transaccion = Column(Integer, ForeignKey('transaccion_ingreso.id_transaccion'))
    id_item = Column(Integer, ForeignKey('item_facturable.id_item'))
    monto_aplicado = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(20), default='aplicado') 
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)
    saldo_anterior = Column(Numeric(10, 2))  
    saldo_posterior = Column(Numeric(10, 2))  
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    transaccion = relationship("TransaccionIngreso", back_populates="detalles")
    item_facturable = relationship("ItemFacturable", back_populates="detalles_pago")

class PlanPago(Base):
    __tablename__ = 'plan_pago'
    id_plan = Column(Integer, primary_key=True, index=True)
    id_persona = Column(Integer, ForeignKey('persona.id_persona'), nullable=False)
    monto_total_deuda = Column(Numeric(10, 2), nullable=False)
    numero_cuotas = Column(Integer, nullable=False)            
    monto_cuota_mensual = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date, default=datetime.utcnow)
    observaciones = Column(String(255))
    estado = Column(String(20), default='activo') 
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    persona = relationship("Persona", back_populates="planes_pago")
    items = relationship("ItemFacturable", back_populates="plan")