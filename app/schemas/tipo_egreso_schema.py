# Contenido en app/schemas/tipo_egreso_schema.py
from typing import Optional
from pydantic import BaseModel, Field

class TipoEgresoBase(BaseModel):
    """Esquema base que contiene los campos comunes para creación y actualización."""
    nombre: str = Field(..., max_length=50, description="Ej: Cheque, Efectivo/Caja, Transferencia.")
    requiere_num_doc: bool = Field(False, description="Indica si el método requiere un número de comprobante/cheque.")

class TipoEgresoCreate(TipoEgresoBase):
    """Esquema para la creación de un nuevo TipoEgreso."""
    # En la creación no se incluye 'activo', ya que por defecto es True
    pass

class TipoEgresoUpdate(BaseModel):
    """Esquema para la actualización parcial de un TipoEgreso. Todos los campos son opcionales."""
    nombre: Optional[str] = Field(None, max_length=50, description="Ej: Cheque, Efectivo/Caja, Transferencia.")
    requiere_num_doc: Optional[bool] = Field(None, description="Indica si el método requiere un número de comprobante/cheque.")
    activo: Optional[bool] = Field(None, description="Estado de activación/desactivación lógica.")
    
    class Config:
        # Permite actualizar solo los campos que se envían (excluye los no establecidos)
        extra = "forbid"

class TipoEgreso(TipoEgresoBase):
    """Esquema para la lectura (respuesta) de un TipoEgreso, incluyendo el ID y el estado activo."""
    id_tipo_egreso: int
    activo: bool # Incluimos el campo activo para la respuesta

    class Config:
        # Habilita la lectura desde el objeto ORM (SQLAlchemy)
        from_attributes = True