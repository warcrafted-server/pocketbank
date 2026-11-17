local ADDON, PB = ...

local locale = GetLocale()
if locale ~= "esES" and locale ~= "esMX" then return end

local L = PB.L

L.WINDOW_TITLE = "PocketBank"
L.BANK = "Banco"
L.SEARCH = "Buscar"
L.LAST_SCANNED = "Último escaneo: %s"
L.NO_DATA = "Aún sin datos. Visita el banco para guardar su contenido."
L.MINIMAP_TOOLTIP_TITLE = "PocketBank"
L.MINIMAP_TOOLTIP_LEFT = "Clic izquierdo: abrir o cerrar la ventana"
L.MINIMAP_TOOLTIP_DRAG = "Arrastrar: mover este botón"
L.BANK_SAVED = "Banco guardado (%d objetos)."
L.WINDOW_NOT_READY = "La ventana aún no está disponible."
L.BANK_TITLE = "Banco de %s"
L.DATE_FORMAT = "%d/%m/%Y %H:%M"
L.NO_DATA_OTHER = "Aún no hay datos del banco de este personaje. Entra con él y visita el banco."
L.BAGS = "Bolsas"
L.BAGS_TITLE = "Bolsas de %s"
L.NO_BAG_DATA = "Aún sin datos de las bolsas. Se guardan solas al entrar al juego."
L.NO_BAG_DATA_OTHER = "Aún no hay datos de las bolsas de este personaje. Entra con él una vez."
