local ADDON, PB = ...

-- Missing keys resolve to the key itself, so an untranslated string shows up as
-- a readable token instead of an empty font string.
PB.L = setmetatable({}, { __index = function(_, key) return key end })
