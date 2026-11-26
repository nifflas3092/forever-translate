-- Forever Translate: in-game slang glossing (works without the desktop app).
-- When someone writes common WoW words in Spanish, Portuguese, Russian,
-- German or French, a short grey English hint is added after their message,
-- e.g.  "alguien para dg? falta tanque (EN: anyone, dungeon, need, tank)".
-- Only words from the list below are matched, as plain text; nothing is run.

local G = {}
ForeverTranslateGloss = G

local WORDS = {
  -- Spanish
  dg = "dungeon",
  tanque = "tank", sanador = "healer", curandero = "healer", curador = "healer",
  mazmorra = "dungeon", mazmorras = "dungeons", banda = "raid", grupo = "group",
  busco = "looking for", buscando = "looking for", busca = "looking for",
  falta = "need", faltan = "need", necesito = "I need", necesitamos = "we need",
  alguien = "anyone", quien = "who", ["quién"] = "who", ayuda = "help",
  gracias = "thanks", hola = "hi", ["adiós"] = "bye", adios = "bye",
  oro = "gold", plata = "silver", cobre = "copper", vendo = "selling", compro = "buying",
  ["misión"] = "quest", mision = "quest", jefe = "boss", nivel = "level",
  espera = "wait", esperen = "wait", vamos = "let's go", voy = "coming",
  perdon = "sorry", ["perdón"] = "sorry", porfa = "please", jaja = "haha", jajaja = "haha",
  entrenador = "trainer", donde = "where", ["dónde"] = "where", muerto = "dead",
  montura = "mount", bolsa = "bag", armadura = "armor", arma = "weapon",
  -- Portuguese
  curandeiro = "healer", masmorra = "dungeon", raide = "raid",
  procuro = "looking for", procurando = "looking for", preciso = "I need",
  precisa = "need", precisamos = "we need", ["alguém"] = "anyone", alguem = "anyone",
  ajuda = "help", obrigado = "thanks", obrigada = "thanks", valeu = "thanks", vlw = "thanks",
  ["olá"] = "hi", oi = "hi", ouro = "gold", prata = "silver", ["missão"] = "quest",
  missao = "quest", chefe = "boss", ["nível"] = "level", desculpa = "sorry",
  kkk = "haha", kkkk = "haha", rsrs = "lol", onde = "where", treinador = "trainer",
  ["você"] = "you", vc = "you", vcs = "you all", mano = "bro",
  -- Russian
  ["танк"] = "tank", ["хил"] = "healer", ["хилер"] = "healer", ["дд"] = "dps",
  ["рейд"] = "raid", ["данж"] = "dungeon", ["подземелье"] = "dungeon",
  ["группа"] = "group", ["пати"] = "group", ["ищу"] = "looking for",
  ["нужен"] = "need", ["нужна"] = "need", ["нужно"] = "need", ["кто"] = "who",
  ["помогите"] = "help", ["помощь"] = "help", ["спасибо"] = "thanks", ["спс"] = "thanks",
  ["привет"] = "hi", ["пока"] = "bye", ["золото"] = "gold", ["голд"] = "gold",
  ["продам"] = "selling", ["куплю"] = "buying", ["квест"] = "quest", ["босс"] = "boss",
  ["лвл"] = "level", ["жди"] = "wait", ["подожди"] = "wait", ["го"] = "let's go",
  ["извини"] = "sorry", ["плз"] = "please", ["пожалуйста"] = "please",
  ["да"] = "yes", ["нет"] = "no", ["где"] = "where", ["хаха"] = "haha", ["ахах"] = "haha",
  -- German
  suche = "looking for", suchen = "looking for", brauche = "I need", brauchen = "we need",
  heiler = "healer", gruppe = "group", schlachtzug = "raid", jemand = "anyone",
  hilfe = "help", danke = "thanks", hallo = "hi", ["tschüss"] = "bye",
  verkaufe = "selling", kaufe = "buying", warte = "wait", bitte = "please",
  ja = "yes", nein = "no", wo = "where", heute = "today", abend = "evening",
  -- French
  cherche = "looking for", besoin = "need", soigneur = "healer", groupe = "group",
  donjon = "dungeon", aide = "help", merci = "thanks", salut = "hi", bonjour = "hi",
  vends = "selling", ["achète"] = "buying", ["quête"] = "quest", attends = "wait",
  ["désolé"] = "sorry", svp = "please", stp = "please", oui = "yes",
}

local MAX_HINTS = 5

-- Lower-case ASCII and Cyrillic capitals (other letters are left as they are).
local function Lower(s)
  s = s:lower()
  s = s:gsub("\208([\144-\159])", function(c) return "\208" .. string.char(c:byte() + 32) end)
  s = s:gsub("\208([\160-\175])", function(c) return "\209" .. string.char(c:byte() - 32) end)
  s = s:gsub("\208\129", "\209\145") -- Ё -> ё
  return s
end

-- Returns the English hint for a message, or nil.
function G.Hint(text)
  if type(text) ~= "string" or text == "" or #text > 600 then return nil end
  local clean = text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""):gsub("|H.-|h(.-)|h", "%1")
  local seen, hints = {}, {}
  -- words are runs of letters/bytes that are not spaces or ASCII punctuation
  for word in Lower(clean):gmatch("[^%s%p%d]+") do
    local meaning = WORDS[word]
    if meaning and not seen[meaning] then
      seen[meaning] = true
      hints[#hints + 1] = meaning
      if #hints >= MAX_HINTS then break end
    end
  end
  if #hints == 0 then return nil end
  return "(EN: " .. table.concat(hints, ", ") .. ")"
end

return G
