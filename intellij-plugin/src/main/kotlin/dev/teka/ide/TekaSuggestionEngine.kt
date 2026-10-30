package dev.teka.ide

/**
 * Lightweight, local completion engine for real TekaLang source.
 *
 * No network or AI model is needed: this uses functions, variables, parameters,
 * keywords and basic language snippets actually supported by the compiler.
 * This is deliberately conservative; it never invents members or imports.
 */
data class TekaCandidate(
    val word: String,
    val insertion: String,
    val label: String,
    val kind: String,
    val priority: Double,
    val caretMarker: Char = '¦'
) {
    fun insertedText(): String = insertion.replace(caretMarker.toString(), "")
    fun caretIndex(): Int = insertion.indexOf(caretMarker).takeIf { it >= 0 } ?: insertedText().length
}

object TekaSuggestionEngine {
    private val identifier = Regex("[A-Za-z_][A-Za-z0-9_]*$")
    private val functionDefinition = Regex(
        """(?m)^[ \t]*(?:def|fn)[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(([^)\n]*)\)(?:[ \t]*->[ \t]*([A-Za-z_][A-Za-z0-9_<>]*))?"""
    )
    private val declaration = Regex("""(?m)^[ \t]*(?:var|let)[ \t]+([A-Za-z_][A-Za-z0-9_]*)""")
    private val inferred = Regex("""(?m)^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=(?!=)""")
    private val parameter = Regex("""\b([A-Za-z_][A-Za-z0-9_]*)[ \t]*:[ \t]*(?:list<[^>]+>|int|float|bool|string)""")
    private val keywordNames = listOf(
        "def", "fn", "return", "if", "elif", "else", "while", "for", "in",
        "break", "continue", "pass", "and", "or", "not",
        "say", "ask", "repeat", "times", "otherwise", "stop", "skip", "is", "below", "above",
        "let", "var", "True", "False", "true", "false",
        "int", "float", "bool", "string", "list", "void", "str", "class", "import", "as"
    )
    private val reserved = keywordNames.toSet() + setOf("print", "range", "len", "push", "pop", "input")

    private fun template(name: String, body: String, description: String, priority: Double = 95.0) =
        TekaCandidate(name, body, description, "snippet", priority)

    private val builtins = listOf(
        TekaCandidate("print", "print(¦)", "print(value)", "built-in", 87.0),
        TekaCandidate("say", "say ¦", "say value — display text", "built-in", 92.0),
        TekaCandidate("ask", "ask(\u0027¦\u0027)", "ask(prompt) — read input", "built-in", 90.0),
        TekaCandidate("range", "range(¦)", "range(start, end)", "built-in", 87.0),
        TekaCandidate("len", "len(¦)", "len(value)", "built-in", 85.0),
        TekaCandidate("push", "push(¦)", "push(list, value)", "built-in", 85.0),
        TekaCandidate("pop", "pop(¦)", "pop(list)", "built-in", 85.0),
        TekaCandidate("str", "str(¦)", "str(value)", "built-in", 85.0),
        TekaCandidate("input", "input('¦')", "input(prompt) -> string", "built-in", 86.0),
        TekaCandidate("int", "int(¦)", "int(value) -> int", "built-in", 85.0),
        TekaCandidate("float", "float(¦)", "float(value) -> float", "built-in", 85.0),
        TekaCandidate("bool", "bool(¦)", "bool(value) -> bool", "built-in", 85.0),
        TekaCandidate("game_open", "game_open('My Game', ¦960, 640)", "open native window", "graphics", 98.0),
        TekaCandidate("game_close", "game_close()", "close game window", "graphics", 92.0),
        TekaCandidate("game_running", "game_running()", "true while window is open", "graphics", 95.0),
        TekaCandidate("game_begin", "game_begin()", "begin drawing frame", "graphics", 95.0),
        TekaCandidate("game_end", "game_end()", "finish drawing frame", "graphics", 95.0),
        TekaCandidate("game_clear", "game_clear(¦8, 12, 22)", "clear RGB background", "graphics", 95.0),
        TekaCandidate("game_rect", "game_rect(¦10, 10, 40, 40, 50, 200, 250)", "draw RGB rectangle", "graphics", 95.0),
        TekaCandidate("game_circle", "game_circle(¦120, 100, 25, 200, 100, 255)", "draw RGB circle", "graphics", 95.0),
        TekaCandidate("game_line", "game_line(¦0, 0, 200, 200, 2, 150, 200, 250)", "draw line", "graphics", 94.0),
        TekaCandidate("game_triangle", "game_triangle(¦100, 40, 80, 90, 120, 90, 120, 180, 255)", "draw triangle", "graphics", 94.0),
        TekaCandidate("game_text", "game_text('¦hello', 20, 20, 24, 255, 255, 255)", "draw text", "graphics", 95.0),
        TekaCandidate("game_key", "game_key('¦SPACE')", "is key down?", "graphics", 95.0),
        TekaCandidate("game_pressed", "game_pressed('¦ENTER')", "was key just pressed?", "graphics", 94.0),
        TekaCandidate("game_dt", "game_dt()", "time since previous frame", "graphics", 94.0),
        TekaCandidate("game_time", "game_time()", "elapsed game time", "graphics", 94.0),
        TekaCandidate("game_rand", "game_rand(¦0, 100)", "native random integer", "graphics", 94.0),
        TekaCandidate("game_fps", "game_fps()", "frames per second", "graphics", 91.0),
        TekaCandidate("game_mouse_x", "game_mouse_x()", "mouse x coordinate", "graphics", 91.0),
        TekaCandidate("game_mouse_y", "game_mouse_y()", "mouse y coordinate", "graphics", 91.0)
    )

    private val snippets = listOf(
        template("repeat", "repeat ¦5 times:\n\tsay 'hello'", "repeat N times:"),
        template("otherwise", "otherwise:\n\t¦pass", "otherwise:"),
        template("say", "say ¦'hello'", "say value"),
        template("ask", "ask('¦question?')", "ask(prompt)"),
        template("for", "for i in range(¦5):\n\tprint(i)", "for i in range(5):"),
        template("if", "if ¦True:\n\tprint('ready')", "if condition:"),
        template("elif", "elif ¦True:\n\tprint('next')", "elif condition:"),
        template("else", "else:\n\t¦pass", "else:"),
        template("while", "while ¦False:\n\tpass", "while condition:"),
        template("def", "def ¦my_function(x: int) -> int:\n\treturn x", "def function(x: int) -> int:"),
        template("fn", "fn ¦my_function(x: int) -> int {\n\treturn x;\n}", "fn function(x: int) -> int { }"),
        template("class", "class ¦MyClass:\n\tdef __init__(self):\n\t\tpass", "class MyClass:"),
        template("import", "import teka.¦math", "import T+ standard library"),
        template("return", "return ¦", "return value"),
        template("var", "var ¦value = 0", "var value = 0", 90.0),
        template("let", "let ¦value = 0", "let value = 0", 90.0)
    )

    data class Context(val typed: String, val textBeforeWord: String, val indent: String, val line: String)

    fun context(source: String, position: Int): Context? {
        if (position !in 0..source.length) return null
        val start = if (position == 0) 0 else source.lastIndexOf('\n', startIndex = position - 1) + 1
        val line = source.substring(start, position)
        if (inStringOrComment(line)) return null
        val typed = identifier.find(line)?.value ?: ""
        val before = line.dropLast(typed.length)
        val indent = line.takeWhile { it == ' ' || it == '\t' }
        return Context(typed, before, indent, line)
    }

    private fun inStringOrComment(line: String): Boolean {
        var string: Char? = null
        var escaped = false
        var i = 0
        while (i < line.length) {
            val c = line[i]
            if (string != null) {
                if (c == string && !escaped) string = null
                if (c == '\\' && !escaped) escaped = true else escaped = false
            } else {
                if (c == '"' || c == '\'') string = c
                else if (c == '#' || (c == '/' && i + 1 < line.length && line[i + 1] == '/')) return true
            }
            i++
        }
        return string != null
    }

