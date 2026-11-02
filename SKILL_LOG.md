# Mi Asistente 4Geeks: registro de skills

He enseñado a Atlas, mi agente de OpenClaw, a consultar mi cuenta de 4Geeks mediante seis skills. Este registro recoge las peticiones, las decisiones y las pruebas con la API, el servicio que permite consultar los datos de la plataforma.

Todas las pruebas son del 2 de noviembre de 2026. Las horas usan Europe/Madrid. HTTP 200 indica que la consulta respondió correctamente; HTTP 403, que la ruta denegó el acceso.

## Cómo empezamos

Mi primera petición fue: «Quiero darte la habilidad de conectarte a mi cuenta de 4Geeks usando mi token de estudiante, sin que tenga que desarrollar código de mi parte. ¿Qué debemos hacer?».

Atlas propuso comprobar primero la conexión. Me pidió guardar el token de forma privada y confirmar la dirección de la API. La credencial quedó fuera del repositorio, en la configuración de OpenClaw con permisos `600`, que restringen el acceso al propietario.

Después fuimos añadiendo las cuatro capacidades principales y dos necesidades adicionales: consultar mis cohortes y entender el feedback de una tarea.

## 1. Comprobar la conexión

**Lo que pedí:** «Cuando te pregunte si mi conexión de 4Geeks funciona, comprueba que el token siga válido y responde sin revelar credenciales».

**Qué decidimos:** crear `4geeks-conexion`. Hace una sola consulta al usuario actual y devuelve el estado de la conexión, sin mostrar la información personal recibida.

**API:** `GET /v1/admissions/user/me`.

**Prueba real, 20:17:** HTTP 200, sesión válida e identidad comprobada. El resultado público contiene solo el estado HTTP y dos comprobaciones de sí/no.

## 2. Consultar mis proyectos

**Lo que pedí:** «¿Qué proyectos tengo asignados en spain-aie-pt-5 y en qué estado está cada uno?».

**Qué decidimos:** crear `4geeks-proyectos`. Resuelve la cohorte exacta y consulta solo proyectos. Comprueba la paginación y la pertenencia a la cohorte antes de presentar una lista completa.

**API:** `GET /v1/admissions/user/me` para resolver la cohorte y `GET /v1/assignment/user/me/task` con los filtros `task_type=PROJECT` y `cohort`.

**Prueba real, 20:33:** HTTP 200 y 7 proyectos pendientes de la cohorte principal (ID 1839). La consulta comprobó que no quedaban páginas por recuperar.

Para resolver la cohorte, Atlas usó las inscripciones del usuario actual. El apartado 5 explica por qué sustituyó la ruta sugerida por el ejercicio.

## 3. Saber qué me falta

**Lo que pedí:** «Quiero saber exactamente qué me falta completar en mi cohorte, incluyendo tareas rechazadas que requieren corregir».

**Qué decidimos:** crear `4geeks-pendientes`. Incluye todos los tipos de trabajo y separa lo que falta completar, lo que necesita correcciones y lo que ya espera revisión. Puede consultar solo la cohorte principal o añadir sus módulos vinculados.

**API:** `GET /v1/admissions/user/me` y `GET /v1/assignment/user/me/task`, filtrando los IDs de las cohortes incluidas.

**Prueba real, 20:41:** HTTP 200 y 90 registros del curso completo: la cohorte principal y sus 7 módulos vinculados.

| Estado | Cantidad |
| --- | ---: |
| Por completar | 43 |
| Requieren correcciones | 0 |
| Esperan revisión | 3 |
| Aprobados | 44 |
| Total | 90 |

Los 43 pendientes son 7 proyectos, 23 ejercicios y 13 lecciones. La API no devolvió fechas límite utilizables; el asistente lo indica sin inventarlas.

Por separado, la cohorte principal devolvió 54 registros: 39 pendientes y 15 aprobados. La diferencia corresponde a los módulos incluidos en el curso completo.

## 4. Resumir mi progreso

