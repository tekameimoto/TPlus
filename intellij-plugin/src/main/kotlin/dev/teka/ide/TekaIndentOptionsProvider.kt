package dev.teka.ide

import com.intellij.openapi.fileTypes.FileType
import com.intellij.psi.PsiFile
import com.intellij.psi.codeStyle.CommonCodeStyleSettings
import com.intellij.psi.codeStyle.FileTypeIndentOptionsProvider

/** New .teka files use literal tab bytes for indentation, not four space bytes. */
class TekaIndentOptionsProvider : FileTypeIndentOptionsProvider {
    override fun getFileType(): FileType = TekaFileType.INSTANCE

    override fun createIndentOptions(): CommonCodeStyleSettings.IndentOptions =
        CommonCodeStyleSettings.IndentOptions().apply {
            USE_TAB_CHARACTER = true
            SMART_TABS = false
            TAB_SIZE = 4
            INDENT_SIZE = 4
            CONTINUATION_INDENT_SIZE = 4
        }

    override fun getPreviewText(): String =
        "def greet(name: string):\n\tprint('hello', name)\n\nfor i in range(3):\n\tgreet('teka')"

    override fun prepareForReformat(psiFile: PsiFile) = Unit
}