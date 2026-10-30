package dev.teka.ide

import com.intellij.lang.Language
import com.intellij.openapi.fileTypes.LanguageFileType
import javax.swing.Icon

object TekaLanguage : Language("TekaLang")

class TekaFileType private constructor() : LanguageFileType(TekaLanguage) {
    override fun getName() = "T+ File"
    override fun getDescription() = "T+ source code"
    override fun getDefaultExtension() = "teka"
    override fun getIcon(): Icon? = null

    companion object {
        @JvmField val INSTANCE = TekaFileType()
    }
}