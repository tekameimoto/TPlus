package dev.teka.ide

import com.google.gson.JsonParser
import com.intellij.lang.annotation.AnnotationHolder
import com.intellij.lang.annotation.ExternalAnnotator
import com.intellij.lang.annotation.HighlightSeverity
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiFile
import java.io.File
import java.util.concurrent.TimeUnit

data class TekaIssue(val line: Int, val column: Int, val message: String, val code: String)

/**
 * Runs the real compiler's CHECK mode against unsaved editor text.
 * Never compiles native code or executes user code while highlighting.
 */
class TekaExternalAnnotator : ExternalAnnotator<String, List<TekaIssue>>() {
    override fun collectInformation(file: PsiFile): String? {
        if (file.virtualFile?.extension != "teka") return null
        val source = file.text
        return if (source.length <= 200_000) source else null
    }

    override fun doAnnotate(collectedInfo: String): List<TekaIssue> {
        val compiler = TekaCommand.resolve() ?: return emptyList()
        var process: Process? = null
        try {
            process = ProcessBuilder(compiler + listOf("check", "--stdin", "--json"))
                .redirectErrorStream(true)
                .start()
            process.outputStream.bufferedWriter(Charsets.UTF_8).use { it.write(collectedInfo) }
            if (!process.waitFor(4, TimeUnit.SECONDS)) {
                process.destroyForcibly()
                return emptyList()
            }
            val output = process.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val root = JsonParser.parseString(output).asJsonObject
            return root.getAsJsonArray("errors")?.mapNotNull { element ->
                val issue = element.asJsonObject
                TekaIssue(
                    issue.get("line")?.asInt ?: 1,
                    issue.get("column")?.asInt ?: 1,
                    issue.get("message")?.asString ?: "TekaLang error",
                    issue.get("code")?.asString ?: "E000"
                )
            } ?: emptyList()
        } catch (_: Exception) {
            return emptyList()
        } finally {
            process?.destroy()
        }
    }

    override fun apply(file: PsiFile, annotationResult: List<TekaIssue>, holder: AnnotationHolder) {
        val document = PsiDocumentManager.getInstance(file.project).getDocument(file) ?: return
        for (issue in annotationResult) {
            if (document.textLength == 0 || document.lineCount == 0) continue
            val index = (issue.line - 1).coerceIn(0, document.lineCount - 1)
            val from = document.getLineStartOffset(index)
            val until = document.getLineEndOffset(index)
            val start = (from + issue.column - 1).coerceIn(from, until)
            val safeStart = start.coerceAtMost(document.textLength - 1)
            val safeEnd = (safeStart + 1).coerceAtMost(document.textLength)
            holder.newAnnotation(HighlightSeverity.ERROR, "error[" + issue.code + "]: " + issue.message)
                .range(TextRange(safeStart, safeEnd))
                .create()
        }
    }
}