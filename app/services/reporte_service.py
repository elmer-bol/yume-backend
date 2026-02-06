from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func
from fastapi import HTTPException
from datetime import datetime, date
from typing import List, Optional

from app.db import models
from app.schemas import reporte_schema

from app.db.models import TransaccionIngreso, Egreso, MedioIngreso

class ReporteService:
    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # 1. ESTADO DE CUENTA INDIVIDUAL (Tu código original intacto)
    # =========================================================================
    def obtener_estado_cuenta(self, id_persona: int) -> reporte_schema.EstadoCuentaResponse:
        persona = self.db.query(models.Persona).filter(models.Persona.id_persona == id_persona).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

        # A. Billeteras
        relaciones = self.db.query(models.RelacionCliente).filter(
            models.RelacionCliente.id_persona == id_persona,
            models.RelacionCliente.estado == 'Activo'
        ).all()

        lista_billeteras = []
        total_saldo_favor = 0.0

        for rel in relaciones:
            nombre_unidad = rel.unidad.identificador_unico if rel.unidad else f"Unidad {rel.id_unidad}"
            saldo = float(rel.saldo_favor)
            lista_billeteras.append({
                "unidad": nombre_unidad,
                "tipo_relacion": rel.tipo_relacion,
                "saldo": saldo
            })
            total_saldo_favor += saldo

        # B. Deudas
        items_pendientes = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.id_persona == id_persona,
            models.ItemFacturable.saldo_pendiente > 0.001,
            models.ItemFacturable.estado != 'cancelado',
            models.ItemFacturable.estado != 'anulado',      
            models.ItemFacturable.estado != 'pagado',      
            models.ItemFacturable.estado != 'congelado'     
        ).order_by(asc(models.ItemFacturable.fecha_vencimiento)).all()

        lista_deudas = []
        total_deuda_pendiente = 0.0
        total_deuda_vencida = 0.0
        hoy = date.today()

        for item in items_pendientes:
            saldo_item = float(item.saldo_pendiente)
            es_vencido = item.fecha_vencimiento < hoy

            # --- NUEVA LÓGICA PARA SACAR LA UNIDAD ---
            uid = item.id_unidad
            u_nombre = "General"
            if item.unidad:
                u_nombre = item.unidad.identificador_unico
            # -----------------------------------------

            lista_deudas.append(reporte_schema.ItemDeuda(
                periodo=item.periodo,
                concepto=item.concepto.nombre if item.concepto else "Concepto General",
                monto_base=float(item.monto_base),
                saldo_pendiente=saldo_item,
                fecha_vencimiento=item.fecha_vencimiento,
                estado="VENCIDO" if es_vencido else item.estado.upper(),
                
                # --- ASIGNAMOS LOS VALORES ---
                id_unidad=uid,
                nombre_unidad=u_nombre
                # -----------------------------
            ))

            total_deuda_pendiente += saldo_item
            if es_vencido:
                total_deuda_vencida += saldo_item

        # C. Pagos
        ultimos_pagos_db = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_usuario_creador == id_persona,
            models.TransaccionIngreso.estado != 'ANULADO'
        ).order_by(desc(models.TransaccionIngreso.fecha)).limit(10).all()
        
        lista_pagos = []
        for pago in ultimos_pagos_db:
            lista_pagos.append(reporte_schema.ItemPago(
                fecha=pago.fecha_creacion,
                monto_total=float(pago.monto_total),
                descripcion=pago.descripcion or "Pago de cuotas",
                num_documento=pago.num_documento,
                medio_pago=pago.medio_ingreso.nombre if pago.medio_ingreso else "Desconocido"
            ))

        # D. Estado General
        estado_general = "Al día"
        if total_deuda_vencida > 0:
            estado_general = "Moroso"
        elif total_saldo_favor > 0 and total_deuda_pendiente == 0:
            estado_general = "Solvente (Saldo a Favor)"
        elif total_deuda_pendiente > 0:
             estado_general = "Con Deuda Corriente"

        resumen_fin = reporte_schema.ResumenFinanciero(
            total_deuda_vencida=total_deuda_vencida,
            total_deuda_pendiente=total_deuda_pendiente,
            saldo_a_favor_disponible=total_saldo_favor,
            estado_general=estado_general
        )

        return reporte_schema.EstadoCuentaResponse(
            fecha_reporte=datetime.now(),
            id_persona=persona.id_persona,
            nombre_persona=f"{persona.nombres} {persona.apellidos}",
            resumen=resumen_fin,
            billeteras=lista_billeteras,
            deudas_pendientes=lista_deudas,
            ultimos_pagos=lista_pagos
        )

    # =========================================================================
    # 2. REPORTE DE MOROSIDAD (Resucitado y Ajustado)
    # =========================================================================
    def obtener_lista_morosos(self) -> List[reporte_schema.MorosoResponse]:
        hoy = date.today()
        
        # Buscamos ItemFacturable con saldo > 0 y fecha de vencimiento pasada
        deudas_vencidas = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.saldo_pendiente > 0.01,
            models.ItemFacturable.fecha_vencimiento < hoy,
            models.ItemFacturable.estado != 'anulado',
            models.ItemFacturable.estado != 'cancelado',
            models.ItemFacturable.estado != 'congelado'
        ).all()

        agrupado = {} 

        for item in deudas_vencidas:
            uid = item.id_unidad
            # Validación segura de unidad
            valor_identificador = item.unidad.identificador_unico if item.unidad else f"ID-{uid}"

            if uid not in agrupado:
                nombre_inquilino = "Desconocido"
                if item.persona:
                    nombre_inquilino = f"{item.persona.nombres} {item.persona.apellidos}"
                
                agrupado[uid] = reporte_schema.MorosoResponse(
                    id_unidad=uid,
                    identificador_unico=valor_identificador, 
                    nombre_inquilino=nombre_inquilino,
                    total_deuda=0.0,
                    cantidad_meses=0,
                    detalles=[]
                )
            
            dias_atraso = (hoy - item.fecha_vencimiento).days
            agrupado[uid].total_deuda += float(item.saldo_pendiente)
            agrupado[uid].cantidad_meses += 1
            
            # Obtenemos nombre del concepto de forma segura
            nombre_concepto = "General"
            if item.concepto:
                nombre_concepto = item.concepto.nombre
            
            agrupado[uid].detalles.append(reporte_schema.DetalleDeudaMoroso(
                periodo=item.periodo,
                concepto=nombre_concepto,
                monto_pendiente=float(item.saldo_pendiente),
                dias_atraso=dias_atraso
            ))
            
        # Retornamos la lista de valores del diccionario
        # return list(agrupado.values())
        
        # Convertimos el diccionario a lista
        lista_final = list(agrupado.values())

        # CAMBIO: Ordenar por id_unidad por defecto (puedes cambiar a total_deuda si prefieres)
        lista_final.sort(key=lambda x: x.id_unidad) 
        
        return lista_final
    
    # =========================================================================
    # 3. CARTERA GLOBAL (Resucitado y Ajustado)
    # =========================================================================
    def obtener_cartera_global(self) -> List[reporte_schema.CarteraGlobalResponse]:
        hoy = date.today()
        
        # Buscamos todo lo activo (Vencido + Futuro)
        items_activos = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.saldo_pendiente > 0.01,
            models.ItemFacturable.estado != 'anulado',
            models.ItemFacturable.estado != 'cancelado',
            models.ItemFacturable.estado != 'pagado',
            models.ItemFacturable.estado != 'congelado'
        ).all()

        agrupado = {}

        for item in items_activos:
            uid = item.id_unidad
            
            if uid not in agrupado:
                nombre_show = "Sin Inquilino"
                if item.persona:
                    nombre_show = f"{item.persona.nombres} {item.persona.apellidos}"
                
                identif = item.unidad.identificador_unico if item.unidad else f"ID-{uid}"
                
                agrupado[uid] = {
                    "id_unidad": uid,
                    "identificador_unico": identif,
                    "nombre_inquilino": nombre_show,
                    "deuda_vencida": 0.0,
                    "deuda_futura": 0.0,
                    "total_general": 0.0,
                    "cantidad_items": 0
                }
            
            saldo = float(item.saldo_pendiente)
            
            if item.fecha_vencimiento < hoy:
                agrupado[uid]["deuda_vencida"] += saldo
            else:
                agrupado[uid]["deuda_futura"] += saldo
            
            agrupado[uid]["total_general"] += saldo
            agrupado[uid]["cantidad_items"] += 1

        resultado = []
        for datos in agrupado.values():
            resultado.append(reporte_schema.CarteraGlobalResponse(**datos))
            
        # Ordenamos: Los que deben más dinero primero
        resultado.sort(key=lambda x: x.total_general, reverse=True)
        
        return resultado

    # =========================================================================
    # 4. DASHBOARD (Tu código original intacto)
    # =========================================================================
    def obtener_dashboard_general(self) -> reporte_schema.DashboardResponse:
        medios = self.db.query(models.MedioIngreso).filter(models.MedioIngreso.activo == True).all()
        lista_billeteras = []
        total_cash = 0.0
        
        for medio in medios:
            # Ingresos: Sumar montos de transacciones en este medio
            total_ing = self.db.query(func.sum(models.TransaccionIngreso.monto_total))\
                .filter(models.TransaccionIngreso.id_medio_ingreso == medio.id_medio_ingreso,
                        models.TransaccionIngreso.estado != 'ANULADO').scalar() or 0.0
            
            # Egresos: Sumar montos de egresos pagados con este medio
            total_egr = self.db.query(func.sum(models.Egreso.monto))\
                 .filter(models.Egreso.id_medio_pago == medio.id_medio_ingreso,
                         models.Egreso.estado != 'cancelado').scalar() or 0.0
            
            saldo = float(total_ing - total_egr)
            total_cash += saldo
            lista_billeteras.append(reporte_schema.SaldoBilletera(
                nombre=medio.nombre, monto=saldo, tipo=medio.tipo
            ))

        cartera = self.obtener_cartera_global()
        total_deuda = sum(c.total_general for c in cartera)
        
        morosos = self.obtener_lista_morosos()
        morosos.sort(key=lambda x: x.total_deuda, reverse=True)
        
        return reporte_schema.DashboardResponse(
            total_disponible=total_cash,
            total_por_cobrar=total_deuda,
            cantidad_morosos=len(morosos),
            billeteras=lista_billeteras,
            top_morosos=morosos[:5]
        )

    # =========================================================================
    # 5. ESTADO DE RESULTADOS (CRITERIO PERCIBIDO / CAJA) - CORREGIDO
    # =========================================================================
    def obtener_estado_resultados(self, fecha_inicio: date, fecha_fin: date) -> reporte_schema.EstadoResultadosResponse:
        """
        Genera el árbol contable basado en lo EFECTIVAMENTE COBRADO y calcula Saldo Inicial.
        """
        
        # --- 1. CALCULO DEL SALDO ANTERIOR (Lógica del Libro Caja) ---
        # Sumamos TODO lo que entró y salió antes de la fecha_inicio
        ingresos_previos = self.db.query(func.coalesce(func.sum(models.TransaccionIngreso.monto_total), 0)).filter(
            models.TransaccionIngreso.fecha < fecha_inicio,
            models.TransaccionIngreso.estado == 'APLICADO' # O 'registrado' segun tu logica
        ).scalar()

        egresos_previos = self.db.query(func.coalesce(func.sum(models.Egreso.monto), 0)).filter(
            models.Egreso.fecha < fecha_inicio,
            models.Egreso.estado != 'cancelado'
        ).scalar()

        saldo_anterior = float(ingresos_previos) - float(egresos_previos)

        # --- 2. OBTENER TOTALES DE INGRESOS DEL PERIODO (REALMENTE COBRADOS) ---
        ingresos_query = self.db.query(
            models.ConceptoDeuda.id_catalogo,
            func.sum(models.TransaccionIngresoDetalle.monto_aplicado)
        ).join(models.TransaccionIngreso, models.TransaccionIngresoDetalle.id_transaccion == models.TransaccionIngreso.id_transaccion)\
         .join(models.ItemFacturable, models.TransaccionIngresoDetalle.id_item == models.ItemFacturable.id_item)\
         .join(models.ConceptoDeuda, models.ItemFacturable.id_concepto == models.ConceptoDeuda.id_concepto)\
         .filter(models.ConceptoDeuda.id_catalogo != None)\
         .filter(models.TransaccionIngreso.fecha >= fecha_inicio,
                 models.TransaccionIngreso.fecha <= fecha_fin,
                 models.TransaccionIngreso.estado != 'ANULADO')\
         .group_by(models.ConceptoDeuda.id_catalogo).all()

        # --- 3. OBTENER EGRESOS DEL PERIODO ---
        egresos_query = self.db.query(
            models.Egreso.id_catalogo,
            func.sum(models.Egreso.monto)
        ).filter(models.Egreso.fecha >= fecha_inicio,
                 models.Egreso.fecha <= fecha_fin,
                 models.Egreso.estado != 'cancelado')\
         .group_by(models.Egreso.id_catalogo).all()

        # Convertir a Diccionarios {id_catalogo: monto}
        saldos_ingresos = {id_cat: float(monto or 0) for id_cat, monto in ingresos_query}
        saldos_egresos = {id_cat: float(monto or 0) for id_cat, monto in egresos_query}

        # --- 4. CONSTRUIR EL ÁRBOL ---
        categorias = self.db.query(models.Categoria)\
            .filter(models.Categoria.activo == True)\
            .order_by(models.Categoria.codigo).all()

        mapa_nodos = {}
        
        for cat in categorias:
            es_ingreso = str(cat.codigo).startswith('4') or cat.tipo == 'INGRESO'
            es_egreso = str(cat.codigo).startswith('5') or cat.tipo == 'EGRESO'

            monto_propio = 0.0
            if not cat.es_rubro:
                if es_ingreso:
                    monto_propio = saldos_ingresos.get(cat.id_catalogo, 0.0)
                elif es_egreso:
                    monto_propio = saldos_egresos.get(cat.id_catalogo, 0.0)

            nivel = len(str(cat.codigo).split('.'))

            nodo = reporte_schema.NodoReporte(
                id_catalogo=cat.id_catalogo,
                codigo=cat.codigo,
                nombre=cat.nombre_cuenta,
                es_rubro=cat.es_rubro,
                nivel=nivel,
                monto=monto_propio,
                hijos=[]
            )
            mapa_nodos[cat.codigo] = nodo

        # --- 5. ARMAR JERARQUÍA ---
        raices_ingresos = []
        raices_egresos = []
        codigos_ordenados = sorted(mapa_nodos.keys(), key=lambda x: len(str(x)), reverse=True)

        for codigo in codigos_ordenados:
            nodo_actual = mapa_nodos[codigo]
            partes = str(codigo).split('.')
            if len(partes) > 1:
                codigo_padre = ".".join(partes[:-1])
                if codigo_padre in mapa_nodos:
                    padre = mapa_nodos[codigo_padre]
                    padre.hijos.append(nodo_actual)
                    padre.monto += nodo_actual.monto
                else:
                    if str(codigo).startswith('4'): raices_ingresos.append(nodo_actual)
                    elif str(codigo).startswith('5'): raices_egresos.append(nodo_actual)
            else:
                if str(codigo).startswith('4'): raices_ingresos.append(nodo_actual)
                elif str(codigo).startswith('5'): raices_egresos.append(nodo_actual)

        # --- 6. ORDENAR ---
        def ordenar_hijos(nodos):
            nodos.sort(key=lambda x: x.codigo)
            for n in nodos:
                if n.hijos: ordenar_hijos(n.hijos)

        ordenar_hijos(raices_ingresos)
        ordenar_hijos(raices_egresos)

        # --- AQUÍ DEFINIMOS LAS VARIABLES QUE FALTABAN ---
        total_ing = sum(n.monto for n in raices_ingresos)
        total_egr = sum(n.monto for n in raices_egresos)

        # --- NODOS RAIZ FINALES ---
        root_ingreso_final = None
        if raices_ingresos:
            if len(raices_ingresos) == 1 and raices_ingresos[0].codigo == '4':
                root_ingreso_final = raices_ingresos[0]
            else:
                root_ingreso_final = reporte_schema.NodoReporte(
                    codigo="4", nombre="TOTAL INGRESOS", es_rubro=True, nivel=0, monto=total_ing, hijos=raices_ingresos
                )
        else:
             # Manejo de caso vacío para evitar errores en frontend
             root_ingreso_final = reporte_schema.NodoReporte(
                codigo="4", nombre="TOTAL INGRESOS", es_rubro=True, nivel=0, monto=0.0, hijos=[]
             )
        
        root_egreso_final = None
        if raices_egresos:
            if len(raices_egresos) == 1 and raices_egresos[0].codigo == '5':
                root_egreso_final = raices_egresos[0]
            else:
                root_egreso_final = reporte_schema.NodoReporte(
                    codigo="5", nombre="TOTAL EGRESOS", es_rubro=True, nivel=0, monto=total_egr, hijos=raices_egresos
                )
        else:
             root_egreso_final = reporte_schema.NodoReporte(
                codigo="5", nombre="TOTAL EGRESOS", es_rubro=True, nivel=0, monto=0.0, hijos=[]
             )

        resultado_neto_periodo = total_ing - total_egr

        return reporte_schema.EstadoResultadosResponse(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ingresos=root_ingreso_final,
            egresos=root_egreso_final,
            total_ingresos=total_ing,
            total_egresos=total_egr,
            resultado_neto=resultado_neto_periodo,
            
            # NUEVOS VALORES CALCULADOS
            saldo_anterior=saldo_anterior,
            saldo_final_acumulado=saldo_anterior + resultado_neto_periodo
        )

    # =========================================================================
    # 6. DETALLE DE MOVIMIENTOS (ACTUALIZADO A PAGOS REALES)
    # =========================================================================
    def obtener_detalle_cuenta(self, id_catalogo: int, fecha_inicio: date, fecha_fin: date) -> List[reporte_schema.DetalleMovimientoResponse]:
        """
        Muestra el detalle de PAGOS recibidos (Ingresos) o GASTOS realizados (Egresos).
        """
        cuenta = self.db.query(models.Categoria).filter(models.Categoria.id_catalogo == id_catalogo).first()
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")

        movimientos = []

        # CASO A: INGRESOS (Buscamos PAGOS, no DEUDAS)
        if str(cuenta.codigo).startswith('4') or cuenta.tipo == 'INGRESO':
            
            # Consultamos el Detalle del Pago unido a la Transacción
            q = self.db.query(
                    models.TransaccionIngresoDetalle, 
                    models.TransaccionIngreso,
                    models.ItemFacturable
                )\
                .join(models.TransaccionIngreso, models.TransaccionIngresoDetalle.id_transaccion == models.TransaccionIngreso.id_transaccion)\
                .join(models.ItemFacturable, models.TransaccionIngresoDetalle.id_item == models.ItemFacturable.id_item)\
                .join(models.ConceptoDeuda, models.ItemFacturable.id_concepto == models.ConceptoDeuda.id_concepto)\
                .filter(models.ConceptoDeuda.id_catalogo == id_catalogo)\
                .filter(models.TransaccionIngreso.fecha >= fecha_inicio,
                        models.TransaccionIngreso.fecha <= fecha_fin,
                        models.TransaccionIngreso.estado != 'ANULADO').all()

            for detalle, transaccion, item in q:
                # Usamos la relación existente en la transacción para sacar el nombre
                nombre_persona = "Desconocido"
                # Intentamos sacar el nombre desde la relación del cliente en la transacción
                if transaccion.relacion_cliente and transaccion.relacion_cliente.persona:
                    p = transaccion.relacion_cliente.persona
                    nombre_persona = f"{p.nombres} {p.apellidos}"
                
                movimientos.append(reporte_schema.DetalleMovimientoResponse(
                    fecha=transaccion.fecha, # Fecha del PAGO
                    descripcion=f"Pago: {item.periodo} ({transaccion.descripcion or 'Sin obs'})",
                    beneficiario_o_pagador=nombre_persona,
                    nro_documento=transaccion.num_documento, # Recibo de caja/banco
                    monto=float(detalle.monto_aplicado), # Solo lo que pagó
                    tipo='INGRESO'
                ))

        # CASO B: EGRESOS (Sigue igual)
        elif str(cuenta.codigo).startswith('5') or cuenta.tipo == 'EGRESO':
            q = self.db.query(models.Egreso)\
                .filter(models.Egreso.id_catalogo == id_catalogo)\
                .filter(models.Egreso.fecha >= fecha_inicio,
                        models.Egreso.fecha <= fecha_fin,
                        models.Egreso.estado != 'cancelado').all()

            for egreso in q:
                movimientos.append(reporte_schema.DetalleMovimientoResponse(
                    fecha=egreso.fecha,
                    descripcion=egreso.descripcion or "Sin descripción",
                    beneficiario_o_pagador=egreso.beneficiario,
                    nro_documento=egreso.num_comprobante,
                    monto=float(egreso.monto),
                    tipo='EGRESO'
                ))

        movimientos.sort(key=lambda x: x.fecha, reverse=True)
        return movimientos
    
    # =========================================================================
    # 7. GENERACION DE LIBRO DIARIO (VERSIÓN PULIDA CON REDONDEO)
    # =========================================================================
    def generar_kardex_caja(self, id_medio: int, fecha_inicio: str, fecha_fin: str):
        """
        Genera un reporte de movimientos (ingresos vs egresos) con saldo acumulado.
        """
        
        # 1. Obtener información de la Caja/Banco usando self.db
        medio = self.db.query(MedioIngreso).filter(MedioIngreso.id_medio_ingreso == id_medio).first()
        if not medio:
            raise HTTPException(status_code=404, detail="Medio de ingreso no encontrado")

        # 2. CALCULAR SALDO INICIAL
        ingresos_previos = self.db.query(func.coalesce(func.sum(TransaccionIngreso.monto_total), 0)).filter(
            TransaccionIngreso.id_medio_ingreso == id_medio,
            TransaccionIngreso.fecha < fecha_inicio,
            TransaccionIngreso.estado != 'anulado' 
        ).scalar()

        egresos_previos = self.db.query(func.coalesce(func.sum(Egreso.monto), 0)).filter(
            Egreso.id_medio_pago == id_medio, 
            Egreso.fecha < fecha_inicio,
            Egreso.estado != 'anulado'
        ).scalar()

        # REDONDEO AQUÍ
        saldo_inicial = round(float(ingresos_previos) - float(egresos_previos), 2)

        # 3. OBTENER MOVIMIENTOS DEL PERIODO
        lista_ingresos = self.db.query(TransaccionIngreso).filter(
            TransaccionIngreso.id_medio_ingreso == id_medio,
            TransaccionIngreso.fecha >= fecha_inicio,
            TransaccionIngreso.fecha <= fecha_fin,
            TransaccionIngreso.estado != 'anulado'
        ).all()

        lista_egresos = self.db.query(Egreso).filter(
            Egreso.id_medio_pago == id_medio,
            Egreso.fecha >= fecha_inicio,
            Egreso.fecha <= fecha_fin,
            Egreso.estado != 'anulado'
        ).all()

        # 4. UNIFICAR Y FORMATEAR
        movimientos = []

        for ing in lista_ingresos:
        # LÓGICA PARA SACAR EL DEPTO
            nombre_origen = "General"
            if ing.relacion_cliente and ing.relacion_cliente.unidad:
                nombre_origen = ing.relacion_cliente.unidad.identificador_unico
            elif ing.relacion_cliente and ing.relacion_cliente.persona:
                # Si no tiene unidad, ponemos el nombre de la persona
                nombre_origen = f"{ing.relacion_cliente.persona.nombres} {ing.relacion_cliente.persona.apellidos}"

            movimientos.append({
                "fecha": ing.fecha,
                "descripcion": ing.descripcion or "Ingreso registrado",
                "numero_doc": ing.num_documento,
                "ingreso": round(float(ing.monto_total), 2),
                "egreso": 0.00,
                "timestamp": ing.fecha_creacion,
                "origen": nombre_origen  # <--- AQUÍ LO AGREGAMOS
            })

        # ... (en la sección de Egresos)
        for egr in lista_egresos:
            desc = egr.descripcion or "Gasto registrado"
            # Para egresos, el origen/destino es el Beneficiario
            nombre_beneficiario = egr.beneficiario or "Sin Beneficiario"

            movimientos.append({
                "fecha": egr.fecha,
                "descripcion": desc,
                "numero_doc": egr.num_comprobante,
                "ingreso": 0.00,
                "egreso": round(float(egr.monto), 2),
                "timestamp": egr.fecha_creacion,
                "origen": nombre_beneficiario # <--- AQUÍ LO AGREGAMOS
            })

        # 5. ORDENAR CRONOLÓGICAMENTE
        movimientos.sort(key=lambda x: (x['fecha'], x['timestamp']))

        # 6. CALCULAR SALDO ACUMULADO
        saldo_actual = saldo_inicial
        movimientos_finales = []

        for mov in movimientos:
            # REDONDEO EN LA SUMA ACUMULADA
            saldo_actual = round(saldo_actual + mov['ingreso'] - mov['egreso'], 2)
            
            mov['saldo_acumulado'] = saldo_actual
            movimientos_finales.append(mov)

        return {
            "id_medio": medio.id_medio_ingreso,
            "nombre_medio": medio.nombre,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "saldo_inicial": saldo_inicial,
            "movimientos": movimientos_finales,
            "saldo_final": saldo_actual
        }