**Lo que pedí:** «¿Qué tan avanzado estoy en mi curso? Quiero un resumen claro con numerador, denominador y fórmula explícita».

**Qué decidimos:** crear `4geeks-progreso`. Agrega los estados de las tareas y distingue el trabajo completado por mí del aprobado en revisión.

**API:** `GET /v1/admissions/user/me` y `GET /v1/assignment/user/me/task`, filtrando las cohortes del curso elegido.

**Prueba real, 20:51:** HTTP 200 y 90 registros del curso: 15 proyectos, 60 ejercicios y 15 lecciones.

| Medida | Cálculo | Resultado |
| --- | --- | ---: |
| Completado por mí | 100 × 47 / 90 | 52,2 % |
| Aprobado en revisión | 100 × 44 / 90 | 48,9 % |

El primer cálculo usa `task_status=DONE`; el segundo, `revision_status=APPROVED`. Ambos usan como denominador todos los registros del alcance. Son porcentajes calculados desde las tareas, no una métrica oficial de 4Geeks.

El cálculo cuenta cada registro de asignación una vez, aunque un título aparezca en la cohorte principal y en un módulo. Las sumas por tipo coinciden con los totales.

## 5. Consultar mis cohortes

**Lo que pedí:** «Necesito saber en qué cohortes estoy inscrito y cuál es el estado de cada inscripción. No supongas que la primera es la activa».

**Qué decidimos:** crear `4geeks-cohortes`. Lista mis inscripciones y mantiene separados `educational_status` (estado de mi inscripción) y `stage` (etapa de la cohorte).

**API:** intenta `GET /v1/admissions/academy/cohort/me`. En mi cuenta devuelve HTTP 403, así que utiliza las inscripciones propias de `GET /v1/admissions/user/me`, que devuelve HTTP 200. No se amplían permisos.

**Prueba real, 20:59:** recuperó 32 inscripciones y confirmó que hay varias activas.

| Estado de inscripción | Cantidad |
| --- | ---: |
| `ACTIVE` | 26 |
| `GRADUATED` | 5 |
| `NOT_COMPLETING` | 1 |

Por ejemplo, `spain-aie-pt-5` tiene inscripción `ACTIVE` y etapa `STARTED`. Son dos campos distintos y la skill conserva ambos valores.

## 6. Consultar detalle y feedback

**Lo que pedí:** «Mi segunda necesidad adicional es entender el detalle y feedback de una tarea para saber cómo mejorarla. Si el feedback está vacío, dilo».

**Qué decidimos:** crear `4geeks-feedback`. Comprueba que la tarea pertenece a mi cuenta y cohorte, consulta su detalle y devuelve el comentario recibido con su campo de origen.

**API:** `GET /v1/assignment/user/me/task`, filtrando la cohorte, y `GET /v1/assignment/user/me/task/{task_id}`. La ruta personal de detalle filtra por el usuario autenticado; es la alternativa comprobada a la ruta genérica del mapa del ejercicio.

**Primera prueba, 21:08:** la tarea pendiente `1004503` permitió comprobar el acceso al detalle, pero no la recuperación de feedback con contenido. Esa prueba quedó incompleta para demostrar esta capacidad.

**Corrección:** busqué entre mis 193 asignaciones, recuperadas en dos páginas con HTTP 200. Encontré comentarios en tareas aprobadas: la API los devuelve en `description`, un campo que la primera versión de la skill omitía. Corregí el lector para conservar ese texto cuando existe fecha de revisión y estado `APPROVED` o `REJECTED`.

**Prueba con feedback real, 21:30:** la tarea propia `1017634`, «Connect Your Agent: Telegram, Google Drive & Calendar», pertenece a la cohorte `1688`. La lista y el detalle devolvieron HTTP 200. Su estado es `DONE`, su revisión `APPROVED` y tiene fecha de revisión.

Fragmento exacto del comentario recuperado de `description`:

> Me gustó que habilitaras solo las acciones necesarias. Aprobado.

