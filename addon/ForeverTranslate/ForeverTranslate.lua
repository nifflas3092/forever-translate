-- Forever Translate: adds English hints for common foreign WoW words in chat
-- (Gloss.lua), and catches chat messages and shows them, one at a time,
-- as a small strip of coloured blocks in the bottom-right corner of the screen.
-- The Forever Translate desktop app reads that strip and translates it.
-- (Addons cannot reach the internet, so the app does the translating.)

local E = ForeverTranslateEncoder

local BLOCK_PIXELS = 3      -- size of one block on screen, in real pixels
local HOLD_SECONDS = 0.15   -- how long each message stays on screen
local MAX_QUEUE = 60

local DEFAULTS = {
  enabled = true,
  gloss = true, -- add short English hints for common foreign WoW words
  point = { "BOTTOMLEFT", "BOTTOMLEFT", 0, 0 }, -- where the strip sits
  channels = {
    say = true, yell = true, whisper = true, party = true, raid = true,
    guild = true, officer = true, instance = true, channel = true,
  },
}

local EVENTS = {
  CHAT_MSG_SAY = { "say", "Say" },
  CHAT_MSG_YELL = { "yell", "Yell" },
  CHAT_MSG_WHISPER = { "whisper", "Whisper" },
  CHAT_MSG_PARTY = { "party", "Party" },
  CHAT_MSG_PARTY_LEADER = { "party", "Party" },
  CHAT_MSG_RAID = { "raid", "Raid" },
  CHAT_MSG_RAID_LEADER = { "raid", "Raid" },
  CHAT_MSG_RAID_WARNING = { "raid", "Raid" },
  CHAT_MSG_GUILD = { "guild", "Guild" },
  CHAT_MSG_OFFICER = { "officer", "Officer" },
  CHAT_MSG_INSTANCE_CHAT = { "instance", "Instance" },
  CHAT_MSG_INSTANCE_CHAT_LEADER = { "instance", "Instance" },
  CHAT_MSG_CHANNEL = { "channel", nil }, -- label comes from the channel name
}

local HELLO_SECONDS = 20     -- re-announce the game language when chat is quiet

local db
local queue = {}
local lastHello = 0
local seq = 0
local shownAt = 0
local bridge, textures = nil, {}

local function Print(msg)
  DEFAULT_CHAT_FRAME:AddMessage("|cff66ccffForever Translate:|r " .. msg)
end

local function CopyDefaults(src, dst)
  for k, v in pairs(src) do
    if type(v) == "table" then
      if type(dst[k]) ~= "table" then dst[k] = {} end
      CopyDefaults(v, dst[k])
    elseif dst[k] == nil then
      dst[k] = v
    end
  end
end

-- Remove colour codes, textures and link wrappers so only readable text is sent.
local function CleanText(text)
  text = text:gsub("|c%x%x%x%x%x%x%x%x", "")
  text = text:gsub("|r", "")
  text = text:gsub("|T.-|t", "")
  text = text:gsub("|A.-|a", "")
  text = text:gsub("|H.-|h(.-)|h", "%1")
  text = text:gsub("\t", " ")
  return text
end

local function ShortName(name)
  if not name then return "?" end
  return (name:gsub("%-.*$", ""))
end

------------------------------------------------------------------------
-- The on-screen bridge
------------------------------------------------------------------------

local function ScreenPixelHeight()
  if GetPhysicalScreenSize then
    local _, h = GetPhysicalScreenSize()
    if h and h > 0 then return h end
  end
  for _, cvar in ipairs({ "gxWindowedResolution", "gxFullscreenResolution", "gxResolution" }) do
    local value = GetCVar and GetCVar(cvar)
    local h = value and tonumber(value:match("%d+x(%d+)"))
    if h and h > 0 then return h end
  end
  return 1080
end

local function SetBlockColor(tex, r, g, b)
  if tex.SetColorTexture then
    tex:SetColorTexture(r / 255, g / 255, b / 255, 1)
  else
    tex:SetTexture(r / 255, g / 255, b / 255, 1)
  end
end

local function BuildBridge()
  -- No parent: scale is always 1 (768 units tall) and it stays visible
  -- even when the UI is hidden with Alt+Z.
  bridge = CreateFrame("Frame", "ForeverTranslateBridge", nil)
  bridge:SetFrameStrata("TOOLTIP")
  bridge:SetScale(1)
  local unit = BLOCK_PIXELS * 768 / ScreenPixelHeight()
  bridge:SetSize(unit * E.COLS, unit * E.ROWS)
  local p = db.point
  bridge:SetPoint(p[1], UIParent, p[2], p[3], p[4])
  bridge:SetMovable(true)
  bridge:SetClampedToScreen(true)
  bridge:RegisterForDrag("LeftButton")
  bridge:SetScript("OnDragStart", bridge.StartMoving)
  bridge:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    local point, _, relPoint, x, y = self:GetPoint(1)
    db.point = { point, relPoint, x, y }
  end)

  for i = 1, E.BLOCKS do
    local col = (i - 1) % E.COLS
    local row = math.floor((i - 1) / E.COLS)
    local tex = bridge:CreateTexture(nil, "OVERLAY")
    tex:SetSize(unit, unit)
    tex:SetPoint("TOPLEFT", bridge, "TOPLEFT", col * unit, -row * unit)
    textures[i] = tex
  end
end

