local obs = obslua

--------------------------------------------------
-- FILE PATHS
--------------------------------------------------

local SCORE_FILE_PATH = ""
local LINKS_FILE_PATH = ""

--------------------------------------------------
-- STATE
--------------------------------------------------

local last_event = ""
local last_score = 0
local last_wickets = 0
local last_over = -1

--------------------------------------------------
-- VOICE SOURCES
--------------------------------------------------

local VOICE_DOT = "AI_DOT"
local VOICE_SINGLE = "AI_SINGLE"
local VOICE_DOUBLE = "AI_DOUBLE"
local VOICE_TRIPLE = "AI_TRIPLE"
local VOICE_FOUR = "AI_FOUR"
local VOICE_SIX = "AI_SIX"
local VOICE_WICKET = "AI_WICKET"
local VOICE_MATCH_END = "AI_MATCH_END"

--------------------------------------------------
-- PLAY VOICE
--------------------------------------------------

function play_voice(name)

    local source = obs.obs_get_source_by_name(name)

    if source ~= nil then
        obs.obs_source_media_restart(source)
        obs.obs_source_release(source)
    end

end

--------------------------------------------------
-- JSON PARSER
--------------------------------------------------

local function json_number(content,key)

    local pattern = '"'..key..'":%s*(%d+)'
    local v = string.match(content,pattern)

    if v then return tonumber(v) end
    return 0

end

local function json_string(content,key)

    local pattern = '"'..key..'":%s*"([^"]+)"'
    return string.match(content,pattern)

end

--------------------------------------------------
-- READ SCORE FILE
--------------------------------------------------

function read_score_file()

    if SCORE_FILE_PATH == "" then return nil end

    local file = io.open(SCORE_FILE_PATH,"r")

    if not file then return nil end

    local content = file:read("*all")
    file:close()

    local data = {}

    data.score = json_number(content,"score")
    data.wickets = json_number(content,"wickets")
    data.over = json_number(content,"over")
    data.ball = json_number(content,"ball")
    data.event = json_string(content,"event")

    return data

end

--------------------------------------------------
-- EVENT HANDLER
--------------------------------------------------

function handle_event(event)

    if event == nil then return end
    if event == last_event then return end

    last_event = event

    if event == "DOT" then play_voice(VOICE_DOT) end
    if event == "SINGLE" then play_voice(VOICE_SINGLE) end
    if event == "DOUBLE" then play_voice(VOICE_DOUBLE) end
    if event == "TRIPLE" then play_voice(VOICE_TRIPLE) end
    if event == "FOUR" then play_voice(VOICE_FOUR) end
    if event == "SIX" then play_voice(VOICE_SIX) end
    if event == "WICKET" then play_voice(VOICE_WICKET) end
    if event == "MATCH_RESULT" then play_voice(VOICE_MATCH_END) end

end

--------------------------------------------------
-- PROCESS MATCH
--------------------------------------------------

function process_match()

    local data = read_score_file()

    if data == nil then return end

    handle_event(data.event)

    last_score = data.score
    last_wickets = data.wickets
    last_over = data.over

end

--------------------------------------------------
-- UPDATE BROWSER SOURCE
--------------------------------------------------

function update_browser_source(source_name,url)

    local source = obs.obs_get_source_by_name(source_name)

    if source == nil then
        print("Source not found:",source_name)
        return
    end

    local settings = obs.obs_source_get_settings(source)

    obs.obs_data_set_string(settings,"url",url)

    -- force reload
    obs.obs_data_set_bool(settings,"refreshnocache",true)

    obs.obs_source_update(source,settings)

    obs.obs_data_release(settings)
    obs.obs_source_release(source)

    print("Updated:",source_name)

end

--------------------------------------------------
-- READ LINKS FILE
--------------------------------------------------

function read_links()

    if LINKS_FILE_PATH == "" then return end

    local file = io.open(LINKS_FILE_PATH,"r")

    if not file then
        print("Links file missing")
        return
    end

    for line in file:lines() do

        local name,url = string.match(line,"(.+)%s*=%s*(.+)")

        if name and url then
            update_browser_source(name,url)
        end

    end

    file:close()

end

--------------------------------------------------
-- TIMERS
--------------------------------------------------

function score_timer()

    process_match()

end

function link_timer()

    read_links()

end

--------------------------------------------------
-- SCRIPT UI
--------------------------------------------------

function script_properties()

    local props = obs.obs_properties_create()

    obs.obs_properties_add_path(
        props,
        "score",
        "Score JSON File",
        obs.OBS_PATH_FILE,
        "*.json",
        nil
    )

    obs.obs_properties_add_path(
        props,
        "links",
        "Links File",
        obs.OBS_PATH_FILE,
        "*.txt",
        nil
    )

    return props

end

--------------------------------------------------
-- UPDATE SETTINGS
--------------------------------------------------

function script_update(settings)

    SCORE_FILE_PATH = obs.obs_data_get_string(settings,"score")
    LINKS_FILE_PATH = obs.obs_data_get_string(settings,"links")

end

--------------------------------------------------
-- SCRIPT LOAD
--------------------------------------------------

function script_load(settings)

    obs.timer_add(score_timer,1000)
    obs.timer_add(link_timer,2000)

end

--------------------------------------------------
-- SCRIPT UNLOAD
--------------------------------------------------

function script_unload()

    obs.timer_remove(score_timer)
    obs.timer_remove(link_timer)

end