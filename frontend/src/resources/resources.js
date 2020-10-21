
import module daedalus

const platform_prefix = daedalus.platform.isAndroid ? "file:///android_asset/site/static/icon/" : "/static/icon/";

const svg_icon_names = [
    "album",
    "bolt",
    "create",
    "discard",
    "disc",
    "documents",
    "download",
    "edit",
    "equalizer",
    "externalmedia",
    "file",
    "folder",
    "genre",
    "logout",
    "media_error",
    "media_next",
    "media_pause",
    "media_play",
    "media_prev",
    "media_shuffle",
    "menu",
    "microphone",
    "more",
    "music_note",
    "new_folder",
    "note",
    "open",
    "playlist",
    "preview",
    "rename",
    "return",
    "save",
    "search",
    "search_generic",
    "select",
    "settings",
    "shuffle",
    "sort",
    "upload",
    "volume_0",
    "volume_1",
    "volume_2",
    "volume_4",
    "checkbox_unchecked",
    "checkbox_partial",
    "checkbox_download",
    "checkbox_checked",
    "checkbox_synced",
    "checkbox_not_synced",
    "plus",
    "minus",
];

export const svg = {};

svg_icon_names.forEach(name => {svg[name] = platform_prefix + name + ".svg"})

