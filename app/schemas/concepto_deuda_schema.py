# Archivo: app/schemas/concepto_deuda_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- INPUT: CREAR ---
class ConceptoDeudaCreate(BaseModel):
    nombre: str = Field(..., min_length=3, description="Nombre del cobro (Ej: Expensas Marzo)")
    descripcion: Optional[str] = None
    
    # ### NUEVO ###: Enlace Contable OBLIGATORIO (Cuenta 4.x.x)
    id_catalogo: int = Field(..., description="ID de la Cuenta Contable de Ingreso")

# --- INPUT: ACTUALIZAR ---
class ConceptoDeudaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_catalogo: Optional[int] = None
    activo: Optional[bool] = None

# --- OUTPUT: RESPUESTA AL FRONTEND ---
class ConceptoDeudaResponse(BaseModel):
    id_concepto: int
    nombre: str
    descripcion: Optional[str]
    activo: bool
    fecha_creacion: Optional[datetime] = None
    
    # ### NUEVO ###: Datos Contables para mostrar en pantalla
    id_catalogo: Optional[int] = None
    nombre_cuenta: Optional[str] = "Sin Asignar" 

    class Config:
        from_attributes = True