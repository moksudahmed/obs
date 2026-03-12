-- OBS CREX + CRICBUZZ AUTO UPDATE + AI COMMENTARY
local obs = obslua

--------------------------------------------------
-- CONFIGURATION
--------------------------------------------------
local LINKS_FILE_PATH = ""
local SCORE_FILE_PATH = "C:/cricket_voices/score.txt"
local audio_source_name = "AI Commentary"

--------------------------------------------------
-- AUDIO FILES
--------------------------------------------------
local audio_files = {
    six = "C:/cricket_voices/six.wav",
    four = "C:/cricket_voices/four.wav",
    wicket = "C:/cricket_voices/wicket.wav",
    over_complete = "C:/cricket_voices/over_complete.wav",
    super_over = "C:/cricket_voices/super_over.wav"
}

--------------------------------------------------
-- SCORE STATE
--------------------------------------------------
local last_runs = 0
local last_wickets = 0

--------------------------------------------------
-- URL STATE
--------------------------------------------------
local last_crex_url = ""
local last_cricbuzz_url = ""
local flag_names = {
    ["Batting Flag"] = true,
    ["Bowling Flag"] = true
}

--------------------------------------------------
-- INITIALIZE SCORE FILE
--------------------------------------------------
local function initialize_score_file()
    local f = io.open(SCORE_FILE_PATH, "r")
    if not f then
        f = io.open(SCORE_FILE_PATH, "w")
        if f then
            f:write("0/0")
            f:close()
            obs.script_log(obs.LOG_INFO, "score.txt initialized with 0/0")
        else
            obs.script_log(obs.LOG_WARNING, "Failed to create score.txt")
        end
    else
        f:close()
    end
end

--------------------------------------------------
-- PLAY AUDIO
--------------------------------------------------
local function play_audio(path)
    local source = obs.obs_get_source_by_name(audio_source_name)
    if not source then
        obs.script_log(obs.LOG_WARNING, "AI Commentary source not found")
        return
    end
    local settings = obs.obs_source_get_settings(source)
    obs.obs_data_set_string(settings, "local_file", path)
    obs.obs_source_update(source, settings)
    obs.obs_source_media_restart(source)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)
end

--------------------------------------------------
-- SCORE DETECTION
--------------------------------------------------
local function read_score()
    local f = io.open(SCORE_FILE_PATH, "r")
    if not f then
        obs.script_log(obs.LOG_WARNING,"Score file not found: "..SCORE_FILE_PATH)
        return
    end

    local text = f:read("*a")
    f:close()

    if not text or text == "" then return end

    local runs, wk = text:match("(%d+)%s*/%s*(%d+)")
    if not runs then return end
    runs = tonumber(runs)
    wk = tonumber(wk)

    -- Only trigger audio if changed
    if runs ~= last_runs then
        local diff = runs - last_runs
        if diff == 4 then play_audio(audio_files.four)
        elseif diff == 6 then play_audio(audio_files.six) end
    end

    if wk > last_wickets then
        play_audio(audio_files.wicket)
    end

    last_runs = runs
    last_wickets = wk
end
--------------------------------------------------
-- STRING UTILITY
--------------------------------------------------
local function trim(s)
    return (s and s:gsub("^%s+",""):gsub("%s+$","")) or ""
end

local function is_crex_url(u) return u and u:match("crex%.com") end
local function is_cricbuzz_url(u) return u and u:match("cricbuzz%.com") end

--------------------------------------------------
-- READ LINKS FILE
--------------------------------------------------
local function read_links_file()
    if LINKS_FILE_PATH == "" then return "","" end
    local f = io.open(LINKS_FILE_PATH,"r")
    if not f then
        obs.script_log(obs.LOG_WARNING,"score_links.txt not found")
        return "",""
    end

    local new_crex, new_cb = "",""
    for line in f:lines() do
        local l = trim(line)
        if new_crex == "" and is_crex_url(l) then new_crex = l
        elseif new_cb == "" and is_cricbuzz_url(l) then new_cb = l
        end
    end
    f:close()
    return new_crex,new_cb
end

--------------------------------------------------
-- APPLY URL CHANGES
--------------------------------------------------
local function apply_all()
    local new_crex,new_cb = read_links_file()
    if new_crex == "" and new_cb == "" then return end

    local sources = obs.obs_enum_sources()
    if not sources then return end

    for _,src in ipairs(sources) do
        if obs.obs_source_get_id(src) == "browser_source" then
            local settings = obs.obs_source_get_settings(src)
            local url = obs.obs_data_get_string(settings,"url")
            local name = obs.obs_source_get_name(src)

            if is_crex_url(url) and new_crex ~= "" then
                local target = flag_names[name] and new_crex:gsub("/live","/info") or new_crex
                if url ~= target then
                    obs.obs_data_set_string(settings,"url",target)
                    obs.obs_source_update(src,settings)
                    obs.script_log(obs.LOG_INFO,"CREX Updated → "..name)
                end
            elseif is_cricbuzz_url(url) and new_cb ~= "" then
                if url ~= new_cb then
                    obs.obs_data_set_string(settings,"url",new_cb)
                    obs.obs_source_update(src,settings)
                    obs.script_log(obs.LOG_INFO,"Cricbuzz Updated → "..name)
                end
            end
            obs.obs_data_release(settings)
        end
    end
    obs.source_list_release(sources)
end

--------------------------------------------------
-- FILE WATCHERS
--------------------------------------------------
local function check_links() apply_all() end
local function check_score() read_score() end

--------------------------------------------------
-- SCRIPT DESCRIPTION
--------------------------------------------------
function script_description()
    return "Auto update CREX + Cricbuzz Browser Sources and AI Voice Commentary"
end

--------------------------------------------------
-- SCRIPT PROPERTIES
--------------------------------------------------
function script_properties()
    local props = obs.obs_properties_create()
    obs.obs_properties_add_path(
        props,
        "links_path",
        "Score Links File (score_links.txt)",
        obs.OBS_PATH_FILE,
        "Text files (*.txt);;All files (*.*)",
        nil
    )
    obs.obs_properties_add_button(
        props,
        "apply_btn",
        "Apply Now",
        apply_clicked
    )
    return props
end

function script_update(settings)
    LINKS_FILE_PATH = obs.obs_data_get_string(settings,"links_path")
end

--------------------------------------------------
-- SCRIPT LOAD / UNLOAD
--------------------------------------------------
function script_load(settings)
    initialize_score_file()          -- <-- create score.txt if missing
    last_crex_url,last_cricbuzz_url = read_links_file()
    apply_all()
    obs.timer_add(check_links,2000)
    obs.timer_add(check_score,1000) -- auto check every second
end

function script_unload()
    obs.timer_remove(check_links)
    obs.timer_remove(check_score)
end

--------------------------------------------------
-- APPLY BUTTON
--------------------------------------------------
function apply_clicked(props, prop)
    apply_all()
    return true
end