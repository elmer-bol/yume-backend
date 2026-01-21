# Archivo: app/schemas/egreso_schema.py
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional

# --- INPUT: REGISTRAR GASTO ---
class EgresoCreate(BaseModel):
    id_tipo_egreso: int = Field(..., description="ID del tipo de documento o clasificación fiscal")
    id_catalogo: int = Field(..., description="Cuenta contable del gasto (Debe ser tipo Egreso)")
    
    # SEGURIDAD: Eliminado. Ya no confiamos en que el usuario nos diga quién es.
    # id_administrador: int = Field(..., description="Quién registra el gasto")
    
    monto: float = Field(..., gt=0, description="Monto gastado")
    fecha: date
    beneficiario: str = Field(..., min_length=3, description="A quién se le pagó (Nombre empresa o persona)")
    num_comprobante: Optional[str] = Field(None, description="Número de factura o recibo")
    descripcion: Optional[str] = None

    @field_validator('monto')
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError("El monto del gasto debe ser mayor a 0")
        return v

# --- OUTPUT: RESPUESTA AL FRONTEND ---
class EgresoResponse(BaseModel):
    id_egreso: int
    monto: float
    fecha: date
    beneficiario: str
    num_comprobante: Optional[str]
    descripcion: Optional[str]
    estado: str
    
    # Nombres para mostrar en tablas sin hacer más peticiones
    nombre_cuenta: str = "Desconocido"  # Del Catalogo
    tipo_egreso: str = "Desconocido"    # Del TipoEgreso
    
    fecha_creacion: datetime

    class Config:
        from_attributes = True