local function Show(payload)
  seq = (seq + 1) % 4096
  local blocks = E.Encode(seq, payload)
  for i = 1, E.BLOCKS do
    local c = blocks[i]
    SetBlockColor(textures[i], c[1], c[2], c[3])
  end
  bridge:Show()
end

local function Enqueue(payload)
  if #queue >= MAX_QUEUE then table.remove(queue, 1) end
  queue[#queue + 1] = payload
end

local function Hello()
  local locale = (GetLocale and GetLocale()) or "enUS"
  -- "\1" can't appear in a real channel name, so players can't fake this
  Enqueue("\1FT\tForever Translate\tconnected " .. locale)
  lastHello = GetTime()
end

local function OnUpdate()
  if not db.enabled then return end
  local now = GetTime()
  -- so the app learns the game language even if it starts after you log in
  if #queue == 0 and now - lastHello >= HELLO_SECONDS then Hello() end
  if #queue > 0 and now - shownAt >= HOLD_SECONDS then
    Show(table.remove(queue, 1))
    shownAt = now
  end
end

------------------------------------------------------------------------
-- Events and slash commands
------------------------------------------------------------------------

local playerName

local function OnChat(event, text, sender, _, channelString, _, _, _, _, channelBaseName)
  local info = EVENTS[event]
  if not info or not db.enabled or not db.channels[info[1]] then return end
  if ShortName(sender) == playerName then return end
  text = CleanText(text or "")
  if not text:find("%S") then return end

  local label = info[2]
  if not label then
    label = channelBaseName
    if not label or label == "" then
      label = (channelString or "Channel"):gsub("^%d+%.%s*", "")
    end
    label = label:gsub("%s*%-.*$", "") -- "Trade - City" -> "Trade"
  end
  Enqueue(label .. "\t" .. ShortName(sender) .. "\t" .. text)
end

------------------------------------------------------------------------
-- Slang hints in the chat window (works without the desktop app)
------------------------------------------------------------------------

local function GlossFilter(self, event, msg, author, ...)
  if not db or not db.gloss or ShortName(author) == playerName then return false end
  local hint = ForeverTranslateGloss.Hint(msg)
  if hint then
    return false, msg .. "  |cff9d9d9d" .. hint .. "|r", author, ...
  end
  return false
end

local function SetupGloss()
  local locale = (GetLocale and GetLocale()) or "enUS"
  if locale:sub(1, 2) ~= "en" or not ChatFrame_AddMessageEventFilter then return end
  for chatEvent in pairs(EVENTS) do
    ChatFrame_AddMessageEventFilter(chatEvent, GlossFilter)
  end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function(self, event, ...)
  if event == "PLAYER_LOGIN" then
    ForeverTranslateDB = ForeverTranslateDB or {}
    db = ForeverTranslateDB
    CopyDefaults(DEFAULTS, db)
    playerName = UnitName("player")
    BuildBridge()
    SetupGloss()
    if not db.enabled then bridge:Hide() end
    Hello()
    for chatEvent in pairs(EVENTS) do
      pcall(self.RegisterEvent, self, chatEvent)
    end
    self:SetScript("OnUpdate", OnUpdate)
    Print("loaded. Type /ftr for options.")
  else
    OnChat(event, ...)
  end
end)

SLASH_FOREVERTRANSLATE1 = "/ftr"
SlashCmdList.FOREVERTRANSLATE = function(input)
  local cmd, arg = (input or ""):lower():match("^(%S*)%s*(.-)$")
  if cmd == "on" or cmd == "off" then
    db.enabled = (cmd == "on")
    if db.enabled then bridge:Show() else bridge:Hide() end
    Print(db.enabled and "on." or "off. The corner strip is hidden.")
  elseif cmd == "move" then
    local moving = not bridge:IsMouseEnabled()
    bridge:EnableMouse(moving)
    if moving then
      Print("drag the strip with the mouse, then type /ftr move again to lock it.")
    else
      Print("strip locked in place.")
    end
  elseif cmd == "reset" then
    db.point = { "BOTTOMLEFT", "BOTTOMLEFT", 0, 0 }
    bridge:ClearAllPoints()
    bridge:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 0, 0)
    Print("strip moved back to the bottom-left corner.")
  elseif cmd == "gloss" then
    db.gloss = not db.gloss
    Print("slang hints are now " .. (db.gloss and "on" or "off") .. ".")
  elseif cmd == "test" then
    Enqueue("Test\tPedro\thola! alguien para Minas de la Muerte? falta tanque")
    Enqueue("Test\tMaria\tvoce tem bandagem? obrigada")
    Enqueue("Test\tIvan\tкто идёт в рейд сегодня?")
    Print("sent 3 test messages to the app.")
  elseif cmd == "channel" and db.channels[arg] ~= nil then
    db.channels[arg] = not db.channels[arg]
    Print(arg .. " is now " .. (db.channels[arg] and "on" or "off") .. ".")
  else
    Print("commands:")
    Print("/ftr on, /ftr off - turn sending on or off")
    Print("/ftr test - send 3 sample messages to the app")
    Print("/ftr gloss - turn the grey English slang hints on or off")
    Print("/ftr move - unlock the strip so you can drag it; again to lock")
    Print("/ftr reset - put the strip back in the bottom-left corner")
    local list = {}
    for name, on in pairs(db.channels) do
      list[#list + 1] = name .. (on and "" or " (off)")
    end
    table.sort(list)
    Print("/ftr channel <name> - toggle one of: " .. table.concat(list, ", "))
  end
end
