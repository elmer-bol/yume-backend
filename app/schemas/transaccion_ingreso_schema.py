# Archivo: app/schemas/transaccion_ingreso_schema.py
from pydantic import BaseModel, Field, model_validator, ConfigDict
from datetime import date, datetime
from typing import Optional, List

# ======================================================================
# ESQUEMAS DE APOYO PARA REPORTES
# ======================================================================

class PersonaInfoSimple(BaseModel):
    nombres: str
    apellidos: str
    model_config = ConfigDict(from_attributes=True)

class UnidadInfoSimple(BaseModel):
    identificador_unico: str
    model_config = ConfigDict(from_attributes=True)

class RelacionClienteReporte(BaseModel):
    id_relacion: int
    persona: Optional[PersonaInfoSimple] = None
    unidad: Optional[UnidadInfoSimple] = None
    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# ESQUEMAS PARA EL DETALLE
# ======================================================================

class TransaccionDetalleIn(BaseModel):
    id_item: int = Field(..., description="ID del Item Facturable.")
    monto_aplicado: float = Field(..., gt=0, description="Monto a pagar.")
    model_config = ConfigDict(from_attributes=True)

class ItemFacturableInfo(BaseModel):
    id_item: int
    periodo: str            
    model_config = ConfigDict(from_attributes=True)

class TransaccionIngresoDetalleCreateInternal(BaseModel):
    id_transaccion: int
    id_item: int
    monto_aplicado: float
    saldo_anterior: Optional[float] = None
    saldo_posterior: Optional[float] = None
    estado: str = "APLICADO"
    model_config = ConfigDict(from_attributes=True)

class TransaccionIngresoDetalle(BaseModel):
    id_detalle: int
    id_transaccion: int
    id_item: int
    monto_aplicado: float
    estado: str
    item_facturable: Optional[ItemFacturableInfo] = None 
    fecha_aplicacion: datetime
    fecha_creacion: datetime
    saldo_anterior: Optional[float] = None
    saldo_posterior: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# ESQUEMAS PARA LA TRANSACCIÓN PRINCIPAL (MAESTRO)
# ======================================================================

class TransaccionIngresoBase(BaseModel):
    """Esquema base que contiene campos comunes de INPUT."""
    
    # SEGURIDAD: Eliminado. El Backend lo obtiene del Token.
    # id_usuario_creador: int = Field(..., description="ID del Cajero/Admin.")
    
    id_relacion: int = Field(..., description="ID de la Relación (Contrato) seleccionada.")
    id_medio_ingreso: int = Field(..., description="Medio de pago.")
    monto_total: float = Field(..., gt=0, description="Dinero total recibido.")
    fecha: date = Field(..., description="Fecha del ingreso.")
    num_documento: Optional[str] = Field(None, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=255)
    id_deposito: Optional[int] = Field(None)
    
    model_config = ConfigDict(from_attributes=True)
        
class TransaccionIngresoCreate(TransaccionIngresoBase):
    detalles: List[TransaccionDetalleIn] = Field(default=[], description="Lista de deudas a pagar.")
    monto_billetera_usado: Optional[float] = Field(default=0.0, ge=0)

    @model_validator(mode='after')
    def check_monto_covers_details(self) -> 'TransaccionIngresoCreate':
        if not self.detalles:
            return self

        sum_details = sum(detalle.monto_aplicado for detalle in self.detalles)
        billetera = self.monto_billetera_usado if self.monto_billetera_usado else 0.0
        total_disponible = self.monto_total + billetera

        if sum_details > total_disponible + 0.001:
             raise ValueError(
                f"Error de Cuadre: Estás intentando pagar ({sum_details}) "
                f"pero solo tienes disponible ({total_disponible}). Faltan fondos."
            )
            
        return self

class TransaccionIngresoCreateInternal(TransaccionIngresoBase):
    estado: str = Field(..., description="Estado inicial.")
    id_catalogo: int 
    model_config = ConfigDict(from_attributes=True)

class TransaccionIngresoUpdate(BaseModel):
    id_medio_ingreso: Optional[int] = None
    id_catalogo: Optional[int] = None
    id_usuario_creador: Optional[int] = None
    monto_total: Optional[float] = None
    fecha: Optional[date] = None
    num_documento: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TransaccionIngresoAnulacion(BaseModel):
    motivo_anulacion: str = Field(..., min_length=10)
    model_config = ConfigDict(from_attributes=True)
        
class TransaccionIngreso(TransaccionIngresoBase):
    id_transaccion: int
    estado: str
    id_catalogo: int 
    fecha_creacion: datetime
    fecha_modificacion: datetime 
    fecha_anulacion: Optional[datetime] = None
    monto_billetera_usado: float = 0.0
    detalles: List[TransaccionIngresoDetalle] = []  
    relacion_cliente: Optional[RelacionClienteReporte] = None
    
    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# ESQUEMAS PARA SIMULACIÓN
# ======================================================================

class DetalleSimulacion(BaseModel):
    id_item_facturable: int
    periodo: str
    monto_aplicado: float
    saldo_restante_deuda: float

class ResultadoSimulacionIngreso(BaseModel):
    monto_total_ingresado: float
    monto_usado_en_deudas: float
    monto_remanente_billetera: float
    detalles_sugeridos: List[DetalleSimulacion]