-- Forever Translate: pixel bridge encoder.
-- Pure Lua 5.1 (no WoW API calls) so it can be tested outside the game.
--
-- The grid is COLS x ROWS coloured blocks. Each block carries 3 nibbles
-- (4 bits each) in its red, green and blue channels, drawn as nibble*17
-- (0, 17, 34 ... 255). Layout, in block order (left to right, top to bottom):
--   0-3    finder pattern: magenta, green, magenta, green
--   4-19   calibration: grey level k for k = 0..15 (lets the app undo gamma)
--   20     sequence number (12 bits)
--   21     payload length in bytes (12 bits)
--   22     checksum (12 bits)
--   23+    payload bytes, high nibble then low nibble, 3 nibbles per block
--   last 2 end markers: green, magenta (bottom-right corner; lets the app
--          measure the exact block size)

local E = {}
ForeverTranslateEncoder = E

E.COLS = 64
E.ROWS = 8
E.BLOCKS = E.COLS * E.ROWS
E.HEADER_BLOCKS = 23
E.MAX_BYTES = math.floor(((E.BLOCKS - E.HEADER_BLOCKS - 2) * 3) / 2) -- 730

local MAGENTA = { 255, 0, 255 }
local GREEN = { 0, 255, 0 }

local function nibbles12(v)
  v = v % 4096
  return math.floor(v / 256), math.floor(v / 16) % 16, v % 16
end

function E.Checksum(payload)
  local sum = 0
  for i = 1, #payload do
    sum = (sum + string.byte(payload, i) * ((i - 1) % 7 + 1)) % 4096
  end
  return sum
end

-- Cut a string to at most maxBytes without splitting a UTF-8 character.
function E.TruncateUTF8(s, maxBytes)
  if #s <= maxBytes then return s end
  local cut = maxBytes
  -- step back while the next byte would be a continuation byte (10xxxxxx)
  while cut > 0 do
    local b = string.byte(s, cut + 1)
    if b == nil or b < 128 or b >= 192 then break end
    cut = cut - 1
  end
  return string.sub(s, 1, cut)
end

-- Returns a list of BLOCKS colours, each {r, g, b} with 0-255 values.
function E.Encode(seq, payload)
  payload = E.TruncateUTF8(payload, E.MAX_BYTES)
  local blocks = {}
  blocks[1] = MAGENTA
  blocks[2] = GREEN
  blocks[3] = MAGENTA
  blocks[4] = GREEN
  for k = 0, 15 do
    local v = k * 17
    blocks[5 + k] = { v, v, v }
  end

  local function put12(index, value)
    local a, b, c = nibbles12(value)
    blocks[index] = { a * 17, b * 17, c * 17 }
  end
  put12(21, seq)
  put12(22, #payload)
  put12(23, E.Checksum(payload))

  local nib = {}
  for i = 1, #payload do
    local byte = string.byte(payload, i)
    nib[#nib + 1] = math.floor(byte / 16)
    nib[#nib + 1] = byte % 16
  end

  local index = E.HEADER_BLOCKS + 1
  local n = 1
  while index <= E.BLOCKS - 2 do
    local r, g, b = nib[n] or 0, nib[n + 1] or 0, nib[n + 2] or 0
    blocks[index] = { r * 17, g * 17, b * 17 }
    n = n + 3
    index = index + 1
  end
  blocks[E.BLOCKS - 1] = GREEN
  blocks[E.BLOCKS] = MAGENTA
  return blocks
end

return E
