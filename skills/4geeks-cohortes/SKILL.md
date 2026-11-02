---
name: 4geeks-cohortes
description: Consulta las cohortes en las que Roger está inscrito y el estado real de cada inscripción. Úsala ante preguntas sobre cohortes/inscripciones propias; enumera todas, no supone cuál está activa y separa educational_status de cohort.stage.
---

# Consulta mis cohortes 4Geeks

1. Desde la raíz del workspace, ejecuta `python3 skills/4geeks-cohortes/scripts/list_cohorts.py`. No leas el archivo de credenciales ni imprimas entorno, cabeceras o token. El helper reutiliza `load_token()` de `4geeks-conexion`.
2. El helper intenta `GET /v1/admissions/academy/cohort/me` y, ante HTTP 401/403, consulta únicamente `GET /v1/admissions/user/me`, usando solo `cohorts`. No eleva permisos ni llama endpoints globales/docentes. Informa el código inicial y la ruta de estudiante efectivamente utilizada.
3. Presenta una línea por inscripción, con nombre/slug y `educational_status` literal. Si aparece `cohort.stage`, preséntalo como etapa del cohorte en campo separado; nunca lo uses como estado de inscripción ni para decidir cuál está activa. Mantén entradas repetidas si la API las devuelve y di cuántas inscripciones hay; no elijas la primera como activa.
4. Responde en español. Omite cualquier otro campo, especialmente identificadores de estudiante, emails, estados financieros o datos personales. Valores de estado ausentes o desconocidos se declaran como tales, sin inferencia.
5. Solo declara consulta completada cuando el helper confirme HTTP 200, forma utilizable de `cohorts` y conteo verificado. Ante errores, informa el estado real y no inventes resultado.

El helper hace solo GET a las dos rutas indicadas, sin reintentos ni escrituras.
