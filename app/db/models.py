from sqlalchemy import Column, Integer, String, Float, Numeric, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Importamos la Base del archivo de conexión
from .database import Base

# ==============================================================================
# 🛡️ MÓDULO DE SEGURIDAD Y AUDITORÍA (FASE 2)
# ==============================================================================

class Rol(Base):
    """
    Define los perfiles de acceso (RBAC Estático).
    Ej: 1=SuperAdmin, 2=Cajero, 3=Inquilino.
    """
    __tablename__ = 'rol'
    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    """
    La entidad que se loguea en el sistema.
    Soporta Login Local (Password) y Social (Google/QR).
    """
    __tablename__ = 'usuario'
    id_usuario = Column(Integer, primary_key=True, index=True)
    
    # Vinculación con la Persona Real (Datos demográficos)
    id_persona = Column(Integer, ForeignKey('persona.id_persona'), nullable=False)
    id_rol = Column(Integer, ForeignKey('rol.id_rol'), nullable=False)

    # Credenciales
    email = Column(String(100), unique=True, index=True, nullable=False) # Username universal
    password_hash = Column(String(200), nullable=True) # Null si entra con Google/QR
    
    # Origen de la cuenta (Para el futuro módulo QR)
    auth_provider = Column(String(20), default='local') # 'local', 'google', 'qr_token'
    
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    persona = relationship("Persona", back_populates="usuario_sistema")
    rol = relationship("Rol", back_populates="usuarios")
    
    # Trazabilidad: Un usuario crea transacciones, no una "persona"
    transacciones_creadas = relationship("TransaccionIngreso", back_populates="usuario_creador")
    egresos_creados = relationship("Egreso", back_populates="usuario_creador")
    depositos_creados = relationship("Deposito", back_populates="usuario_creador")
    logs_auditoria = relationship("AuditLog", back_populates="usuario")

class AuditLog(Base):
    """
    La Caja Negra. Registra cambios críticos (Edición/Eliminación).
    """
    __tablename__ = 'audit_log'
    id_log = Column(Integer, primary_key=True, index=True)
    
    id_usuario = Column(Integer, ForeignKey('usuario.id_usuario'))
    fecha = Column(DateTime, default=datetime.utcnow)
    
    # Qué pasó
    accion = Column(String(20), nullable=False) # CREATE, UPDATE, DELETE, LOGIN
    tabla = Column(String(50), nullable=False)  # 'transaccion_ingreso', 'egreso'
    id_registro_afectado = Column(String(50))   # El ID del dato tocado
    
    # Evidencia Forense
    valores_anteriores = Column(JSON, nullable=True) # Snapshot del dato antes de morir
    valores_nuevos = Column(JSON, nullable=True)     # Snapshot del dato nuevo
    
    motivo = Column(String(255), nullable=True) # "Error de dedo", "Solicitud de Gerencia"
    ip_origen = Column(String(50), nullable=True)

    usuario = relationship("Usuario", back_populates="logs_auditoria")

# ==============================================================================
# FIN MÓDULO SEGURIDAD
# ==============================================================================

# --- CATÁLOGOS Y UNIVERSALIDAD ---

class Categoria(Base):
    __tablename__ = 'catalogo'
    id_catalogo = Column(Integer, primary_key=True, index=True)
    nombre_cuenta = Column(String(50), nullable=False, unique=True)
    tipo = Column(String(10), nullable=False) 
    activo = Column(Boolean, default=True)

    egresos = relationship("Egreso", back_populates="catalogo")
    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="categoria")

class TipoEgreso(Base):
    __tablename__ = 'tipo_egreso'
    id_tipo_egreso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    requiere_num_doc = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    egresos = relationship("Egreso", back_populates="tipo_egreso")

class MedioIngreso(Base):
    __tablename__ = 'medio_ingreso'
    id_medio_ingreso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    tipo = Column(String(20), nullable=False)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=False)
    requiere_referencia = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="medio_ingreso")
    cuenta_contable = relationship("Categoria")

# --- PERSONAS Y UNIDADES DE SERVICIO ---

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

    # ### MODIFICADO ###
    # Agregamos la relación inversa hacia Usuario
    usuario_sistema = relationship("Usuario", back_populates="persona", uselist=False)

    roles = relationship("RelacionCliente", back_populates="persona")
    items_facturables = relationship("ItemFacturable", back_populates="persona")
    
    # NOTA: Las relaciones directas de transacciones ahora van a 'Usuario', no a 'Persona'.
    # Si necesitas saber qué persona hizo algo, vas: Transaccion -> Usuario -> Persona.

class UnidadServicio(Base):
    __tablename__ = 'unidad_servicio'
    id_unidad = Column(Integer, primary_key=True, index=True)
    identificador_unico = Column(String(50), nullable=False, unique=True)
    tipo_unidad = Column(String(50))
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

# --- FLUJO DE CAJA Y FACTURACIÓN ---

class ConceptoDeuda(Base):
    __tablename__ = 'concepto_deuda'
    id_concepto = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True) 
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    items_facturables = relationship("ItemFacturable", back_populates="concepto")

