# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

## [0.6.0] - 2026-11-21

### Añadido

- La ventana se puede mover arrastrándola por el título o el fondo; recuerda su posición (esquina superior izquierda, la misma para toda la cuenta) y no se sale de la pantalla.
- `/pb reset` devuelve la ventana a su sitio por defecto.

## [0.5.0] - 2026-11-20

### Añadido

- Tooltip de los objetos con cuántos tiene cada personaje de la cuenta (nombre en el color de su clase y el reparto entre banco, bolsas y equipo), y el total cuando lo tienen varios. Funciona en cualquier tooltip de objeto del juego (bolsas, chat, vendedores, subasta…), no solo en la ventana de PocketBank.

## [0.4.0] - 2026-11-18

### Añadido

- Equipo: se guarda solo al entrar al juego y al cambiarlo. Tercera pestaña lateral con una copia de la hoja de personaje (casillas, fondo de su raza, nivel y clase), también para los demás personajes. Modelo 3D: el personaje conectado tal cual; otro de la misma raza y sexo, con el cuerpo del conectado y su equipo guardado; de otra raza, sin modelo y con un aviso, porque el juego no permite cargarlo. Las armas se ven envainadas, como en la hoja del juego.
- Tooltip de cada pieza de equipo sin la comparación con lo que llevas puesto.
- Diagnóstico `/pb paperdoll`.

## [0.3.0] - 2026-11-18

### Añadido

- Bolsas: se guardan solas al entrar al juego y en cada cambio (mochila, las cuatro bolsas y la casilla de la bolsa de profesión; el llavero no). Pestaña lateral nueva que las muestra en la misma rejilla, también las de los demás personajes, con su propio aviso si aún no hay datos.

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
