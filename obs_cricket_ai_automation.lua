local obs = obslua

--------------------------------------------------
-- CONFIG
--------------------------------------------------

local LINKS_FILE_PATH = ""
local SCORE_FILE_PATH = ""

--------------------------------------------------
-- VOICE SOURCES
--------------------------------------------------

local VOICE_WELCOME = "AI_WELCOME"
local VOICE_DOT = "AI_DOT"
local VOICE_SINGLE = "AI_SINGLE"
local VOICE_DOUBLE = "AI_DOUBLE"
local VOICE_TRIPLE = "AI_TRIPLE"
local VOICE_FOUR = "AI_FOUR"
local VOICE_SIX = "AI_SIX"
local VOICE_WICKET = "AI_WICKET"
local VOICE_OVER = "AI_OVER"
local VOICE_WIDE = "AI_WIDE"
local VOICE_NO_BALL = "AI_NO_BALL"
local VOICE_FREE_HIT = "AI_FREE_HIT"
local VOICE_BYE = "AI_BYE"
local VOICE_LEG_BYE = "AI_LEG_BYE"
local VOICE_MATCH_END = "AI_MATCH_END"
local VOICE_LAST_OVER = "AI_LAST_OVER"

--------------------------------------------------
-- INTERNAL STATE
--------------------------------------------------

local last_event = ""
local last_crex_url = ""
local last_cricbuzz_url = ""

local match_started = false
local last_over = -1
local last_over_announced = false

--------------------------------------------------
-- FLAG SOURCES
--------------------------------------------------

local flag_names = {
    ["Batting Flag"] = true,
    ["Bowling Flag"] = true
}

--------------------------------------------------
-- PLAY VOICE
--------------------------------------------------

function play_voice(source_name)

    local source = obs.obs_get_source_by_name(source_name)

    if source ~= nil then
        obs.obs_source_media_restart(source)
        obs.obs_source_release(source)
    end

end

--------------------------------------------------
-- TRIM
--------------------------------------------------

local function trim(s)
    return (s and s:gsub("^%s+", ""):gsub("%s+$", "")) or ""
end

--------------------------------------------------
-- JSON VALUE READER
--------------------------------------------------

local function json_string(content,key)

    local pattern = '"'..key..'":%s*"([^"]+)"'
    return string.match(content,pattern)

end

local function json_number(content,key)

    local pattern = '"'..key..'":%s*(%d+)'
    local v = string.match(content,pattern)

    if v then return tonumber(v) end

    return nil

end

--------------------------------------------------
-- SCORE FILE READER
--------------------------------------------------

function read_score_file()

    if SCORE_FILE_PATH == "" then return nil end

    local f = io.open(SCORE_FILE_PATH,"r")
    if not f then return nil end

    local content = f:read("*all")
    f:close()

    local data = {}

    data.score = json_number(content,"score")
    data.wickets = json_number(content,"wickets")
    data.over = json_number(content,"over")
    data.ball = json_number(content,"ball")
    data.event = json_string(content,"event")

    return data

end

--------------------------------------------------
-- EVENT VOICE SYSTEM
--------------------------------------------------

function handle_event(event)

    if event == last_event then return end
    last_event = event

    if event == "DOT" then
        play_voice(VOICE_DOT)

    elseif event == "SINGLE" then
        play_voice(VOICE_SINGLE)

    elseif event == "DOUBLE" then
        play_voice(VOICE_DOUBLE)

    elseif event == "TRIPLE" then
        play_voice(VOICE_TRIPLE)

    elseif event == "FOUR" then
        play_voice(VOICE_FOUR)

    elseif event == "SIX" then
        play_voice(VOICE_SIX)

    elseif event == "WICKET" then
        play_voice(VOICE_WICKET)

    elseif event == "OVER_COMPLETE" then
        play_voice(VOICE_OVER)

    elseif event == "WIDE" then
        play_voice(VOICE_WIDE)

    elseif event == "NO_BALL" then
        play_voice(VOICE_NO_BALL)

    elseif event == "FREE_HIT" then
        play_voice(VOICE_FREE_HIT)

    elseif event == "BYE" then
        play_voice(VOICE_BYE)

    elseif event == "LEG_BYE" then
        play_voice(VOICE_LEG_BYE)

    elseif event == "MATCH_RESULT" then
        play_voice(VOICE_MATCH_END)

    end

