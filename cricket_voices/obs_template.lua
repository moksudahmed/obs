local obs = obslua

--------------------------------------------------
-- CONFIG
--------------------------------------------------
local LINKS_FILE_PATH = ""
local SCORE_FILE_PATH = ""
local VOICE_FOLDER = "C:/cricket_voices/"
local READY_FILE = VOICE_FOLDER .. "ready.json"
local VOICE_FOLDER_WIN = "C:\\cricket_voices\\"

--------------------------------------------------
-- VOICE SOURCES MAPPING
--------------------------------------------------
local VOICE_MAP = {
    WELCOME = "AI_WELCOME",
    DOT = "AI_DOT",
    SINGLE = "AI_SINGLE",
    DOUBLE = "AI_DOUBLE",
    TRIPLE = "AI_TRIPLE",
    FOUR = "AI_FOUR",
    SIX = "AI_SIX",
    WICKET = "AI_WICKET",
    OVER = "AI_OVER",
    WIDE = "AI_WIDE",
    NO_BALL = "AI_NO_BALL",
    FREE_HIT = "AI_FREE_HIT",
    BYE = "AI_BYE",
    LEG_BYE = "AI_LEG_BYE",
    MATCH_END = "AI_MATCH_END",
    TOSS = "AI_TOSS",
    LAST_OVER = "AI_LAST_OVER"
}

--------------------------------------------------
-- INTERNAL STATE
--------------------------------------------------
local last_event = ""
local last_crex_url = ""
local last_cricbuzz_url = ""
local match_started = false
local last_over = -1
local last_over_announced = false
local pending_events = {}  -- Queue for events waiting to play
local retry_counters = {}   -- Retry counters per event
local max_retries = 30      -- Retry for 15 seconds
local retry_interval = 5    -- Check every second

--------------------------------------------------
-- FLAG SOURCES
--------------------------------------------------
local flag_names = {
    ["Batting Flag"] = true,
    ["Bowling Flag"] = true
}

--------------------------------------------------
-- UTILITY
--------------------------------------------------
local function trim(s)
    return (s and s:gsub("^%s+", ""):gsub("%s+$", "")) or ""
end

local function file_exists(filepath)
    if not filepath then return false end
    local f = io.open(filepath, "r")
    if f then
        f:close()
        return true
    end
    return false
end

local function get_file_size(filepath)
    if not file_exists(filepath) then return 0 end
    local f = io.open(filepath, "rb")
    if not f then return 0 end
    local size = f:seek("end")
    f:close()
    return size
end

--------------------------------------------------
-- READ READY FILE (Signals from Python)
--------------------------------------------------
function read_ready_file()
    if not file_exists(READY_FILE) then
        return {}
    end
    
    local f = io.open(READY_FILE, "r")
    if not f then return {} end
    
    local content = f:read("*all")
    f:close()
    
    -- Parse JSON more reliably
    local ready = {}
    for event, _ in pairs(VOICE_MAP) do
        -- Look for event pattern
        local pattern = '"' .. event .. '":%s*"([^"]+)"'
        local filepath = string.match(content, pattern)
        if filepath and file_exists(filepath) then
            -- Verify file has content (not empty)
            if get_file_size(filepath) > 100 then  -- At least 100 bytes
                ready[event] = filepath
            end
        end
    end
    
    return ready
end

--------------------------------------------------
-- GET LATEST FILE (Fallback)
--------------------------------------------------
function get_latest_file_fallback(event)
    local pattern = VOICE_FOLDER_WIN .. event .. "_*.mp3"
    local command = 'dir "' .. pattern .. '" /b /o-d 2>nul'
    local handle = io.popen(command)
    
    if handle then
        local latest = handle:read("*l")
        handle:close()
        if latest and latest ~= "" then
            local full_path = VOICE_FOLDER .. latest
            if get_file_size(full_path) > 100 then
                return full_path
            end
        end
    end
    
    return nil
end

--------------------------------------------------
-- ASYNC VOICE PLAYER WITH RETRY QUEUE
--------------------------------------------------
local function try_play_event(event_name, retry_count)
    if not event_name or event_name == "" then
        return false
    end
    
    -- Get source name
    local source_name = VOICE_MAP[event_name]
    if not source_name then
        source_name = "AI_" .. event_name
    end
    
    -- Try to get ready file
    local ready = read_ready_file()
    local file_path = ready[event_name]
    
    -- Fallback to latest file if ready file not found
    if not file_path then
        file_path = get_latest_file_fallback(event_name)
    end
    
    if file_path then
        -- Get media source
        local source = obs.obs_get_source_by_name(source_name)
        if not source then
            print("[Cricket] ❌ Source not found: " .. source_name)
            return false
        end
        
        -- Update source with file
        local settings = obs.obs_source_get_settings(source)
        if settings then
            local current_file = obs.obs_data_get_string(settings, "local_file")
            if current_file ~= file_path then
                obs.obs_data_set_string(settings, "local_file", file_path)
                obs.obs_source_update(source, settings)
                print("[Cricket] 📁 Updated: " .. source_name .. " -> " .. file_path)
            end
            obs.obs_data_release(settings)
        end
        
        -- Play
        obs.obs_source_media_stop(source)
        obs.obs_source_media_restart(source)
        obs.obs_source_release(source)
        
        print("[Cricket] 🔊 Playing: " .. event_name .. " (retry: " .. retry_count .. ")")
        
        -- Clean up retry counter
        retry_counters[event_name] = nil
        
        return true
    end
    
    return false
