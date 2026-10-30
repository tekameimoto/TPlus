package dev.teka.ide

import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.RunManager
import com.intellij.execution.configurations.ConfigurationTypeUtil
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.execution.process.KillableColoredProcessHandler
import com.intellij.execution.ui.RunContentManager
import com.intellij.execution.filters.TextConsoleBuilderFactory
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.ui.Messages
import com.intellij.execution.configurations.GeneralCommandLine
import java.io.File

class RunTekaAction : AnAction() {
    override fun update(event: AnActionEvent) {
        val file = event.getData(CommonDataKeys.VIRTUAL_FILE)
            ?: event.getData(CommonDataKeys.PSI_FILE)?.virtualFile
        event.presentation.isEnabledAndVisible = file?.extension == "teka" && event.project != null
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val file = event.getData(CommonDataKeys.VIRTUAL_FILE)
            ?: event.getData(CommonDataKeys.PSI_FILE)?.virtualFile ?: return
        FileDocumentManager.getInstance().saveAllDocuments()
        // Make this file a real IntelliJ Run Configuration, so the normal
        // toolbar's Play button can run it the next time without right-clicking.
        val manager = RunManager.getInstance(project)
        val config = manager.allSettings.firstOrNull {
            (it.configuration as? TekaRunConfiguration)?.filePath == file.path
        } ?: run {
            val factory = ConfigurationTypeUtil.findConfigurationType(TekaRunConfigurationType::class.java)
                .configurationFactories.first()
            manager.createConfiguration("T+: ${file.name}", factory).also {
                (it.configuration as TekaRunConfiguration).filePath = file.path
                manager.addConfiguration(it)
            }
        }
        manager.selectedConfiguration = config
        val root = project.basePath?.let(::File) ?: File(System.getProperty("user.home"))
        val compilerCommand = TekaCommand.resolve(root)
        if (compilerCommand == null) {
            Messages.showErrorDialog(project, "Install the T+ compiler first. See the README for your operating system.", "T+ Compiler Not Found")
            return
        }
        val command = GeneralCommandLine(compilerCommand + listOf("run", file.path)).withWorkDirectory(root)
        try {
            val handler = KillableColoredProcessHandler(command)
            val console = TextConsoleBuilderFactory.getInstance().createBuilder(project).console
            console.attachToProcess(handler)
            val descriptor = RunContentDescriptor(console, handler, console.component, "T+: ${file.name}")
            RunContentManager.getInstance(project)
                .showRunContent(DefaultRunExecutor.getRunExecutorInstance(), descriptor)
            handler.startNotify()
        } catch (ex: Exception) {
            Messages.showErrorDialog(project,
                "Could not start T+: ${ex.message}",
                "T+ Run Error")
        }
    }
}