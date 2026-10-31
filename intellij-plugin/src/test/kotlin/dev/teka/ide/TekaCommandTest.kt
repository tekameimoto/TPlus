package dev.teka.ide

import com.google.gson.Gson
import java.io.File
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir

class TekaCommandTest {
    @TempDir
    lateinit var base: File

    private fun installation(version: String, manifest: File): List<String> {
        val python = File(base, "Python with spaces/python.exe").apply {
            parentFile.mkdirs()
            writeText("test fixture")
        }
        val launcher = File(base, "$version/launcher.py").apply {
            parentFile.mkdirs()
            writeText("test fixture")
        }
        manifest.parentFile.mkdirs()
        manifest.writeText(Gson().toJson(mapOf("python" to python.path, "launcher" to launcher.path)))
        return listOf(python.path, launcher.path)
    }

    @Test
    fun `reinstallation selects new version while older version remains`() {
        val legacy = File(base, "0.9.0/launcher.json")
        val old = installation("0.9.0", legacy)
        assertEquals(old, TekaCommand.resolveWindows(base, null))
        val current = installation("0.9.1", File(base, "bin/launcher.json"))
        assertEquals(current, TekaCommand.resolveWindows(base, null))
        assertEquals(old, TekaCommand.resolveWindows(base, legacy.parentFile))
    }

    @Test
    fun `malformed manifest falls back without throwing`() {
        val old = installation("0.9.0", File(base, "0.9.0/launcher.json"))
        File(base, "bin/launcher.json").apply { parentFile.mkdirs(); writeText("[]") }
        assertEquals(old, TekaCommand.resolveWindows(base, null))
    }

    @Test
    fun `missing launcher is not offered as a working compiler`() {
        val command = installation("0.9.1", File(base, "bin/launcher.json"))
        File(command[1]).delete()
        assertNull(TekaCommand.resolveWindows(base, null))
    }
}
