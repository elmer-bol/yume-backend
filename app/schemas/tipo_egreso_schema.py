from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# --- SUB-SCHEMA (Para mostrar info del Rubro vinculado) ---
class RubroInfo(BaseModel):
    id_catalogo: int
    codigo: str
    nombre_cuenta: str

# --- BASE ---
class TipoEgresoBase(BaseModel):
    """Campos comunes para validación."""
    nombre: str = Field(..., min_length=3, max_length=50, description="Nombre del grupo visual.")
    requiere_num_doc: bool = Field(False, description="¿Exige comprobante?")
    
    # ### NUEVO: Campo para vincular al Catálogo ###
    id_catalogo: Optional[int] = Field(None, description="ID del Rubro Contable Padre (Ej: Servicios Básicos)")

# --- CREATE ---
class TipoEgresoCreate(TipoEgresoBase):
    pass

# --- UPDATE ---
class TipoEgresoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    requiere_num_doc: Optional[bool] = None
    activo: Optional[bool] = None
    
    # ### NUEVO ###
    id_catalogo: Optional[int] = None
    
    model_config = ConfigDict(extra="forbid")

# --- RESPONSE ---
class TipoEgresoResponse(TipoEgresoBase):
    id_tipo_egreso: int
    activo: bool 

    # ### NUEVO: Información del Rubro vinculado ###
    # Al usar ORM mode, Pydantic leerá la relación 'rubro_contable' del modelo
    rubro_contable: Optional[RubroInfo] = None

    model_config = ConfigDict(from_attributes=True)