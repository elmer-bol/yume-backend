# Archivo: app/schemas/unidad_servicio_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime # Importar para campos de auditoría

# 1. Esquema Base (para crear o actualizar)
class UnidadServicioBase(BaseModel):
    identificador_unico: str = Field(..., max_length=50, description="Ej: A-101 o Aula 5A. Debe ser único.")
    
    # CRÍTICO: El modelo SQLAlchemy permite que estos sean nulos/opcionales.
    tipo_unidad: Optional[str] = Field(None, max_length=50, description="Ej: Departamento, Aula Escolar, Contrato")
    estado: Optional[str] = Field('Vacío', max_length=20, description="Ej: Ocupado, Vacío, Activo, Mantenimiento")
    
    activo: bool = Field(True, description="Estado de actividad de la unidad. Usado para baja lógica.")


# 2. Esquema de Creación (Hereda del Base)
class UnidadServicioCreate(UnidadServicioBase):
    pass

# 3. Esquema de Actualización (PUT/PATCH)
class UnidadServicioUpdate(BaseModel):
    """
    Esquema para actualizar la Unidad de Servicio. Todos los campos son opcionales.
    """
    identificador_unico: Optional[str] = Field(None, max_length=50, description="Nuevo identificador único.")
    tipo_unidad: Optional[str] = Field(None, max_length=50)
    estado: Optional[str] = Field(None, max_length=20)
    activo: Optional[bool] = None # Permite la baja/alta lógica (Soft Delete)

# 4. Esquema de Filtro para Búsqueda (GET con Query Params)
class UnidadServicioFilter(BaseModel):
    """
    Esquema para buscar y filtrar la lista de unidades. 
    Se utilizará como dependencia en el endpoint GET.
    """
    identificador_unico: Optional[str] = Field(None, description="Buscar por identificador único exacto.")
    tipo_unidad: Optional[str] = Field(None, description="Filtrar por tipo de unidad (parcial).")
    estado: Optional[str] = Field(None, description="Filtrar por estado (Ej: Ocupado).")
    activo: Optional[bool] = Field(True, description="Filtrar por estado activo (por defecto, True).")
    def is_empty(self) -> bool:
        """
        Verifica si se aplicó algún filtro de negocio explícito. 
        Utiliza exclude_defaults=True para ignorar campos con valores predeterminados 
        cuando no se envían como parámetros de consulta.
        """
        # Si el diccionario de campos (excluyendo los que tienen su valor por defecto) está vacío, 
        # significa que el usuario no aplicó filtros.
        provided_fields = self.model_dump(exclude_defaults=True)
        return not bool(provided_fields)

# 5. Esquema de Lectura (Para retornar los datos)
class UnidadServicio(UnidadServicioBase):
    id_unidad: int  # Incluye el ID, que la BD asigna automáticamente
    fecha_creacion: datetime # Incluye el campo de auditoría

    class Config:
        from_attributes = True