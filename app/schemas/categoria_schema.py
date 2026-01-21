# Archivo: app/schemas/categoria_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Clase para estandarizar los tipos de categoría y evitar errores de tipeo.
class TipoCategoriaEnum:
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"

# 1. Esquema Base
class CategoriaBase(BaseModel):
    # Longitud ajustada a 50 para coincidir con el ORM.
    nombre_cuenta: str = Field(..., max_length=50, description="Nombre descriptivo de la cuenta contable.")
    
    # Tipo estandarizado, con max_length=10 para coincidir con el ORM.
    tipo: str = Field(..., max_length=10, description=f"Tipo de categoría: '{TipoCategoriaEnum.INGRESO}' o '{TipoCategoriaEnum.EGRESO}'.")
    activo: bool = Field(True, description="Indica si la categoría está disponible para ser usada.")


# 2. Esquema de Creación
class CategoriaCreate(CategoriaBase):
    pass

# 3. Esquema de Lectura (Para retornar los datos)
class Categoria(CategoriaBase):
    id_catalogo: int = Field(..., description="Identificador único de la categoría.")
    
    class Config:
        from_attributes = True

# 4. Esquema de Actualización (PATCH)
class CategoriaUpdate(BaseModel):
    # Todos los campos son opcionales
    nombre_cuenta: Optional[str] = Field(None, max_length=50)
    tipo: Optional[str] = Field(None, max_length=10, description=f"Debe ser '{TipoCategoriaEnum.INGRESO}' o '{TipoCategoriaEnum.EGRESO}'.")
    activo: Optional[bool] = None

# 5. Esquema de Filtro para Búsqueda (GET con Query Params)
class CategoriaFilter(BaseModel):
    """Esquema utilizado para filtrar las categorías en las consultas GET."""
    nombre_cuenta: Optional[str] = Field(None, description="Buscar por nombre de cuenta (búsqueda parcial).")
    tipo: Optional[str] = Field(None, description=f"Filtrar por tipo ('{TipoCategoriaEnum.INGRESO}' o '{TipoCategoriaEnum.EGRESO}').")
    activo: Optional[bool] = Field(None, description="Filtrar por estado activo.")