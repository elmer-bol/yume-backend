# Archivo: app/schemas/transaccion_ingreso_detalle_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# --- CLASES BASE Y DE ENTRADA ---
class TransaccionIngresoDetalleBase(BaseModel):
    id_item: int = Field(..., description="ID del Item Facturable (la deuda).")
    monto_aplicado: float = Field(..., gt=0)
    
    class Config:
        from_attributes = True

class TransaccionDetalleIn(TransaccionIngresoDetalleBase):
    pass 

class TransaccionIngresoDetalleCreate(TransaccionIngresoDetalleBase):
    id_transaccion: int
    class Config:
        from_attributes = True

# --- CLASE INTERNA (Para el Repositorio) ---
class TransaccionIngresoDetalleCreateInternal(BaseModel):
    id_transaccion: int
    id_item: int = Field(..., description="ID de la deuda (FK).")
    monto_aplicado: float
    saldo_anterior: Optional[float] = None
    saldo_posterior: Optional[float] = None
    estado: str = "APLICADO"
    
    class Config:
        from_attributes = True

class TransaccionIngresoDetalleUpdate(BaseModel):
    estado: Optional[Literal["APLICADO", "REVERSADO", "ANULADO"]] = Field(None)
    class Config:
        from_attributes = True

# --- CLASE DE RESPUESTA (RESPONSE) ---
# Esta es la que estaba fallando. La alineamos con tu DB real.
class TransaccionIngresoDetalle(BaseModel):
    id_detalle: int
    id_transaccion: int
    id_item: int
    monto_aplicado: float
    estado: str 
    
    # Solo las fechas que SÍ existen en tu tabla
    fecha_aplicacion: datetime
    fecha_creacion: datetime
    
    # NO INCLUIMOS fecha_modificacion PORQUE NO EXISTE EN LA TABLA
    
    saldo_anterior: Optional[float] = None
    saldo_posterior: Optional[float] = None

    class Config:
        from_attributes = True