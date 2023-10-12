-- Code is very much lifted from @Zunawe's Pokemon Emerald connector, modified
-- to use the specific offsets relevant to FE8.

local socket = require("socket")
local json = require("json")
require("common")

local SOCKET_PORT = 43053

local STATE_UNINITIALIZED = 0
local STATE_INITIAL_CONNECTION_MADE = 1
local STATE_TENTATIVELY_CONNECTED = 2
local STATE_OK = 3

local GAME_STATE_UNSAFE = 0
local GAME_STATE_SAFE = 1

local ap_socket = nil

local current_state = STATE_UNINITIALIZED
local previous_state = STATE_UNINITIALIZED

local current_game_state = GAME_STATE_UNSAFE

local received_items = {}

-- Offsets and sizes
local iwram_start = 0x3000000
local ewram_start = 0x2000000

-- CR cam: These offsets are currently configured by hand after inspecting the
-- results of the build (or pulling them from the relevant header files). We
-- should probably look towards populating them automatically eventually.

local flags_offset = 0x026E3C
local flags_size = 8
local archipelago_received_item_address = 0x026E44
local archipelago_received_item_index = 0x026E48

-- ROM addresses
local slot_name_address = 0xEFD05C

local proc_pool_address = 0x024E68
local proc_size = 0x6C
local num_procs = 0x40

-- These two include the ROM hardware offset because we compare against them as
-- literal values when checking if these procs are live.
local wm_proc_address = 0x08A3EE74
local e_player_phase_proc_address = 0x0859AAD8

local bizhawk_version = client.getversion()
local bizhawk_major, bizhawk_minor, bizhawk_patch = bizhawk_version:match("(%d+)%.(%d+)%.?(%d*)")
bizhawk_major = tonumber(bizhawk_major)
bizhawk_minor = tonumber(bizhawk_minor)

function check_game_state ()
    local current_proc = proc_pool_address
    local count = 0

    while count < num_procs do
      local ptr = memory.read_u32_le(current_proc, "EWRAM")
      if ptr == wm_proc_address or ptr == e_player_phase_proc_address then
        current_game_state = GAME_STATE_SAFE
        return
      end
      count = count + 1
      current_proc = current_proc + proc_size
    end
    current_game_state = GAME_STATE_UNSAFE
end

-- Process data received from AP client
function process_data (data)
    if (data == nil) then
        return
    end

    if (data["items"] ~= nil) then
        received_items = data["items"]
    end
end

-- Try to fill the received item struct with the next item
function try_write_next_item ()
    if (current_game_state == GAME_STATE_SAFE) then
        -- CR cam: this +2 is hand-computed from the definition of `struct APReceivedItem`
        local is_filled = memory.read_u8(archipelago_received_item_address + 2, "EWRAM")
        local item_index = memory.read_u32_le(archipelago_received_item_index, "EWRAM")

        if (is_filled ~= 0) then return end

        local next_item = received_items[item_index+1]
        if (next_item ~= nil) then
            -- TODO: progression filtering?
            memory.write_u16_le(archipelago_received_item_address + 0, next_item[1], "EWRAM")
            memory.write_u8(archipelago_received_item_address + 2, 1, "EWRAM")
            memory.write_u32_le(archipelago_received_item_index, item_index+1, "EWRAM")
        end
    end
end

-- Send relevant data to AP client (flags indicating checked locations)
-- AP client will deterimine which flags are important
function create_message ()
    local data = {}

    data["script_version"] = 1

    local slot_name = memory.read_bytes_as_array(slot_name_address, 64, "ROM")
    data["slot_name"] = slot_name

    -- TODO: do we need to check safety here somehow?
    local flag_bytes = memory.read_bytes_as_array(flags_offset, flags_size, "EWRAM")
    data["flag_bytes"] = flag_bytes

    return json.encode(data).."\n"
end

-- Receive data from AP client and send message back
function send_receive ()
    local message, err = ap_socket:receive()

    -- Handle errors
    if (err == "closed") then
        if (current_state == STATE_OK) then
            print("Connection closed")
        end
        current_state = STATE_UNINITIALIZED
        return
    elseif (err == "timeout") then
        return
    elseif err ~= nil then
        print(err)
        current_state = STATE_UNINITIALIZED
        return
    end

    -- Process received data
    if (message ~= nil and message ~= "") then
        process_data(json.decode(message))
    end

    -- Send data
    local result, err ap_socket:send(create_message())

    if (result == nil) then
        print(err)
    elseif (current_state == STATE_INITIAL_CONNECTION_MADE) then
        current_state = STATE_TENTATIVELY_CONNECTED
    elseif (current_state == STATE_TENTATIVELY_CONNECTED) then
        print("Connected!")
        current_state = STATE_OK
    end
end

function main ()
    if (bizhawk_major < 2 or (bizhawk_major == 2 and bizhawk_minor < 7)) then
        print("Must use a version of bizhawk 2.7.0 or higher")
        return
    elseif (isUntestedBizhawk) then
        print(untestedBizhawkMessage)
    end

    local frame = 0

    local server, err = socket.bind("localhost", SOCKET_PORT)
    if (err ~= nil) then
        print(err)
        return
    end

    while true do
        frame = frame + 1

        if not (current_state == previous_state) then
            previous_state = current_state
        end

        if (current_state == STATE_UNINITIALIZED) then
            if (frame % 60 == 0) then
                print("Trying to connect to client...")
                emu.frameadvance() -- To flush print message

                server:settimeout(2)
                local client, timeout = server:accept()
                if (timeout == nil) then
                    print("Connected!")
                    current_state = STATE_INITIAL_CONNECTION_MADE
                    ap_socket = client
                    ap_socket:settimeout(0)
                end
            end
        else
            if (frame % 10 == 0) then
                check_game_state()
                send_receive()
                try_write_next_item()
            end
        end

        emu.frameadvance()
    end
end

main()

