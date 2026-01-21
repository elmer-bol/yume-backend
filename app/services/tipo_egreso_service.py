# Archivo: app/services/tipo_egreso_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.db import models
from app.schemas import tipo_egreso_schema as schemas

class TipoEgresoService:
    def __init__(self, db: Session):
        self.db = db

    def _get_by_id_or_error(self, id: int) -> models.TipoEgreso:
        """Helper privado para buscar o lanzar error 404"""
        item = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.id_tipo_egreso == id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Tipo de Egreso no encontrado")
        return item

    def get_by_id(self, tipo_egreso_id: int) -> models.TipoEgreso:
        return self._get_by_id_or_error(tipo_egreso_id)

    def get_all(self, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[models.TipoEgreso]:
        query = self.db.query(models.TipoEgreso)
        if not include_inactive:
            query = query.filter(models.TipoEgreso.activo == True)
        return query.offset(skip).limit(limit).all()

    def create(self, tipo_in: schemas.TipoEgresoCreate) -> models.TipoEgreso:
        # Validar duplicados
        existe = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.nombre == tipo_in.nombre).first()
        if existe:
            raise HTTPException(status_code=409, detail=f"El tipo '{tipo_in.nombre}' ya existe.")

        nuevo = models.TipoEgreso(
            nombre=tipo_in.nombre,
            descripcion=tipo_in.descripcion,
            activo=True
        )
        self.db.add(nuevo)
        self.db.commit()
        self.db.refresh(nuevo)
        return nuevo

    def update(self, tipo_egreso_id: int, tipo_in: schemas.TipoEgresoUpdate) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(tipo_egreso_id)

        # Si cambia el nombre, validar que no choque con otro
        if tipo_in.nombre and tipo_in.nombre != db_obj.nombre:
            existe = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.nombre == tipo_in.nombre).first()
            if existe:
                raise HTTPException(status_code=409, detail=f"El nombre '{tipo_in.nombre}' ya está en uso.")

        update_data = tipo_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def soft_delete(self, tipo_egreso_id: int) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(tipo_egreso_id)
        if not db_obj.activo:
             raise HTTPException(status_code=400, detail="El ítem ya está inactivo.")
        
        db_obj.activo = False
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def activate(self, tipo_egreso_id: int) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(tipo_egreso_id)
        if db_obj.activo:
             raise HTTPException(status_code=400, detail="El ítem ya está activo.")
        
        db_obj.activo = True
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj