"""Typed, native standard-library modules used by the TekaLang compiler.

Only modules explicitly listed here are supported. Importing one never
executes Python code at runtime. Methods map to C++17 native helpers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import NamedTuple


class NativeFunction(NamedTuple):
    args: tuple[str, ...]
    returns: str
    cpp: str


@dataclass(frozen=True)
class NativeModule:
    functions: dict[str, NativeFunction]
    constants: dict[str, tuple[str, str]]
    includes: tuple[str, ...]
    helpers: str = ""
    requires_graphics: bool = False


RANDOM_CPP = r"""
inline std::mt19937& tk_random_engine() {
    static thread_local std::mt19937 engine(std::random_device{}());
    return engine;
}
inline long long tk_random_randint(long long start, long long stop) {
    if (start > stop) throw std::invalid_argument("random.randint requires start <= stop");
    std::uniform_int_distribution<long long> dist(start, stop);
    return dist(tk_random_engine());
}
inline double tk_random_uniform(double start, double stop) {
    if (!std::isfinite(start) || !std::isfinite(stop) || start > stop)
        throw std::invalid_argument("random.uniform requires finite start <= stop");
    std::uniform_real_distribution<double> dist(start, stop);
    return dist(tk_random_engine());
}
inline double tk_random_random() {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    return dist(tk_random_engine());
}
inline long long tk_random_randrange(long long stop) {
    if (stop <= 0) throw std::invalid_argument("random.randrange requires stop > 0");
    std::uniform_int_distribution<long long> dist(0, stop - 1);
    return dist(tk_random_engine());
}
"""

MATH_CPP = r"""
inline double tk_math_sqrt(double value) {
    if (value < 0) throw std::domain_error("math.sqrt requires a nonnegative number");
    return std::sqrt(value);
}
"""

MODULES: dict[str, NativeModule] = {
    "random": NativeModule(
        functions={
            "randint": NativeFunction(("int", "int"), "int", "tk_random_randint"),
            "random": NativeFunction((), "float", "tk_random_random"),
            "randrange": NativeFunction(("int",), "int", "tk_random_randrange"),
            "uniform": NativeFunction(("float", "float"), "float", "tk_random_uniform"),
        },
        constants={},
        includes=("<random>", "<stdexcept>", "<cmath>"),
        helpers=RANDOM_CPP,
    ),
    "math": NativeModule(
        functions={
            "sqrt": NativeFunction(("float",), "float", "tk_math_sqrt"),
            "sin": NativeFunction(("float",), "float", "std::sin"),
            "cos": NativeFunction(("float",), "float", "std::cos"),
            "tan": NativeFunction(("float",), "float", "std::tan"),
            "floor": NativeFunction(("float",), "int", "tk_math_floor"),
            "ceil": NativeFunction(("float",), "int", "tk_math_ceil"),
            "pow": NativeFunction(("float", "float"), "float", "std::pow"),
        },
        constants={"pi": ("float", "3.14159265358979323846"),
                   "e": ("float", "2.71828182845904523536")},
        includes=("<cmath>", "<stdexcept>"),
        helpers=MATH_CPP + r"""
