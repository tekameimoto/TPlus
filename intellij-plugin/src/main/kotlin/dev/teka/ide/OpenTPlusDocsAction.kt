package dev.teka.ide

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.vfs.LocalFileSystem
import java.nio.file.Files
import java.nio.file.Paths

/** Open the authoritative local T+ handbook in IntelliJ, without a network request. */
class OpenTPlusDocsAction : AnAction("Open T+ Handbook") {
    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val path = Paths.get(System.getProperty("user.home"), "Developer", "TekaLang", "TPLUS_HANDBOOK.md")
        if (!Files.isRegularFile(path)) {
            Messages.showErrorDialog(project, "T+ handbook not found at $path", "T+ Documentation")
            return
        }
        val virtualFile = LocalFileSystem.getInstance().refreshAndFindFileByIoFile(path.toFile())
        if (virtualFile != null) {
            FileEditorManager.getInstance(project).openFile(virtualFile, true)
        } else {
            Messages.showErrorDialog(project, "Could not open the handbook at $path", "T+ Documentation")
        }
    }
}