    private fun isDefinitionContext(ctx: Context): Boolean {
        val before = ctx.textBeforeWord.trimEnd()
        return before.endsWith("def") || before.endsWith("fn") ||
            before.endsWith("var") || before.endsWith("let") ||
            before.matches(Regex(".*\\b(?:def|fn)\\s+"))
    }

    fun candidates(source: String, position: Int): List<TekaCandidate> {
        val ctx = context(source, position) ?: return emptyList()
        val members = TekaMemberCompletion.candidateList(source, position)
        if (members != null) return members
        if (isDefinitionContext(ctx)) return emptyList() // don't overwrite identifiers being declared

        val functionParams = LinkedHashSet<String>()
        val funcs = LinkedHashMap<String, TekaCandidate>()
        for (m in functionDefinition.findAll(source)) {
            val name = m.groupValues[1]
            val args = m.groupValues[2]
            val returnType = m.groupValues[3].ifBlank { "void" }
            if (name in reserved) continue
            val params = parameter.findAll(args).map { it.groupValues[1] }.toList()
            if (m.range.first < position) functionParams.addAll(params)
            val mark = if (params.isNotEmpty()) "¦" else ""
            val insertion = "$name($mark)"
            funcs[name] = TekaCandidate(name, insertion, "$name($args) -> $returnType", "function", 105.0)
        }

        val seen = LinkedHashSet<String>()
        seen.addAll(functionParams)
        val preceding = source.take(position)
        declaration.findAll(preceding).forEach { seen.add(it.groupValues[1]) }
        inferred.findAll(preceding).forEach { seen.add(it.groupValues[1]) }
        // Loop variables are immutable within the loop, but useful inside the body.
        Regex("""(?m)^[ \t]*for[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]+in\b""")
            .findAll(preceding).forEach { seen.add(it.groupValues[1]) }

        val vars = seen.filterNot { it in reserved || it == ctx.typed }
            .map { TekaCandidate(it, it, it, "variable", 115.0) }

        // Snippets should only be offered as standalone starts of a statement,
        // not in expressions, arguments, function annotations, or after other code.
        val beginningOfStatement = ctx.textBeforeWord.isBlank()
        val options = ArrayList<TekaCandidate>()
        options.addAll(vars)
        options.addAll(funcs.values)
        options.addAll(builtins)
        if (beginningOfStatement) options.addAll(snippets)
        options.addAll(keywordNames.map { name -> TekaCandidate(name, name, name, "keyword", 30.0) })

        val typed = ctx.typed
        return options.filter { candidate ->
            if (typed.isEmpty()) return@filter false // no intrusive popup at blank lines
            candidate.word.startsWith(typed, ignoreCase = true) &&
                candidate.word != typed || candidate.kind == "snippet" && candidate.word == typed
        }.distinctBy { it.kind to it.word }
            .sortedWith(compareByDescending<TekaCandidate> { it.priority }
                .thenBy { it.word.length }
                .thenBy { it.word })
            .take(45)
    }

    fun inlineSuffix(source: String, position: Int): String? {
        val ctx = context(source, position) ?: return null
        // Require 2+ letters to avoid noisy ghost text after each keystroke.
        if (ctx.typed.length < 2) {
            // A single i at the start of a statement can ghost-complete to if.
            if (ctx.typed == "i" && ctx.textBeforeWord.isBlank()) return "f"
            return null
        }
        val first = candidates(source, position).firstOrNull() ?: return null
        val completed = first.insertedText()
        if (!completed.startsWith(ctx.typed, ignoreCase = false)) return null
        val suffix = completed.drop(ctx.typed.length)
        if (suffix.isBlank() || suffix.length > 180) return null
        return suffix
    }
}