La prueba confirma texto no vacío y coincidencia de tarea y cohorte. También pasaron tres casos: descripción sin revisión, comentario vacío y comentario de una tarea revisada. La respuesta no contiene nota numérica. Los resultados están en [prueba-feedback-real.json](prueba-feedback-real.json). Atlas repitió la consulta desde la conversación y devolvió el comentario real; la [petición y respuesta](conversaciones/feedback-real.md) documentan esta prueba. Se omite el saludo personal del comentario publicado.

## Comprobación final

A las 21:12 se ejecutaron las seis consultas y OpenClaw reconoció las seis skills como disponibles. En ese momento, la prueba de feedback solo demostraba acceso al detalle. La corrección y la prueba de las 21:30 completan la evidencia de texto real. [verificacion.json](verificacion.json) distingue ambas comprobaciones.

La revisión de privacidad del paquete actualizado no encontró el token en sus 26 archivos. El resultado está en [privacidad.json](privacidad.json).

También se revisó la clasificación de proyectos: una entrega con `DONE` no implica aprobación. La prueba real identificó los 7 proyectos pendientes de la cohorte principal y 2 aprobados de `personal-assistants-with-openclaw`. Pasaron además cinco casos de clasificación que cubren pendientes, revisión, aprobación, rechazo y estados sin clasificar.

### Revisión de los criterios

| Requisito | Evidencia |
| --- | --- |
| OpenClaw activo y accesible | Conversaciones reales con Atlas y reconocimiento de las seis skills. |
| Cuatro skills principales | Apartados 1 a 4 y sus pruebas con la API. |
| Dos skills adicionales | Cohortes y detalle/feedback, con la necesidad que las originó. |
| Una responsabilidad por skill | Cada carpeta contiene una función concreta y sus instrucciones. |
| Construcción conversacional | Peticiones originales enlazadas debajo y decisiones en cada apartado. |
| Token privado | Configuración fuera del repositorio, permisos `600`; no se incluye su valor. |
| Registro con prompt, función, API y prueba | Este archivo y las peticiones completas. |
| Información precisa | Estados literales, fórmulas reproducibles, alcance y límites expresos. |
| Entrega en GitHub | `SKILL_LOG.md` en la raíz del repositorio junto a las skills y la verificación. |

Las skills usan únicamente consultas de lectura. No cambian tareas, entregas ni permisos de 4Geeks.

### Incidencia del entorno

Una prueba adicional con las seis skills en una sola conversación se interrumpió por falta de memoria en el servidor. No se cuenta como superada. El servicio se recuperó; conviene evitar agrupar tantas operaciones en el servidor actual.

Después, Atlas respondió a una pregunta de progreso desde la conversación: seleccionó `4geeks-progreso`, consultó la API y devolvió 47/90 completadas y 44/90 aprobadas. La [petición y respuesta final](conversaciones/comprobacion-final.md) documentan esa prueba superada.

### Peticiones originales y archivos

| Conversación | Skill |
| --- | --- |
| [Descubrimiento](conversaciones/descubrimiento.md) | Plan inicial con Atlas. |
| [Petición 1](conversaciones/skill-1.md) | [Conexión](skills/4geeks-conexion/SKILL.md) |
| [Petición 2](conversaciones/skill-2.md) | [Proyectos](skills/4geeks-proyectos/SKILL.md) |
| [Petición 3](conversaciones/skill-3.md) | [Pendientes](skills/4geeks-pendientes/SKILL.md) |
| [Petición 4](conversaciones/skill-4.md) | [Progreso](skills/4geeks-progreso/SKILL.md) |
| [Petición 5](conversaciones/skill-5.md) | [Cohortes](skills/4geeks-cohortes/SKILL.md) |
| [Petición 6](conversaciones/skill-6.md) | [Detalle y feedback](skills/4geeks-feedback/SKILL.md) |
| [Corrección y prueba de feedback](conversaciones/feedback-real.md) | Consulta de una tarea revisada con comentario real. |

Los resultados corresponden al momento de las pruebas y cambiarán a medida que avance el curso.