end

-- Timer function to process pending events
function process_pending_events()
    local to_remove = {}
    
    for event_name, retry_count in pairs(pending_events) do
        if retry_count >= max_retries then
            -- Give up after max retries
            print("[Cricket] ❌ Failed to play " .. event_name .. " after " .. max_retries .. " retries")
            to_remove[event_name] = true
            retry_counters[event_name] = nil
        else
            -- Try to play the event
            if try_play_event(event_name, retry_count) then
                to_remove[event_name] = true
            else
                -- Increment retry counter for next time
                pending_events[event_name] = retry_count + 1
            end
        end
    end
    
    -- Remove completed/failed events
    for event_name, _ in pairs(to_remove) do
        pending_events[event_name] = nil
    end
end

--------------------------------------------------
-- PLAY VOICE (Add to queue)
--------------------------------------------------
function play_voice(event_name)
    if not event_name or event_name == "" then
        return false
    end
    
    -- Don't duplicate same event if it's already pending
    if pending_events[event_name] then
        print("[Cricket] ⏳ " .. event_name .. " already pending, skipping duplicate")
        return false
    end
    
    print("[Cricket] 📝 Queued: " .. event_name)
    
    -- Try immediate play first
    if try_play_event(event_name, 0) then
        return true
    end
    
    -- Add to pending queue for retry
    pending_events[event_name] = 1
    print("[Cricket] ⏳ Waiting for file generation: " .. event_name)
    
    return true
end

--------------------------------------------------
-- JSON READERS
--------------------------------------------------
local function json_string(content, key)
    if not content or not key then return nil end
    local pattern = '"' .. key .. '":%s*"([^"]+)"'
    return string.match(content, pattern)
end

local function json_number(content, key)
    if not content or not key then return nil end
    local pattern = '"' .. key .. '":%s*(%d+)'
    local v = string.match(content, pattern)
    return v and tonumber(v) or nil
end

local function json_float(content, key)
    if not content or not key then return nil end
    local pattern = '"' .. key .. '":%s*([%d.]+)'
    local v = string.match(content, pattern)
    return v and tonumber(v) or nil
end

--------------------------------------------------
-- SCORE FILE READER
--------------------------------------------------
function read_score_file()
    if SCORE_FILE_PATH == "" then return nil end
    
    if not file_exists(SCORE_FILE_PATH) then
        return nil
    end
    
    local f = io.open(SCORE_FILE_PATH, "r")
    if not f then return nil end
    
    local content = f:read("*all")
    f:close()
    
    if not content or content == "" then return nil end
    
    local data = {}
    data.score = json_number(content, "runs") or json_number(content, "score") or 0
    data.wickets = json_number(content, "wickets") or 0
    data.over = json_float(content, "over") or 0
    data.ball = json_number(content, "ball") or 0
    data.event = json_string(content, "event") or ""
    
    return data
end

--------------------------------------------------
-- EVENT HANDLER
--------------------------------------------------
function handle_event(event)
    if not event or event == "" then return end
    
    -- Don't replay the exact same event immediately
    if event == last_event then
        return
    end
    
    print("[Cricket] 🎯 Event: " .. event)
    
    local event_map = {
        DOT = "DOT",
        SINGLE = "SINGLE",
        DOUBLE = "DOUBLE",
        TRIPLE = "TRIPLE",
        FOUR = "FOUR",
        SIX = "SIX",
        WICKET = "WICKET",
        OVER_COMPLETE = "OVER",
        WIDE = "WIDE",
        NO_BALL = "NO_BALL",
        FREE_HIT = "FREE_HIT",
        BYE = "BYE",
        LEG_BYE = "LEG_BYE",
        MATCH_END = "MATCH_END",
        MATCH_RESULT = "MATCH_END",
        TOSS = "TOSS"
    }
    
    local voice_event = event_map[event]
    if voice_event then
        play_voice(voice_event)
    end
    
    last_event = event
end

--------------------------------------------------
-- MATCH PROCESS
--------------------------------------------------
function process_match()
    local data = read_score_file()
    if not data then return end
    
    local score = data.score or 0
    local wickets = data.wickets or 0
    local over = data.over or 0
    local ball = data.ball or 0
    local event = data.event or ""
    
    -- Match start
    if not match_started and over == 0 and ball <= 1 and score == 0 then
        match_started = true
        last_over_announced = false
        print("[Cricket] 🏏 Match started!")
        play_voice("WELCOME")
    end
    
    -- Handle event
    if event ~= "" then
        handle_event(event)
    end
    
    -- Last over
    if over == 19 and not last_over_announced and match_started then
        play_voice("LAST_OVER")
        last_over_announced = true
        print("[Cricket] 📢 Last over!")
    end
    
    last_over = over
