package dev.teka.ide

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.ui.Messages

class NewTekaFileAction : AnAction("T+ File", "Create a new .teka source file", null) {
    override fun update(event: AnActionEvent) {
        event.presentation.isEnabledAndVisible = event.project != null &&
            event.getData(CommonDataKeys.VIRTUAL_FILE) != null
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val selected = event.getData(CommonDataKeys.VIRTUAL_FILE) ?: return
        val folder = if (selected.isDirectory) selected else selected.parent ?: return
        val raw = Messages.showInputDialog(
            project, "Name your .teka file:", "New T+ File", null
        )?.trim() ?: return
        if (raw.isBlank()) return
        val name = if (raw.endsWith(".teka")) raw else "$raw.teka"
        if (name.contains('/') || name.contains('\\') || name == ".teka") {
            Messages.showErrorDialog(project, "Enter a valid file name.", "T+")
            return
        }
        if (folder.findChild(name) != null) {
            Messages.showErrorDialog(project, "$name already exists.", "T+")
            return
        }
        WriteCommandAction.runWriteCommandAction(project) {
            val file = folder.createChildData(this, name)
            file.setBinaryContent("print('hello from teka!')\n".toByteArray(Charsets.UTF_8))
            FileEditorManager.getInstance(project).openFile(file, true)
        }
    }
}