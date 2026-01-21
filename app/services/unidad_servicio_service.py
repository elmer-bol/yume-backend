# Archivo: app/services/unidad_servicio_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import models
from app.schemas import unidad_servicio_schema as schemas

class UnidadServicioService:
    def __init__(self, db: Session):
        self.db = db

    def get_unidad_by_id(self, unidad_id: int) -> Optional[models.UnidadServicio]:
        return self.db.query(models.UnidadServicio).filter(models.UnidadServicio.id_unidad == unidad_id).first()

    def get_all_unidades(self, skip: int = 0, limit: int = 100) -> List[models.UnidadServicio]:
        return self.db.query(models.UnidadServicio).offset(skip).limit(limit).all()

    def search_unidades(self, filters: schemas.UnidadServicioFilter, skip: int = 0, limit: int = 100) -> List[models.UnidadServicio]:
        query = self.db.query(models.UnidadServicio)

        # Aplicamos los filtros dinámicamente
        if filters.identificador_unico:
            query = query.filter(models.UnidadServicio.identificador_unico.ilike(f"%{filters.identificador_unico}%"))
        
        if filters.tipo_unidad:
            query = query.filter(models.UnidadServicio.tipo_unidad == filters.tipo_unidad)
            
        if filters.estado:
            query = query.filter(models.UnidadServicio.estado == filters.estado)
            
        if filters.activo is not None:
            query = query.filter(models.UnidadServicio.activo == filters.activo)

        return query.offset(skip).limit(limit).all()

    def create_unidad(self, unidad_in: schemas.UnidadServicioCreate) -> Optional[models.UnidadServicio]:
        # 1. Validar unicidad del identificador
        existe = self.db.query(models.UnidadServicio).filter(
            models.UnidadServicio.identificador_unico == unidad_in.identificador_unico
        ).first()

        if existe:
            return None # El endpoint lanzará el 409 Conflict

        # 2. Crear
        db_unidad = models.UnidadServicio(
            identificador_unico=unidad_in.identificador_unico,
            tipo_unidad=unidad_in.tipo_unidad,
            estado=unidad_in.estado,
            activo=True
        )
        self.db.add(db_unidad)
        self.db.commit()
        self.db.refresh(db_unidad)
        return db_unidad

    def update_unidad(self, unidad_id: int, unidad_in: schemas.UnidadServicioUpdate) -> Optional[models.UnidadServicio]:
        db_unidad = self.get_unidad_by_id(unidad_id)
        if not db_unidad:
            return None

        # Si cambia el identificador, verificar que no choque con otro
        if unidad_in.identificador_unico and unidad_in.identificador_unico != db_unidad.identificador_unico:
            existe = self.db.query(models.UnidadServicio).filter(
                models.UnidadServicio.identificador_unico == unidad_in.identificador_unico
            ).first()
            if existe:
                # Retornamos None para simplificar, idealmente lanzaríamos excepción
                return None 

        update_data = unidad_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_unidad, field, value)

        self.db.commit()
        self.db.refresh(db_unidad)
        return db_unidad

    def soft_delete_unidad(self, unidad_id: int) -> Optional[models.UnidadServicio]:
        db_unidad = self.get_unidad_by_id(unidad_id)
        if not db_unidad:
            return None
        
        db_unidad.activo = False
        self.db.commit()
        self.db.refresh(db_unidad)
        return db_unidad