package dev.teka.ide

/** Conservative type/member completion for the currently supported TekaLang subset. */
object TekaMemberCompletion {
    private val access =
        Regex("""([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.([A-Za-z_]\w*)?$""")
    private val classHeader = Regex("""(?m)^class\s+([A-Za-z_]\w*)\s*:""")
    private val imports =
        Regex("""(?m)^[ \t]*import[ \t]+(teka\.)?(random|math|time|text|files|json|system|graphics)(?:[ \t]+as[ \t]+([A-Za-z_]\w*))?""")
    private val inferredCtor =
        Regex("""(?m)^[ \t]*(?:var[ \t]+|let[ \t]+)?([A-Za-z_]\w*)[ \t]*=[ \t]*([A-Za-z_]\w*)\(""")
    private val classField = Regex("""(?m)\bself\.([A-Za-z_]\w*)[ \t]*=[ \t]*([^\n#;]+)""")
    private val methodDefinition =
        Regex("""(?m)^[ \t]+def[ \t]+([A-Za-z_]\w*)[ \t]*\(([^)\n]*)\)""")

    private val standardModules = mapOf(
        "random" to listOf(
            TekaCandidate("randint", "randint(¦1, 100)", "randint(int, int) -> int", "module function", 110.0),
            TekaCandidate("random", "random()", "random() -> float", "module function", 105.0),
            TekaCandidate("randrange", "randrange(¦10)", "randrange(int) -> int", "module function", 105.0),
            TekaCandidate("uniform", "uniform(¦0.0, 1.0)", "uniform(float, float) -> float", "module function", 105.0)
        ),
        "math" to listOf(
            TekaCandidate("sqrt", "sqrt(¦144)", "sqrt(float) -> float", "module function", 110.0),
            TekaCandidate("sin", "sin(¦0.0)", "sin(float) -> float", "module function", 105.0),
            TekaCandidate("cos", "cos(¦0.0)", "cos(float) -> float", "module function", 105.0),
            TekaCandidate("tan", "tan(¦0.0)", "tan(float) -> float", "module function", 105.0),
            TekaCandidate("floor", "floor(¦1.2)", "floor(float) -> int", "module function", 105.0),
            TekaCandidate("ceil", "ceil(¦1.2)", "ceil(float) -> int", "module function", 105.0),
            TekaCandidate("pow", "pow(¦2.0, 3.0)", "pow(float, float) -> float", "module function", 105.0),
            TekaCandidate("pi", "pi", "pi: float", "constant", 112.0),
            TekaCandidate("e", "e", "e: float", "constant", 105.0)
        ),
        "time" to listOf("sleep", "wait", "now", "monotonic").map { name ->
            val args = if (name == "sleep" || name == "wait") "¦1.0" else ""
            TekaCandidate(name, "$name($args)", "$name() — native time", "module function", 105.0)
        },
        "text" to listOf("upper", "lower", "contains", "starts_with", "ends_with", "replace").map { name ->
            TekaCandidate(name, "$name(¦)", "$name — text utility", "module function", 105.0)
        },
        "files" to listOf("read", "write", "append", "exists").map { name ->
            TekaCandidate(name, "$name(¦)", "$name — file utility", "module function", 105.0)
        },
        "json" to listOf(
            TekaCandidate("quote", "quote(¦)", "quote(string) -> JSON string", "module function", 105.0)
        ),
        "system" to listOf(
            TekaCandidate("platform", "platform()", "platform() -> string", "module function", 105.0),
            TekaCandidate("getenv", "getenv(¦)", "getenv(key) -> string", "module function", 105.0)
        ),
        "graphics" to listOf("open", "close", "running", "begin", "end", "clear", "rect",
            "circle", "line", "triangle", "text", "key", "pressed", "dt", "time", "rand", "fps", "mouse_x", "mouse_y").map { name ->
            TekaCandidate(name, "$name(¦)", "$name — raylib graphics", "module function", 105.0)
        }
    )

    private data class Klass(
        val name: String,
        val fields: Map<String, String>,
        val methods: List<TekaCandidate>
    )

