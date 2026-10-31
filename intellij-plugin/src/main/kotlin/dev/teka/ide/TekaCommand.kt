package dev.teka.ide

import com.google.gson.JsonParser
import java.io.File

/** Resolve the installed compiler without depending on the IDE's shell PATH. */
object TekaCommand {
    internal fun resolveWindows(base: File, explicitHome: File?): List<String>? {
        // Preserve compatibility with the published v0.9.0 installer.
        val manifests = if (explicitHome != null) listOf(File(explicitHome, "launcher.json"))
            else listOf(File(base, "bin/launcher.json"), File(base, "0.9.0/launcher.json"))
        for (manifest in manifests) {
            try {
                if (!manifest.isFile) continue
                val info = JsonParser.parseString(manifest.readText()).asJsonObject
                val python = info.get("python").asString
                val launcher = info.get("launcher").asString
                if (File(python).isFile && File(launcher).isFile) return listOf(python, launcher)
            } catch (_: Exception) {
                // Try the legacy installation when a manifest is incomplete.
            }
        }
        return null
    }

    fun resolve(root: File? = null): List<String>? {
        val windows = System.getProperty("os.name").startsWith("Windows", ignoreCase = true)
        if (windows) {
            val local = System.getenv("LOCALAPPDATA")
                ?: File(System.getProperty("user.home"), "AppData/Local").path
            val home = System.getenv("TEKA_HOME")?.let(::File)
            resolveWindows(File(local, "TPlus"), home)?.let { return it }
        } else {
            val launcher = File(System.getProperty("user.home"), ".local/bin/teka")
            if (launcher.isFile) return listOf(launcher.absolutePath)
        }
        val compiler = root?.let { File(it, "teka.py") }
        return if (compiler?.isFile == true)
            listOf(if (windows) "python" else "python3", compiler.absolutePath) else null
    }
}
