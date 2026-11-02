---
name: 4geeks-pendientes
description: Consulta todos los trabajos asignados en una cohorte 4Geeks y separa pendientes de completar, correcciones rechazadas y entregas en revisión. Incluye macrocohorte o curso con módulos vinculados.
---

# Qué trabajo 4Geeks me falta

1. Ejecuta desde la raíz del workspace `python3 skills/4geeks-pendientes/scripts/list_pending_work.py <slug> [macro|course]`. Si el usuario menciona solo el slug, el helper usa `course` e incluye exclusivamente módulos cuya `source_macro_cohort` apunte a esa macrocohorte. Usa `macro` si pide expresamente solo la macrocohorte.
2. El helper lee `FOURGEEKS_STUDENT_TOKEN` de forma privada a través de `skills/4geeks-conexion/scripts/check_connection.py`. No abras el archivo secreto ni muestres token, cabeceras, respuesta sin filtrar o datos personales.
3. El helper resuelve el slug exacto con `GET /v1/admissions/user/me`, envía los IDs de cohorte separados por comas a `GET /v1/assignment/user/me/task` sin filtro `task_type` y sigue todas las páginas. Solo informa resultado completo si la paginación y el alcance pueden verificarse. Informa errores HTTP tal cual, especialmente 401/403; nunca inventes éxito.
4. Conserva ambas dimensiones de estado. Clasifica `revision_status=REJECTED` como corrección requerida; `task_status=PENDING` como trabajo a completar; `task_status=DONE` sin rechazo como entregado y esperando revisión; `revision_status=APPROVED` como aprobado. Los demás estados/combinaciones quedan sin clasificar. No cuentes trabajo entregado en revisión como pendiente.
5. Resume cantidades totales y por tipo, lista el nombre seguro de cada trabajo, y da la próxima acción por categoría. Muestra fecha límite solo si el helper la encontró en un campo real de plazo; no infieras desde fechas de creación/actualización. Si la lista es incompleta, indícalo claramente y conserva el error.
6. Modos disponibles: `<slug> macro` solo macrocohorte; `<slug> course` macro más módulos asociados por `source_macro_cohort`, sin otros cursos. Esta skill lista trabajo pendiente/correcciones y no reemplaza `4geeks-proyectos`.

Solo GET. No cambia entregas, configuración, servicios o permisos. No publica ni muestra cuerpos de entrega, correos o URLs privadas.
