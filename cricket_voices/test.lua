local obs = obslua

--------------------------------------------------
-- CONFIG
--------------------------------------------------
local SCORE_FILE_PATH = ""
local LINKS_FILE_PATH = ""

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
    LAST_OVER = "AI_LAST_OVER",
    OVER_COMPLETE = "AI_OVER"  -- Map OVER_COMPLETE to AI_OVER
}

--------------------------------------------------
-- INTERNAL STATE
--------------------------------------------------
local last_event = ""
local last_mp3 = ""
local last_crex_url = ""
local last_cricbuzz_url = ""
local last_file_size = 0
local last_modified_time = 0

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

local function get_file_modified_time(filepath)
    if not file_exists(filepath) then return 0 end
    local f = io.open(filepath, "r")
    if not f then return 0 end
    local modified = f:seek("end")  -- Approximation, but works
    f:close()
    return modified
end

--------------------------------------------------
-- WAIT FOR COMPLETE JSON FILE
--------------------------------------------------
function is_json_complete(filepath)
    if not file_exists(filepath) then return false end
    
    -- Check if file size is stable (not being written)
    local current_size = get_file_size(filepath)
    local current_time = os.time()
    
    -- If file size changed recently, wait
    if current_size ~= last_file_size then
        last_file_size = current_size
        last_modified_time = current_time
        return false
    end
    
    -- If file size hasn't changed for 0.5 seconds, it's complete
    if current_time - last_modified_time > 0.15 then
        return true
    end
    
    return false
end

--------------------------------------------------
-- READ SCORE.JSON AND GET MP3 (with validation)
--------------------------------------------------
function get_event_and_mp3()
    if SCORE_FILE_PATH == "" then return nil, nil end
    if not file_exists(SCORE_FILE_PATH) then return nil, nil end
    
    -- Wait for file to be completely written
    if not is_json_complete(SCORE_FILE_PATH) then
        return nil, nil
    end
    
    local f = io.open(SCORE_FILE_PATH, "r")
    if not f then return nil, nil end
    
    local content = f:read("*all")
    f:close()
    
    if not content or content == "" then return nil, nil end
    
    -- Validate JSON format (check for balanced braces)
    local brace_count = 0
    for i = 1, #content do
        local char = content:sub(i, i)
        if char == "{" then
            brace_count = brace_count + 1
        elseif char == "}" then
            brace_count = brace_count - 1
        end
    end
    
    if brace_count ~= 0 then
        print("[Cricket] ⏳ JSON incomplete, waiting...")
        return nil, nil
    end
    
    -- Get event name
    local event = string.match(content, '"event"%s*:%s*"([^"]+)"')
    
    -- Get MP3 file for that event
    local mp3 = nil
    if event then
        local pattern = '"' .. event .. '"%s*:%s*"([^"]+)"'
        mp3 = string.match(content, pattern)
    end
    
    return event, mp3
end

--------------------------------------------------
-- PLAY VOICE (with source validation)
--------------------------------------------------
function play_voice(event_name, mp3_file)
    if not event_name or not mp3_file then
        return false
    end
    
    -- Check if file exists
    if not file_exists(mp3_file) then
        print("[Cricket] ⚠️ File not found: " .. mp3_file)
        return false
    end
    
    -- Map event names to source names
    local source_name = VOICE_MAP[event_name]
    if not source_name then
        source_name = "AI_" .. event_name
    end
    
    -- Also check if the event is OVER_COMPLETE and map to OVER
    if event_name == "OVER_COMPLETE" then
        source_name = "AI_OVER"
    end
    
    -- Get media source
    local source = obs.obs_get_source_by_name(source_name)
    if not source then
        print("[Cricket] ⚠️ Source not found: " .. source_name .. " - skipping")
        return false
    end
    
    -- Update source with MP3 file
    local settings = obs.obs_source_get_settings(source)
    if settings then
        obs.obs_data_set_string(settings, "local_file", mp3_file)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
    end
    
    -- Play
    obs.obs_source_media_stop(source)
    obs.obs_source_media_restart(source)
    obs.obs_source_release(source)
    
    print("[Cricket] 🔊 Playing: " .. event_name .. " -> " .. mp3_file)
    return true
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
                        print("[Cricket] 🔗 Updated Crex URL: " .. name)
                    end
                elseif is_cricbuzz_url(url) then
                    if url ~= new_cricbuzz and new_cricbuzz ~= "" then
                        obs.obs_data_set_string(settings, "url", new_cricbuzz)
                        obs.obs_source_update(src, settings)
                        print("[Cricket] 🔗 Updated Cricbuzz URL: " .. name)
                    end
                end
                
                obs.obs_data_release(settings)
            end
        end
    end
    
    obs.source_list_release(sources)
end

--------------------------------------------------
-- MAIN PROCESS
--------------------------------------------------
function process_score()
    local event, mp3 = get_event_and_mp3()
    
    if event and mp3 and (event ~= last_event or mp3 ~= last_mp3) then
        print("[Cricket] 🎯 New event: " .. event)
        play_voice(event, mp3)
        last_event = event
        last_mp3 = mp3
    end
end

--------------------------------------------------
-- TIMERS
--------------------------------------------------
function score_timer()
    pcall(process_score)
end

function link_timer()
    pcall(apply_links)
end

--------------------------------------------------
-- OBS UI
--------------------------------------------------
function script_description()
    return [[
🏏 Cricket Commentary System - SIMPLE

Reads score.json and plays the MP3 file directly.
Waits for JSON file to be completely written before reading.

JSON Format:
{
    "event": "SINGLE",
    "SINGLE": "C:/cricket_voices/SINGLE_1775456601040.mp3"
}

Note: Create media sources named:
- AI_WELCOME, AI_DOT, AI_SINGLE, AI_DOUBLE, AI_TRIPLE
- AI_FOUR, AI_SIX, AI_WICKET, AI_OVER, AI_WIDE
- AI_NO_BALL, AI_FREE_HIT, AI_BYE, AI_LEG_BYE
- AI_MATCH_END, AI_TOSS, AI_LAST_OVER
    ]]
end

function script_properties()
    local props = obs.obs_properties_create()
    
    obs.obs_properties_add_path(props, "score_file", "Score JSON File", obs.OBS_PATH_FILE, "*.json", nil)
    obs.obs_properties_add_path(props, "links_file", "Score Links TXT File", obs.OBS_PATH_FILE, "*.txt", nil)
    
    return props
end

function script_update(settings)
    SCORE_FILE_PATH = obs.obs_data_get_string(settings, "score_file")
    LINKS_FILE_PATH = obs.obs_data_get_string(settings, "links_file")
    
    if SCORE_FILE_PATH ~= "" then
        print("[Cricket] 📄 Score file: " .. SCORE_FILE_PATH)
    end
    if LINKS_FILE_PATH ~= "" then
        print("[Cricket] 🔗 Links file: " .. LINKS_FILE_PATH)
    end
end

function script_load(settings)
    print("[Cricket] ========================================")
    print("[Cricket] Cricket Commentary System - SIMPLE")
    print("[Cricket] ========================================")
    
    script_update(settings)
    
    obs.timer_add(score_timer, 500)   -- Check score every 0.5 seconds
    obs.timer_add(link_timer, 5000)   -- Check links every 5 seconds
    
    print("[Cricket] ✅ System ready!")
    print("[Cricket] 💡 Make sure you have AI_OVER source in your scene")
end

function script_unload()
    print("[Cricket] System unloaded")
    obs.timer_remove(score_timer)
    obs.timer_remove(link_timer)
end
