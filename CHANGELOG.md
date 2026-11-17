# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

## [0.2.0] - 2026-11-17

### Añadido

- Selector de personaje en la ventana: desplegable con todos los personajes guardados (nombre completo en el color de su clase, el conectado primero) que muestra el banco, el dinero y la fecha de la última visita del elegido, con el icono de su clase como retrato. Recuerda el elegido al cerrar y abrir la ventana.
- Aviso propio para los personajes que aún no han visitado el banco.

### Corregido

- El dinero guardado podía quedar a 0 al cerrar sesión; ya no se sobrescribe al salir y se guarda también al entrar en el mundo.
- El aviso de «sin datos» quedaba tapado por las casillas; ahora se ve encima, sobre una franja oscura.

## [0.1.0] - 2026-11-17

### Añadido

- Escaneo del banco al visitarlo: guarda el contenido del banco y de sus bolsas por personaje (clave GUID, porque Forever no tiene reinos), con la fecha, el dinero, la clase, el nivel y el nombre de dos partes.
- Ventana del banco de solo lectura con el aspecto del banco del juego: marco con retrato, rejilla de 8 columnas con las bolsas del banco como filas extra, pestaña lateral, fecha del último escaneo y dinero.
- Tooltip de cada objeto; Mayús + clic enlaza el objeto en el chat.
- Botón del minimapa (arrastrable, recuerda su posición) y `/pb` para abrir o cerrar la ventana; `/pb version`.
- Diagnóstico `/pb debug` y `/pb frames` para soporte.
- Localización en español e inglés.
