---
name: 4geeks-proyectos
description: Lista los proyectos asignados a Roger en un cohorte 4Geeks y su estado real. Úsala ante preguntas por proyectos/tareas de tipo proyecto en un cohorte concreto; paginación completa, solo GET.
---

# Consulta mis proyectos 4Geeks

1. Desde la raíz del workspace, ejecuta `python3 skills/4geeks-proyectos/scripts/list_projects.py <cohort-slug>`, pasando el slug solicitado (p. ej. `spain-aie-pt-5`). El helper reutiliza el lector seguro del token de `4geeks-conexion`; no leas el archivo privado ni imprimas entorno, cabeceras o token.
2. El helper resuelve primero el slug exacto mediante `GET /v1/admissions/academy/cohort/me`; si ese endpoint devuelve 401/403, usa el campo `cohorts` de `GET /v1/admissions/user/me` y conserva el HTTP inicial en el resultado. Después consulta `GET /v1/assignment/user/me/task` con `task_type=PROJECT`, el ID de cohorte resuelto y paginación por `limit`/`offset`. No sustituye el ID por un slug ni consulta detalles individuales.
3. Presenta el resultado solo como completo cuando el helper confirme el slug exacto, el filtro `cohort=<id>` aplicado en cada página y la paginación terminada sin repetir páginas. Si los registros incluyen cohorte, exige además que coincida. Si alguna prueba del filtro o exhaustividad falla, dilo y marca la lista incompleta.
4. Conserva `task_status` y `revision_status`. La revisión `APPROVED` significa aprobado; `REJECTED`, requiere correcciones. Con revisión vacía o `PENDING`, `task_status=PENDING` significa pendiente y `DONE`, entregado esperando revisión. Las demás combinaciones quedan sin clasificar; muestra ambos valores originales. Nunca infieras aprobación desde `DONE`.
5. Responde en español con todos los proyectos, sus estados, totales por estado, filtro y si la lista es completa. No muestres ni guardes emails, URLs de entrega, cuerpos completos o información ajena. Ante 401/403 informa que la autenticación fue rechazada; en otros errores indica el HTTP/causa comprobable sin declarar éxito.

El helper hace solo GET y no reintenta llamadas fallidas. No cambia tareas, entregas, configuración ni conexiones.
