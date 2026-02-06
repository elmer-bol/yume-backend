# Archivo: app/services/concepto_deuda_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.db import models
from app.schemas import concepto_deuda_schema as schemas

class ConceptoDeudaService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # VALIDACIÓN PRIVADA (Helper)
    # -------------------------------------------------------------------------
    def _validar_cuenta_ingreso(self, id_catalogo: int):
        """Verifica que la cuenta exista y sea de tipo INGRESO (Grupo 4)"""
        cuenta = self.db.query(models.Categoria).filter(
            models.Categoria.id_catalogo == id_catalogo
        ).first()

        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
        
        # Validamos que sea Ingreso (por tipo o por código que empiece con 4)
        if cuenta.tipo != 'INGRESO' and not str(cuenta.codigo).startswith('4'):
            raise HTTPException(
                status_code=400, 
                detail=f"La cuenta '{cuenta.nombre_cuenta}' NO es de Ingreso. Solo puedes asociar cuentas del grupo 4."
            )

    # -------------------------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # -------------------------------------------------------------------------

    def get_concepto_by_id(self, concepto_id: int) -> Optional[models.ConceptoDeuda]:
        return self.db.query(models.ConceptoDeuda).filter(models.ConceptoDeuda.id_concepto == concepto_id).first()

    def get_all_conceptos(self, skip: int = 0, limit: int = 100):
        # Usamos join implícito (lazy load) para traer la cuenta contable
        conceptos = self.db.query(models.ConceptoDeuda).offset(skip).limit(limit).all()
        
        # Mapeamos la respuesta para incluir el nombre de la cuenta manualmente
        # (Aunque Pydantic lo haría si la relación está cargada, esto asegura que no falle)
        resultados = []
        for c in conceptos:
            resp = schemas.ConceptoDeudaResponse.model_validate(c)
            if c.cuenta_contable:
                resp.nombre_cuenta = c.cuenta_contable.nombre_cuenta
            resultados.append(resp)
        return resultados

    def create_concepto(self, concepto_in: schemas.ConceptoDeudaCreate) -> models.ConceptoDeuda:
        # 1. Validar nombre único
        existe = self.db.query(models.ConceptoDeuda).filter(
            models.ConceptoDeuda.nombre == concepto_in.nombre
        ).first()
        if existe:
            raise HTTPException(status_code=409, detail=f"El concepto '{concepto_in.nombre}' ya existe.")

        # 2. Validar cuenta contable (NUEVO)
        self._validar_cuenta_ingreso(concepto_in.id_catalogo)

        # 3. Crear registro
        nuevo_concepto = models.ConceptoDeuda(
            nombre=concepto_in.nombre,
            descripcion=concepto_in.descripcion,
            id_catalogo=concepto_in.id_catalogo, # Guardamos el enlace
            activo=True
        )
        
        self.db.add(nuevo_concepto)
        self.db.commit()
        self.db.refresh(nuevo_concepto)
        return nuevo_concepto

    def update_concepto(self, concepto_id: int, concepto_in: schemas.ConceptoDeudaUpdate) -> models.ConceptoDeuda:
        db_concepto = self.get_concepto_by_id(concepto_id)
        if not db_concepto:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")

        # Si cambia el nombre, validar duplicados
        if concepto_in.nombre and concepto_in.nombre != db_concepto.nombre:
            existe = self.db.query(models.ConceptoDeuda).filter(models.ConceptoDeuda.nombre == concepto_in.nombre).first()
            if existe:
                raise HTTPException(status_code=409, detail=f"El nombre '{concepto_in.nombre}' ya está en uso.")

        # Si cambia la cuenta contable, validar que sea Ingreso (NUEVO)
        if concepto_in.id_catalogo:
            self._validar_cuenta_ingreso(concepto_in.id_catalogo)

        # Actualizar campos dinámicamente
        update_data = concepto_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_concepto, field, value)

        self.db.commit()
        self.db.refresh(db_concepto)
        return db_concepto

    def delete_concepto(self, concepto_id: int) -> models.ConceptoDeuda:
        db_concepto = self.get_concepto_by_id(concepto_id)
        if not db_concepto:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")

        if not db_concepto.activo:
             raise HTTPException(status_code=400, detail="El concepto ya se encuentra inactivo.")

        db_concepto.activo = False
        self.db.commit()
        self.db.refresh(db_concepto)
        return db_concepto