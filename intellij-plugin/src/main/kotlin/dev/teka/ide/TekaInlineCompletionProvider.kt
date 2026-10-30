package dev.teka.ide

import com.intellij.codeInsight.inline.completion.InlineCompletionEvent
import com.intellij.codeInsight.inline.completion.InlineCompletionProvider
import com.intellij.codeInsight.inline.completion.InlineCompletionProviderID
import com.intellij.codeInsight.inline.completion.InlineCompletionRequest
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSingleSuggestion
import com.intellij.codeInsight.inline.completion.elements.InlineCompletionGrayTextElement
import com.intellij.codeInsight.inline.completion.elements.InlineCompletionElement
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flowOf

/**
 * Gray inline code suggestions — press Tab to accept when an inline proposal
 * appears. Uses the same context-aware local candidate engine as the popup.
 * No network requests, no language model, and no code execution.
 */
class TekaInlineCompletionProvider : InlineCompletionProvider {
    override val id: InlineCompletionProviderID = InlineCompletionProviderID("tekalang-local-inline")

    override fun isEnabled(event: InlineCompletionEvent): Boolean =
        event is InlineCompletionEvent.DocumentChange &&
            event.toRequest()?.file?.virtualFile?.extension == "teka"

    override suspend fun getSuggestion(request: InlineCompletionRequest): InlineCompletionSingleSuggestion {
        if (request.file.virtualFile?.extension != "teka") {
            return InlineCompletionSingleSuggestion.build(elements = emptyFlow<InlineCompletionElement>())
        }
        val document = request.document
        val offset = request.endOffset.coerceIn(0, document.textLength)
        val before = document.charsSequence.subSequence(0, offset).toString()
        val suffix = TekaSuggestionEngine.inlineSuffix(before, before.length)
            ?: return InlineCompletionSingleSuggestion.build(elements = emptyFlow<InlineCompletionElement>())
        return InlineCompletionSingleSuggestion.build(elements = flowOf<InlineCompletionElement>(InlineCompletionGrayTextElement(suffix)))
    }
}