end

--------------------------------------------------
-- URL HELPERS
--------------------------------------------------
local function is_crex_url(u)
    return u and u:match("^https?://[^/]*crex%.com/")
end

local function is_cricbuzz_url(u)
    return u and u:match("^https?://[^/]*cricbuzz%.com/")
end

--------------------------------------------------
-- READ LINKS FILE
--------------------------------------------------
function read_links_file()
    if LINKS_FILE_PATH == "" then return "", "" end
    
    if not file_exists(LINKS_FILE_PATH) then
        return "", ""
    end
    
    local f = io.open(LINKS_FILE_PATH, "r")
    if not f then return "", "" end
    
    local new_crex = ""
    local new_cricbuzz = ""
    
    for line in f:lines() do
        local l = trim(line)
        if new_crex == "" and is_crex_url(l) then
            new_crex = l
        elseif new_cricbuzz == "" and is_cricbuzz_url(l) then
            new_cricbuzz = l
        end
    end
    
    f:close()
    return new_crex, new_cricbuzz
end

--------------------------------------------------
-- UPDATE BROWSER SOURCES
--------------------------------------------------
function apply_links()
    local new_crex, new_cricbuzz = read_links_file()
    
    if new_crex == "" and new_cricbuzz == "" then return end
    if new_crex == last_crex_url and new_cricbuzz == last_cricbuzz_url then return end
    
    last_crex_url = new_crex
    last_cricbuzz_url = new_cricbuzz
    
    local sources = obs.obs_enum_sources()
    
    for _, src in ipairs(sources) do
        if obs.obs_source_get_id(src) == "browser_source" then
            local settings = obs.obs_source_get_settings(src)
            if settings then
                local url = obs.obs_data_get_string(settings, "url")
                local name = obs.obs_source_get_name(src)
                
                if is_crex_url(url) then
                    local target = new_crex
                    if flag_names[name] then
                        target = new_crex:gsub("/live$", "/info")
                    end
                    if url ~= target and target ~= "" then
                        obs.obs_data_set_string(settings, "url", target)
                        obs.obs_source_update(src, settings)
                    end
                elseif is_cricbuzz_url(url) then
                    if url ~= new_cricbuzz and new_cricbuzz ~= "" then
                        obs.obs_data_set_string(settings, "url", new_cricbuzz)
                        obs.obs_source_update(src, settings)
                    end
                end
                
                obs.obs_data_release(settings)
            end
        end
    end
    
    obs.source_list_release(sources)
end

--------------------------------------------------
-- TIMERS
--------------------------------------------------
function score_timer()
    pcall(process_match)
end

function link_timer()
    pcall(apply_links)
end

-- Clean up old retry counters periodically
function cleanup_timer()
    -- No cleanup needed, but we can log queue status
    if next(pending_events) then
        local queue_msg = "Pending events: "
        for event, retry in pairs(pending_events) do
            queue_msg = queue_msg .. event .. "(" .. retry .. ") "
        end
        print("[Cricket] " .. queue_msg)
    end
end

--------------------------------------------------
-- OBS UI
--------------------------------------------------
function script_description()
    return [[
🏏 Cricket Commentary System - ASYNC VERSION

✓ Queues events while files are being generated
✓ Retries up to 15 seconds for file to appear
✓ Never misses a commentary event!

How it works:
1. Event occurs in score.json
2. OBS queues the event for playback
3. Every second, OBS checks if the file is ready
4. Plays automatically when file appears
5. Retries until success or timeout

This ensures you NEVER hear old or missing files!
    ]]
end

function script_properties()
    local props = obs.obs_properties_create()
    
    obs.obs_properties_add_path(props, "links", "score_links.txt", obs.OBS_PATH_FILE, "*.txt", nil)
    obs.obs_properties_add_path(props, "score", "score.json", obs.OBS_PATH_FILE, "*.json", nil)
    
    return props
end

function script_update(settings)
    LINKS_FILE_PATH = obs.obs_data_get_string(settings, "links")
    SCORE_FILE_PATH = obs.obs_data_get_string(settings, "score")
end

function script_load(settings)
    print("[Cricket] ========================================")
    print("[Cricket] Cricket Commentary System - ASYNC VERSION")
    print("[Cricket] ========================================")
    
    script_update(settings)
    
    obs.timer_add(score_timer, 1000)           -- Check score every second
    obs.timer_add(link_timer, 5000)            -- Check links every 5 seconds
    obs.timer_add(process_pending_events, 1000) -- Process queue every second
    obs.timer_add(cleanup_timer, 10000)         -- Log queue status every 10 seconds
    
    print("[Cricket] Voice folder: " .. VOICE_FOLDER)
    print("[Cricket] System will queue events and retry for 15 seconds")
    print("[Cricket] Ready!")
end

function script_unload()
    print("[Cricket] System UNLOADED")
    obs.timer_remove(score_timer)
    obs.timer_remove(link_timer)
    obs.timer_remove(process_pending_events)
    obs.timer_remove(cleanup_timer)
end