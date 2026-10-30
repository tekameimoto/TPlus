package dev.teka.ide

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.intellij.notification.Notification
import com.intellij.notification.NotificationAction
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Invoked at IDE startup and from Tools -> Check for T+ Updates. */
object TekaUpdates {
    private val checkedOnce = AtomicBoolean(false)
    private const val GROUP = "TekaLang Updates"

    private fun command(vararg args: String): JsonObject {
        val launcher = TekaCommand.resolve() ?: throw IllegalStateException("T+ compiler is not installed")
        val process = ProcessBuilder(launcher + args)
            .redirectErrorStream(true)
            .start()
        try {
            if (!process.waitFor(12, TimeUnit.SECONDS)) {
                process.destroyForcibly()
                throw IllegalStateException("Update check timed out")
            }
            val output = process.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            return JsonParser.parseString(output).asJsonObject
        } finally {
            process.destroy()
        }
    }

    private fun notice(project: Project, title: String, text: String, warning: Boolean = false): Notification {
        return Notification(GROUP, title, text, if (warning) NotificationType.WARNING else NotificationType.INFORMATION)
    }

    fun check(project: Project, interactive: Boolean) {
        ApplicationManager.getApplication().executeOnPooledThread {
            try {
                val response = command("update", "check", "--json")
                if (response.get("ok")?.asBoolean != true) {
                    if (interactive) {
                        val error = response.get("error")?.asString ?: "Unknown release-feed error"
                        notice(project, "T+ update check failed", error, true).notify(project)
                    }
                    return@executeOnPooledThread
                }
                val latest = response.get("latest")?.asString ?: "unknown"
                val available = response.get("available")?.asBoolean == true
                if (available) {
                    val notes = response.get("notes")?.asString ?: ""
                    val notification = notice(project, "T+ $latest is available",
                        "A new T+ compiler and IntelliJ plugin are available. $notes")
                    notification.addAction(NotificationAction.createSimple("Install update") {
                        notification.expire()
                        install(project)
                    })
                    notification.notify(project)
                } else if (interactive) {
                    val current = response.get("current")?.asString ?: "installed"
                    notice(project, "T+ is up to date", "Version $current is already installed.").notify(project)
                }
            } catch (ex: Exception) {
                if (interactive) notice(project, "Update check failed", ex.message ?: "Unknown error", true).notify(project)
            }
        }
    }

    private fun install(project: Project) {
        // Only called from the explicit "Install update" user action.
        ApplicationManager.getApplication().executeOnPooledThread {
            try {
                val result = command("update", "install", "--yes", "--json")
                if (result.get("ok")?.asBoolean != true) {
                    val error = result.get("error")?.asString ?: "Update failed"
                    notice(project, "T+ update failed", error, true).notify(project)
                    return@executeOnPooledThread
                }
                if (result.get("installed")?.asBoolean == true) {
                    val latest = result.get("latest")?.asString ?: "new version"
                    notice(project, "T+ $latest installed",
                        "The compiler is ready. Restart IntelliJ IDEA to activate the updated plugin.").notify(project)
                } else {
                    notice(project, "T+", "No new release to install.").notify(project)
                }
            } catch (ex: Exception) {
                notice(project, "T+ update failed", ex.message ?: "Unexpected error", true).notify(project)
            }
        }
    }

    fun checkAtStartup(project: Project) {
        if (checkedOnce.compareAndSet(false, true)) check(project, false)
    }
}

class CheckTekaUpdatesAction : AnAction(
    "Check for T+ Updates",
    "Check T+'s configured stable update source and offer installation",
    null
) {
    override fun actionPerformed(event: AnActionEvent) {
        event.project?.let { TekaUpdates.check(it, true) }
    }
}

class TekaUpdateStartupActivity : ProjectActivity {
    override suspend fun execute(project: Project) {
        TekaUpdates.checkAtStartup(project)
    }
}