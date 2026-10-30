package dev.teka.ide

import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionProvider
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.CompletionType
import com.intellij.codeInsight.completion.InsertionContext
import com.intellij.codeInsight.lookup.LookupElement
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.codeInsight.completion.PrioritizedLookupElement
import com.intellij.patterns.PlatformPatterns
import com.intellij.util.ProcessingContext

/** Java-like suggestions: builtins, user-defined functions, variables, snippets. */
class TekaCompletionContributor : CompletionContributor() {
    init {
        extend(
            CompletionType.BASIC,
            PlatformPatterns.psiElement().withLanguage(TekaLanguage),
            object : CompletionProvider<CompletionParameters>() {
                override fun addCompletions(
                    parameters: CompletionParameters,
                    context: ProcessingContext,
                    result: CompletionResultSet
                ) {
                    val source = parameters.originalFile.text
                    val offset = parameters.offset.coerceIn(0, source.length)
                    val candidates = TekaSuggestionEngine.candidates(source, offset)
                    for (candidate in candidates) {
                        val builder = LookupElementBuilder.create(candidate.word)
                            .withPresentableText(candidate.label)
                            .withTypeText(candidate.kind)
                            .withInsertHandler { insertContext, _: LookupElement ->
                                insertCandidate(insertContext, candidate)
                            }
                        result.addElement(PrioritizedLookupElement.withPriority(builder, candidate.priority))
                    }
                }
            }
        )
    }

    private fun insertCandidate(ctx: InsertionContext, candidate: TekaCandidate) {
        val document = ctx.document
        val begin = ctx.startOffset.coerceIn(0, document.textLength)
        val end = ctx.tailOffset.coerceIn(begin, document.textLength)
        val replacement = candidate.insertedText()
        document.replaceString(begin, end, replacement)
        val target = (begin + candidate.caretIndex()).coerceIn(begin, document.textLength)
        ctx.editor.caretModel.moveToOffset(target)
        ctx.editor.scrollingModel.scrollToCaret(com.intellij.openapi.editor.ScrollType.RELATIVE)
        ctx.setTailOffset(begin + replacement.length)
        // Don't insert the Tab/Enter character itself as an extra code character.
        ctx.setAddCompletionChar(false)
    }
}