    private fun classes(source: String): Map<String, Klass> {
        val headers = classHeader.findAll(source).toList()
        val found = linkedMapOf<String, Klass>()
        headers.forEachIndexed { idx, item ->
            val begin = item.range.last + 1
            val end = if (idx + 1 < headers.size) headers[idx + 1].range.first else source.length
            val body = source.substring(begin, end)
            val fields = linkedMapOf<String, String>()
            for (field in classField.findAll(body)) {
                val name = field.groupValues[1]
                val rhs = field.groupValues[2].trim()
                val ctor = Regex("""^([A-Za-z_]\w*)\(""").find(rhs)
                fields[name] = ctor?.groupValues?.get(1) ?: ""
            }
            val methods = methodDefinition.findAll(body).mapNotNull { method ->
                val name = method.groupValues[1]
                if (name == "__init__") return@mapNotNull null
                val args = method.groupValues[2].split(',').map { it.trim() }
                    .filter { it.isNotBlank() && it != "self" }
                val inserted = if (args.isEmpty()) "$name()" else "$name(¦)"
                TekaCandidate(name, inserted, name + "(" + args.joinToString(", ") + ")",
                    "method", 115.0)
            }.toList()
            found[item.groupValues[1]] = Klass(item.groupValues[1], fields, methods)
        }
        return found
    }

    private fun currentClass(source: String, position: Int): String? {
        val prefix = source.take(position)
        val header = classHeader.findAll(prefix).lastOrNull() ?: return null
        val tail = prefix.substring(header.range.last + 1)
        if (Regex("""(?m)^(?![ \t]|$|#)\S""").containsMatchIn(tail)) return null
        return header.groupValues[1]
    }

    fun candidateList(source: String, position: Int): List<TekaCandidate>? {
        if (position !in 0..source.length) return null
        val prefix = source.take(position)
        val line = prefix.substringAfterLast('\n')
        val m = access.find(line) ?: return null
        val chain = m.groupValues[1].split('.')
        val partial = m.groupValues[2]
        val clsMap = classes(source)
        var receiverType = ""
        val first = chain.first()

        val importsSeen = imports.findAll(prefix).toList()
        val namespaceModules = importsSeen.filter {
            it.groupValues[1].isNotBlank() && it.groupValues[3].isBlank()
        }.map { it.groupValues[2] }.toSet()
        if (first == "teka") {
            if (chain.size == 1) {
                return namespaceModules.filter { it.startsWith(partial, ignoreCase = true) }
                    .map { TekaCandidate(it, it, "teka.$it", "module", 110.0) }
                    .sortedBy { it.word }
            }
            if (chain[1] !in namespaceModules) return emptyList()
            receiverType = "module:" + chain[1]
        } else {
            for (item in importsSeen) {
                val alias = item.groupValues[3].ifBlank {
                    if (item.groupValues[1].isNotBlank()) "" else item.groupValues[2]
                }
                if (first == alias && alias.isNotBlank()) receiverType = "module:" + item.groupValues[2]
            }
        }
        if (first == "self") {
            receiverType = currentClass(source, position) ?: ""
        } else if (receiverType.isBlank()) {
            inferredCtor.findAll(prefix).forEach { item ->
                if (item.groupValues[1] == first && item.groupValues[2] in clsMap)
                    receiverType = item.groupValues[2]
            }
        }
        val remaining = if (first == "teka") chain.drop(2) else chain.drop(1)
        for (piece in remaining) {
            val cls = clsMap[receiverType] ?: return emptyList()
            receiverType = cls.fields[piece] ?: return emptyList()
        }

        val found = if (receiverType.startsWith("module:")) {
            standardModules[receiverType.removePrefix("module:")] ?: emptyList()
        } else {
            val cls = clsMap[receiverType] ?: return emptyList()
            cls.fields.keys.map { field ->
                TekaCandidate(field, field, field, "field", 120.0)
            } + cls.methods
        }
        return found.filter { it.word.startsWith(partial, ignoreCase = true) }
            .sortedWith(compareByDescending<TekaCandidate> { it.priority }.thenBy { it.word })
            .take(40)
    }
}