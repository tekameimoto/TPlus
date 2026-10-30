package dev.teka.ide

import com.intellij.execution.Executor
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.ConfigurationType
import com.intellij.execution.configurations.ConfigurationTypeBase
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.configurations.LocatableConfigurationBase
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.execution.configurations.RunConfigurationOptions
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RuntimeConfigurationError
import com.intellij.execution.configurations.ConfigurationTypeUtil
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.configurations.CommandLineState
import com.intellij.execution.process.OSProcessHandler
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessTerminatedListener
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project
import com.intellij.icons.AllIcons
import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.LazyRunConfigurationProducer
import com.intellij.openapi.util.JDOMExternalizable
import com.intellij.psi.PsiElement
import org.jdom.Element
import java.awt.BorderLayout
import java.io.File
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField

/** Standard IntelliJ Run Configuration type for .teka source files. */
class TekaRunConfigurationType : ConfigurationTypeBase(
    "TekaLangRunConfiguration",
    "T+",
    "Run a .teka file using the T+ compiler",
    AllIcons.RunConfigurations.Application
) {
    init {
        addFactory(TekaRunConfigurationFactory(this))
    }
}

class TekaRunConfigurationFactory(type: ConfigurationType) : ConfigurationFactory(type) {
    override fun getId() = "TekaLangConfigurationFactory"

    override fun createTemplateConfiguration(project: Project): RunConfiguration =
        TekaRunConfiguration(project, this, "T+")
}

class TekaRunConfiguration(
    project: Project,
    factory: ConfigurationFactory,
    name: String
) : LocatableConfigurationBase<RunConfigurationOptions>(project, factory, name) {

    var filePath: String = ""

    override fun readExternal(element: Element) {
        super.readExternal(element)
        filePath = element.getAttributeValue("tekaFile") ?: ""
    }

    override fun writeExternal(element: Element) {
        super.writeExternal(element)
        element.setAttribute("tekaFile", filePath)
    }

    override fun getConfigurationEditor(): SettingsEditor<out RunConfiguration> =
        TekaRunConfigurationEditor()

    override fun checkConfiguration() {
        val file = File(filePath)
        if (filePath.isBlank() || !file.isFile || file.extension != "teka") {
            throw RuntimeConfigurationError("Choose an existing .teka file to run.")
        }
        if (TekaCommand.resolve() == null) {
            throw RuntimeConfigurationError("T+ compiler not found. Install it using the instructions for your operating system.")
        }
    }

    override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState {
        val path = filePath
        return object : CommandLineState(environment) {
            override fun startProcess(): ProcessHandler {
                val file = File(path)
                val launcher = TekaCommand.resolve() ?: throw IllegalStateException("T+ compiler not installed")
                val command = GeneralCommandLine(launcher + listOf("run", file.absolutePath))
                    .withWorkDirectory(file.parentFile)
                val handler = OSProcessHandler(command)
                ProcessTerminatedListener.attach(handler)
                return handler
            }
        }
    }
}

class TekaRunConfigurationEditor : SettingsEditor<TekaRunConfiguration>() {
    private val pathInput = JTextField()
    private val panel = JPanel(BorderLayout(8, 0)).apply {
        add(JLabel("T+ .teka file:"), BorderLayout.WEST)
        add(pathInput, BorderLayout.CENTER)
    }

    override fun createEditor(): JComponent = panel

    override fun resetEditorFrom(configuration: TekaRunConfiguration) {
        pathInput.text = configuration.filePath
    }

    override fun applyEditorTo(configuration: TekaRunConfiguration) {
        configuration.filePath = pathInput.text.trim()
    }
}

class TekaRunConfigurationProducer : LazyRunConfigurationProducer<TekaRunConfiguration>() {
    override fun getConfigurationFactory(): ConfigurationFactory {
        return ConfigurationTypeUtil
            .findConfigurationType(TekaRunConfigurationType::class.java)
            .configurationFactories.first()
    }

    override fun setupConfigurationFromContext(
        configuration: TekaRunConfiguration,
        context: ConfigurationContext,
        sourceElement: com.intellij.openapi.util.Ref<PsiElement>
    ): Boolean {
        val file = context.psiLocation?.containingFile?.virtualFile ?: return false
        if (file.extension != "teka") return false
        configuration.filePath = file.path
        configuration.name = "T+: ${file.name}"
        return true
    }

    override fun isConfigurationFromContext(
        configuration: TekaRunConfiguration,
        context: ConfigurationContext
    ): Boolean {
        val file = context.psiLocation?.containingFile?.virtualFile ?: return false
        return file.extension == "teka" && File(configuration.filePath).absolutePath == File(file.path).absolutePath
    }
}