end

--------------------------------------------------
-- MATCH PROCESS
--------------------------------------------------

function process_match()

    local data = read_score_file()
    if data == nil then return end

    local score = data.score or 0
    local wickets = data.wickets or 0
    local over = data.over or 0
    local ball = data.ball or 0
    local event = data.event or ""

    --------------------------------------------------
    -- MATCH START
    --------------------------------------------------

    if not match_started and over == 0 and ball == 1 then
        match_started = true
        play_voice(VOICE_WELCOME)
    end

    --------------------------------------------------
    -- EVENT HANDLER
    --------------------------------------------------

    handle_event(event)

    --------------------------------------------------
    -- LAST OVER
    --------------------------------------------------

    if over == 19 and not last_over_announced then
        play_voice(VOICE_LAST_OVER)
        last_over_announced = true
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
-- READ LINK FILE
--------------------------------------------------

function read_links_file()

    if LINKS_FILE_PATH == "" then return "","" end

    local f = io.open(LINKS_FILE_PATH,"r")
    if not f then return "","" end

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

    return new_crex,new_cricbuzz

end

--------------------------------------------------
-- UPDATE BROWSER SOURCES
--------------------------------------------------

function apply_links()

    local new_crex,new_cricbuzz = read_links_file()

    if new_crex == last_crex_url and new_cricbuzz == last_cricbuzz_url then
        return
    end

    last_crex_url = new_crex
    last_cricbuzz_url = new_cricbuzz

    local sources = obs.obs_enum_sources()

    for _,src in ipairs(sources) do

        if obs.obs_source_get_id(src) == "browser_source" then

            local settings = obs.obs_source_get_settings(src)
            local url = obs.obs_data_get_string(settings,"url")
            local name = obs.obs_source_get_name(src)

            if is_crex_url(url) then

                local target = new_crex

                if flag_names[name] then
                    target = new_crex:gsub("/live$","/info")
                end

                if url ~= target then
                    obs.obs_data_set_string(settings,"url",target)
                    obs.obs_source_update(src,settings)
                end

            elseif is_cricbuzz_url(url) then

                if url ~= new_cricbuzz then
                    obs.obs_data_set_string(settings,"url",new_cricbuzz)
                    obs.obs_source_update(src,settings)
                end

            end

            obs.obs_data_release(settings)

        end

    end

    obs.source_list_release(sources)

end

--------------------------------------------------
-- TIMERS
--------------------------------------------------

function score_timer()
    process_match()
end

function link_timer()
    apply_links()
end

--------------------------------------------------
-- OBS UI
--------------------------------------------------

function script_description()

    return "CREX + Cricbuzz Auto URL Updater + Advanced Cricket AI Voice Automation"

end

function script_properties()

    local props = obs.obs_properties_create()

    obs.obs_properties_add_path(
        props,
        "links",
        "score_links.txt",
        obs.OBS_PATH_FILE,
        "*.txt",
        nil
    )

    obs.obs_properties_add_path(
        props,
        "score",
        "score.json",
        obs.OBS_PATH_FILE,
        "*.json",
        nil
    )

    return props

end

function script_update(settings)

    LINKS_FILE_PATH = obs.obs_data_get_string(settings,"links")
    SCORE_FILE_PATH = obs.obs_data_get_string(settings,"score")

end

--------------------------------------------------
-- SCRIPT LOAD
--------------------------------------------------

function script_load(settings)

    obs.timer_add(score_timer,1000)
    obs.timer_add(link_timer,2000)

end

function script_unload()

    obs.timer_remove(score_timer)
    obs.timer_remove(link_timer)

end