inline long long tk_math_floor(double x) {
    return static_cast<long long>(std::floor(x));
}
inline long long tk_math_ceil(double x) {
    return static_cast<long long>(std::ceil(x));
}
""",
    ),
}


TIME_CPP = r"""
inline void tk_time_sleep(double seconds) {
    if (!std::isfinite(seconds) || seconds < 0 || seconds > 86400)
        throw std::invalid_argument("time.sleep requires seconds from 0 to 86400");
    std::this_thread::sleep_for(std::chrono::duration<double>(seconds));
}
inline double tk_time_now() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}
inline double tk_time_monotonic() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}
"""

TEXT_CPP = r"""
inline std::string tk_text_upper(std::string s) {
    for (char& c : s) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    return s;
}
inline std::string tk_text_lower(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}
inline bool tk_text_contains(const std::string& s, const std::string& piece) {
    return s.find(piece) != std::string::npos;
}
inline bool tk_text_starts_with(const std::string& s, const std::string& prefix) {
    return s.size() >= prefix.size() && s.compare(0, prefix.size(), prefix) == 0;
}
inline bool tk_text_ends_with(const std::string& s, const std::string& suffix) {
    return s.size() >= suffix.size() && s.compare(s.size()-suffix.size(),suffix.size(),suffix)==0;
}
inline std::string tk_text_replace(std::string s,const std::string& old,const std::string& replacement) {
    if (old.empty()) throw std::invalid_argument("text.replace requires a nonempty search string");
    std::size_t offset=0;
    while ((offset=s.find(old,offset))!=std::string::npos) {
        s.replace(offset,old.size(),replacement);
        offset+=replacement.size();
    }
    return s;
}
"""

FILES_CPP = r"""
inline std::string tk_files_read(const std::string& path) {
    std::ifstream stream(path,std::ios::binary);
    if (!stream) throw std::runtime_error("files.read: cannot open " + path);
    std::ostringstream text;
    text << stream.rdbuf();
    if (!stream.eof() && stream.fail()) throw std::runtime_error("files.read: I/O error " + path);
    return text.str();
}
inline void tk_files_write(const std::string& path,const std::string& text) {
    std::ofstream stream(path,std::ios::binary|std::ios::trunc);
    if (!stream || !(stream << text)) throw std::runtime_error("files.write: failed " + path);
}
inline void tk_files_append(const std::string& path,const std::string& text) {
    std::ofstream stream(path,std::ios::binary|std::ios::app);
    if (!stream || !(stream << text)) throw std::runtime_error("files.append: failed " + path);
}
inline bool tk_files_exists(const std::string& path) {
    std::error_code err;
    bool value=std::filesystem::exists(path,err);
    if (err) throw std::runtime_error("files.exists: " + err.message());
    return value;
}
"""

JSON_CPP = r"""
inline std::string tk_json_quote(const std::string& s) {
    static const char* hex = "0123456789abcdef";
    std::string out = "\"";
    for (unsigned char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            default:
                if (c < 0x20) {
                    out += "\\u00";
                    out += hex[c >> 4];
                    out += hex[c & 15];
                } else out.push_back(static_cast<char>(c));
        }
    }
    return out + "\"";
}
"""

SYSTEM_CPP = r"""
inline std::string tk_system_platform() {
#if defined(__APPLE__)
    return "macos";
#elif defined(_WIN32)
    return "windows";
#elif defined(__linux__)
    return "linux";
#else
    return "unknown";
#endif
}
inline std::string tk_system_getenv(const std::string& key) {
    const char* value = std::getenv(key.c_str());
    return value ? std::string(value) : std::string();
}
"""

MODULES.update({
    "time": NativeModule(
        functions={
            "sleep": NativeFunction(("float",), "void", "tk_time_sleep"),
            "wait": NativeFunction(("float",), "void", "tk_time_sleep"),
            "now": NativeFunction((), "float", "tk_time_now"),
            "monotonic": NativeFunction((), "float", "tk_time_monotonic"),
        },
        constants={},
        includes=("<chrono>", "<thread>", "<cmath>", "<stdexcept>"),
        helpers=TIME_CPP,
    ),
    "text": NativeModule(
        functions={
            "upper": NativeFunction(("string",), "string", "tk_text_upper"),
            "lower": NativeFunction(("string",), "string", "tk_text_lower"),
            "contains": NativeFunction(("string","string"), "bool", "tk_text_contains"),
            "starts_with": NativeFunction(("string","string"), "bool", "tk_text_starts_with"),
            "ends_with": NativeFunction(("string","string"), "bool", "tk_text_ends_with"),
            "replace": NativeFunction(("string","string","string"), "string", "tk_text_replace"),
        },
        constants={},
        includes=("<cctype>", "<stdexcept>", "<string>"),
        helpers=TEXT_CPP,
    ),
    "files": NativeModule(
        functions={
            "read": NativeFunction(("string",), "string", "tk_files_read"),
            "write": NativeFunction(("string","string"), "void", "tk_files_write"),
            "append": NativeFunction(("string","string"), "void", "tk_files_append"),
            "exists": NativeFunction(("string",), "bool", "tk_files_exists"),
        },
        constants={},
        includes=("<fstream>", "<sstream>", "<filesystem>", "<system_error>", "<stdexcept>"),
        helpers=FILES_CPP,
    ),
    "json": NativeModule(
        functions={
            "quote": NativeFunction(("string",), "string", "tk_json_quote"),
        },
        constants={},
        includes=("<string>",),
        helpers=JSON_CPP,
    ),
    "system": NativeModule(
        functions={
            "platform": NativeFunction((), "string", "tk_system_platform"),
            "getenv": NativeFunction(("string",), "string", "tk_system_getenv"),
        },
        constants={},
        includes=("<cstdlib>", "<string>"),
        helpers=SYSTEM_CPP,
    ),
    "graphics": NativeModule(
        functions={
            "open": NativeFunction(("string","int","int"), "void", "tk_game_open"),
            "close": NativeFunction((), "void", "tk_game_close"),
            "running": NativeFunction((), "bool", "tk_game_running"),
            "begin": NativeFunction((), "void", "tk_game_begin"),
            "end": NativeFunction((), "void", "tk_game_end"),
            "clear": NativeFunction(("int","int","int"), "void", "tk_game_clear"),
            "rect": NativeFunction(("float","float","float","float","int","int","int"), "void", "tk_game_rect"),
            "circle": NativeFunction(("float","float","float","int","int","int"), "void", "tk_game_circle"),
            "line": NativeFunction(("float","float","float","float","float","int","int","int"), "void", "tk_game_line"),
            "triangle": NativeFunction(("float","float","float","float","float","float","int","int","int"), "void", "tk_game_triangle"),
            "text": NativeFunction(("string","float","float","int","int","int","int"), "void", "tk_game_text"),
            "key": NativeFunction(("string",), "bool", "tk_game_key"),
            "pressed": NativeFunction(("string",), "bool", "tk_game_pressed"),
            "dt": NativeFunction((), "float", "tk_game_dt"),
            "time": NativeFunction((), "float", "tk_game_time"),
            "rand": NativeFunction(("int","int"), "int", "tk_game_rand"),
            "mouse_x": NativeFunction((), "int", "tk_game_mouse_x"),
            "mouse_y": NativeFunction((), "int", "tk_game_mouse_y"),
            "fps": NativeFunction((), "int", "tk_game_fps"),
        },
        constants={},
        includes=(),
        requires_graphics=True,
    ),
})



def known_modules() -> str:
    return ", ".join(sorted(MODULES))