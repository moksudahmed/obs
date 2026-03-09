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
local VOICE_FOUR = "AI_FOUR"
local VOICE_SIX = "AI_SIX"
local VOICE_WICKET = "AI_WICKET"
local VOICE_OVER = "AI_OVER"
local VOICE_LAST_OVER = "AI_LAST_OVER"
local VOICE_MATCH_END = "AI_MATCH_END"

--------------------------------------------------
-- INTERNAL STATE
--------------------------------------------------

local last_crex_url = ""
local last_cricbuzz_url = ""

local last_score = 0
local last_wickets = 0
local last_over = -1
local match_started = false
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
-- FILE UTILITIES
--------------------------------------------------

local function trim(s)
    return (s and s:gsub("^%s+", ""):gsub("%s+$", "")) or ""
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

    for key,value in string.gmatch(content,'"(%w+)":%s*(%d+)') do
        data[key] = tonumber(value)
    end

    return data
end

--------------------------------------------------
-- MATCH EVENT DETECTION
--------------------------------------------------

function process_match()

    local data = read_score_file()
    if data == nil then return end

    local score = data.score or 0
    local wickets = data.wickets or 0
    local over = data.over or 0
    local ball = data.ball or 0

    --------------------------------------------------
    -- MATCH START
    --------------------------------------------------

    if not match_started and over == 0 and ball == 1 then
        match_started = true
        play_voice(VOICE_WELCOME)
    end

    --------------------------------------------------
    -- FOUR
    --------------------------------------------------

    if score - last_score == 4 then
        play_voice(VOICE_FOUR)
    end

    --------------------------------------------------
    -- SIX
    --------------------------------------------------

    if score - last_score == 6 then
        play_voice(VOICE_SIX)
    end

    --------------------------------------------------
    -- WICKET
    --------------------------------------------------

    if wickets > last_wickets then
        play_voice(VOICE_WICKET)
    end

    --------------------------------------------------
    -- OVER COMPLETE
    --------------------------------------------------

    if over > last_over then
        play_voice(VOICE_OVER)
    end

    --------------------------------------------------
    -- LAST OVER
    --------------------------------------------------

    if over == 19 and not last_over_announced then
        play_voice(VOICE_LAST_OVER)
        last_over_announced = true
    end

    --------------------------------------------------
    -- MATCH END
    --------------------------------------------------

    if over >= 20 and ball == 6 then
        play_voice(VOICE_MATCH_END)
    end

    last_score = score
    last_wickets = wickets
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

    return "CREX + Cricbuzz Auto URL Updater + Cricket AI Voice Automation"

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