# BUSCA LA CLASE ItemFacturable Y REEMPLÁZALA CON ESTA VERSIÓN MEJORADA
class ItemFacturable(Base):
    __tablename__ = 'item_facturable'
    __table_args__ = (
        UniqueConstraint('id_unidad', 'id_concepto', 'periodo', 'id_persona', name='uq_item_facturable_periodo'),
        Index('ix_item_facturable_persona_unidad', 'id_persona', 'id_unidad'),
        Index('ix_item_estado_vencimiento', 'estado', 'fecha_vencimiento'),
        Index('ix_item_persona_estado', 'id_persona', 'estado'),
        Index('ix_item_periodo_estado', 'periodo', 'estado'),
        Index('ix_item_fecha_vencimiento', 'fecha_vencimiento'),
    )
    id_item = Column(Integer, primary_key=True, index=True)
    id_unidad = Column(Integer, ForeignKey('unidad_servicio.id_unidad'))
    id_concepto = Column(Integer, ForeignKey('concepto_deuda.id_concepto'))
    id_persona = Column(Integer, ForeignKey('persona.id_persona'))
    
    # --- AUDITORÍA NUEVA ---
    # Nota: Si ya tienes datos en producción, estos campos deben ser nullable=True al principio
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=True)
    id_usuario_modificacion = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=True)
    # -----------------------

    monto_base = Column(Numeric(10, 2), nullable=False)
    periodo = Column(String(10), nullable=False)
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
    
    # Relaciones de auditoría (Opcional, pero útil)
    usuario_creador = relationship("Usuario", foreign_keys=[id_usuario_creador])
    usuario_modificador = relationship("Usuario", foreign_keys=[id_usuario_modificacion])

class Egreso(Base):
    __tablename__ = 'egreso'
    id_egreso = Column(Integer, primary_key=True, index=True)
    id_tipo_egreso = Column(Integer, ForeignKey('tipo_egreso.id_tipo_egreso'), nullable=False)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'))
    
    # ### MODIFICADO ###
    # Antes apuntaba a Persona, ahora a Usuario (para saber login y rol)
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'))
    
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    beneficiario = Column(String(100), nullable=False)
    num_comprobante = Column(String(50))
    descripcion = Column(String(200))
    estado = Column(String(20), default='registrado') 
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tipo_egreso = relationship("TipoEgreso", back_populates="egresos")
    catalogo = relationship("Categoria", back_populates="egresos")
    # ### MODIFICADO ###
    usuario_creador = relationship("Usuario", back_populates="egresos_creados")

class Deposito(Base):
    __tablename__ = 'deposito'
    id_deposito = Column(Integer, primary_key=True, index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    num_referencia = Column(String(50))
    
    # ### MODIFICADO ###
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'))
    
    banco = Column(String(50))
    cuenta_destino = Column(String(50))
    estado = Column(String(20), default='pendiente')  
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ### MODIFICADO ###
    usuario_creador = relationship("Usuario", back_populates="depositos_creados")
    transacciones_ingreso = relationship("TransaccionIngreso", back_populates="deposito")

class TransaccionIngreso(Base):
    __tablename__ = 'transaccion_ingreso'
    __table_args__ = (
        Index('ix_transaccion_fecha_estado', 'fecha', 'estado'),
        Index('ix_transaccion_persona_fecha', 'id_usuario_creador', 'fecha'),
        Index('ix_transaccion_medio_fecha', 'id_medio_ingreso', 'fecha'),
        Index('ix_transaccion_relacion', 'id_relacion'),
    )
    id_transaccion = Column(Integer, primary_key=True, index=True)
    id_relacion = Column(Integer, ForeignKey('relacion_cliente.id_relacion'), nullable=False)
    
    # ### MODIFICADO ###
    # Cambiamos el ForeignKey de 'persona.id_persona' a 'usuario.id_usuario'
    id_usuario_creador = Column(Integer, ForeignKey('usuario.id_usuario'), nullable=False)

    id_medio_ingreso = Column(Integer, ForeignKey('medio_ingreso.id_medio_ingreso'), nullable=False)
    id_catalogo = Column(Integer, ForeignKey('catalogo.id_catalogo'), nullable=False)
    id_deposito = Column(Integer, ForeignKey('deposito.id_deposito'), nullable=True)
    monto_total = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, nullable=False)
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
    
    # ### MODIFICADO ###
    usuario_creador = relationship("Usuario", back_populates="transacciones_creadas")
    
    relacion_cliente = relationship("RelacionCliente") 
    detalles = relationship("TransaccionIngresoDetalle", back_populates="transaccion")

class TransaccionIngresoDetalle(Base):
    # Sin cambios, pero se mantiene para que el archivo esté completo si lo necesitas
    __tablename__ = 'transaccion_ingreso_detalle'
    __table_args__ = (
        Index('ix_detalle_item_transaccion', 'id_item', 'id_transaccion'),
        Index('ix_detalle_estado_fecha', 'estado', 'fecha_aplicacion'),
    )
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