package dev.teka.ide

import com.intellij.codeInsight.AutoPopupController
import com.intellij.codeInsight.editorActions.TypedHandlerDelegate
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile

/** Pop up symbol completion while typing in TekaLang, similar to Java. */
class TekaAutoPopupHandler : TypedHandlerDelegate() {
    override fun checkAutoPopup(
        charTyped: Char,
        project: Project,
        editor: Editor,
        file: PsiFile
    ): Result {
        if (file.virtualFile?.extension != "teka") return Result.CONTINUE
        if (charTyped.isLetterOrDigit() || charTyped == '_' || charTyped == '.') {
            AutoPopupController.getInstance(project).scheduleAutoPopup(editor)
            return Result.STOP
        }
        return Result.CONTINUE
    }
}