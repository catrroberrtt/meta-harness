# Publicar el repositorio central

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Antes de hacer público este repositorio hay que completar la lista de abajo. Lo que ya está en el historial de git también se publicaría: reescribirlo es mucho más caro que prevenirlo.

## Lista de comprobación previa

- [ ] **Escaneo en verde, historial incluido.** `python3 herramientas/harness-escaneo-publico.py . --lista-prohibidos <lista> --lista-nombres <lista> --exigir-listas` termina con código 0 (0 hallazgos en el árbol y 0 en el historial). La lista de términos prohibidos (empresa, proyectos, usuarios, hosts) la mantiene el dueño fuera del repositorio o en un `.prohibidos.txt` no versionado.
- [ ] **Casos de ejemplo anonimizados.** Ningún caso, plantilla ni prueba contiene nombres reales, cuentas, hosts, correos ni identificadores de tickets de una organización.
- [x] **Licencia elegida** (Apache-2.0) y archivo `LICENSE` añadido.
- [ ] **`SECURITY.md`** presente, con un canal de contacto real para reportes.
- [ ] **`CONTRIBUTING.md`** presente y vigente.
- [ ] **Protección de la rama principal:** sin push directo, revisión obligatoria, pruebas y escaneo como comprobaciones requeridas, sin force-push.
- [ ] **Quién aprueba aportes:** lista nombrada de al menos dos personas con permiso de fusión (o una y un plan de suplencia).
- [ ] **Escaneo de secretos en CI** activado en el servicio donde se aloje (además de este escaneo local).
- [ ] Revisión manual final del árbol y de los metadatos de commit (correos de autor).
- [ ] Dónde vive (cuenta personal u organización) decidido.

## Si se publica un secreto por error

1. **Rotar o revocar el secreto de inmediato.** Es el único paso que lo neutraliza; reescribir historial no basta, porque pudo copiarse.
2. Evaluar si se usó: revisar registros del proveedor del secreto.
3. Reescribir el historial para quitarlo (por ejemplo con `git filter-repo`), forzar la actualización y pedir al servicio de alojamiento que purgue cachés y vistas de los commits antiguos.
4. Avisar a quienes clonaron o hicieron fork: deben descartar sus copias.
5. Ejecutar de nuevo el escaneo (historial incluido) y registrar el incidente y la causa; añadir el patrón al escaneo si no lo detectó.

## Opciones de licencia (decide el dueño)

| Opción | Qué permite | Consecuencias |
|---|---|---|
| **MIT** | Usar, copiar, modificar y redistribuir, incluso en software cerrado, conservando el aviso | Máxima adopción y mínima fricción. No obliga a devolver mejoras ni da protección explícita de patentes. |
| **Apache-2.0** | Lo mismo que MIT, más concesión expresa de patentes y cláusula de terminación si se litiga | Adopción alta y más seguridad jurídica para empresas; texto más largo, exige indicar cambios y conservar avisos. |
| **AGPL-3.0** | Uso libre, pero toda versión modificada, incluso ofrecida solo como servicio en red, debe publicarse bajo la misma licencia | Protege contra apropiación cerrada; muchas empresas la vetan, lo que reduce la adopción corporativa. |
| **Sin licencia (todos los derechos reservados)** | Se puede ver (según el servicio) pero nadie puede legalmente usar, copiar ni modificar | No es de código abierto: nadie puede aportar ni reutilizar con seguridad, y los forks quedan en zona gris. Solo tiene sentido para publicar a modo de consulta. |

**Recomendación:** Apache-2.0. Es permisiva (el objetivo es que el método se adopte y se instale), añade la protección de patentes que MIT no tiene y es bien aceptada por equipos corporativos. Si prioriza que las mejoras vuelvan a la comunidad por encima de la adopción, AGPL-3.0.

**Estado: DECISIÓN PENDIENTE del dueño.** Este repositorio no incluye `LICENSE` hasta que la elija. Una vez elegida: añadir `LICENSE`, la mención en `README.md`, y confirmar que los aportes se aceptan bajo esa licencia (ver `CONTRIBUTING.md`).

## Decisiones del dueño (7-oct-2026)
- **Licencia: Apache-2.0.** `LICENSE` es el texto oficial sin modificar; `NOTICE` firma a nombre de la persona (Cristofer Alfaro), no de una organización.
- **Historial: un solo commit limpio al publicar.** El historial de trabajo se conserva solo en local (rama `historial-local`, nunca publicada).
- **Dónde vive:** cuenta personal `catrroberrtt`, repositorio público `meta-harness`.
- **Seguridad:** reporte privado de vulnerabilidades de GitHub (ver `SECURITY.md`).
- **Escaneo:** el árbol da 0 hallazgos con `.permitidos.txt`: 56 excepciones revisadas a mano, cada una con su motivo (correos que no son personas, secretos falsos de prueba y nombres de campo). La clase `prohibido` (empresa o proyecto) no admite excepciones. La lista de términos prohibidos no se publica: vive fuera del repositorio.
