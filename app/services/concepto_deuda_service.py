# Archivo: app/services/concepto_deuda_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.db import models
from app.schemas import concepto_deuda_schema as schemas

class ConceptoDeudaService:
    def __init__(self, db: Session):
        self.db = db

    def get_concepto_by_id(self, concepto_id: int) -> Optional[models.ConceptoDeuda]:
        return self.db.query(models.ConceptoDeuda).filter(models.ConceptoDeuda.id_concepto == concepto_id).first()

    def get_all_conceptos(self, skip: int = 0, limit: int = 100) -> List[models.ConceptoDeuda]:
        return self.db.query(models.ConceptoDeuda).offset(skip).limit(limit).all()

    def create_concepto(self, concepto_in: schemas.ConceptoDeudaCreate) -> models.ConceptoDeuda:
        existe = self.db.query(models.ConceptoDeuda).filter(
            models.ConceptoDeuda.nombre == concepto_in.nombre
        ).first()
        
        if existe:
            raise HTTPException(status_code=409, detail=f"El concepto '{concepto_in.nombre}' ya existe.")

        nuevo_concepto = models.ConceptoDeuda(
            nombre=concepto_in.nombre,
            descripcion=concepto_in.descripcion,
            
            activo=True
        )
        
        self.db.add(nuevo_concepto)
        self.db.commit()
        self.db.refresh(nuevo_concepto)
        return nuevo_concepto

    # --- NUEVO: ACTUALIZAR ---
    def update_concepto(self, concepto_id: int, concepto_in: schemas.ConceptoDeudaUpdate) -> models.ConceptoDeuda:
        db_concepto = self.get_concepto_by_id(concepto_id)
        if not db_concepto:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")

        # Si cambia el nombre, validar duplicados
        if concepto_in.nombre and concepto_in.nombre != db_concepto.nombre:
            existe = self.db.query(models.ConceptoDeuda).filter(models.ConceptoDeuda.nombre == concepto_in.nombre).first()
            if existe:
                raise HTTPException(status_code=409, detail=f"El nombre '{concepto_in.nombre}' ya está en uso.")

        # Actualizar campos
        update_data = concepto_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_concepto, field, value)

        self.db.commit()
        self.db.refresh(db_concepto)
        return db_concepto

    # --- SOFT DELETE (DESACTIVAR) ---
    def delete_concepto(self, concepto_id: int) -> models.ConceptoDeuda:
        """
        Desactiva el concepto para que no se use en nuevas deudas.
        NO validamos uso histórico, porque justamente queremos archivar
        conceptos viejos que ya fueron usados (ej: 'Expensas 2023').
        """
        db_concepto = self.get_concepto_by_id(concepto_id)
        if not db_concepto:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")

        # (Opcional) Si ya está desactivado, avisamos
        if not db_concepto.activo:
             raise HTTPException(status_code=400, detail="El concepto ya se encuentra inactivo.")

        # Simplemente apagamos el switch
        db_concepto.activo = False
        
        self.db.commit()
        self.db.refresh(db_concepto)
        return db_concepto