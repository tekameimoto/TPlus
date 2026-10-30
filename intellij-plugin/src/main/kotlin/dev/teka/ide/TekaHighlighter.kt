package dev.teka.ide

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IElementType

class TekaHighlighterFactory : SyntaxHighlighterFactory() {
    override fun getSyntaxHighlighter(project: Project?, virtualFile: VirtualFile?) = TekaHighlighter()
}

class TekaHighlighter : SyntaxHighlighterBase() {
    override fun getHighlightingLexer(): Lexer = TekaLexer()
    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> = when (tokenType) {
        TekaTokens.KEYWORD -> KEYWORD
        TekaTokens.STRING -> STRING
        TekaTokens.NUMBER -> NUMBER
        TekaTokens.COMMENT -> COMMENT
        TekaTokens.OPERATOR -> OPERATOR
        TokenType.BAD_CHARACTER -> BAD
        else -> EMPTY
    }
    companion object {
        private val KEYWORD = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_KEYWORD", DefaultLanguageHighlighterColors.KEYWORD))
        private val STRING = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_STRING", DefaultLanguageHighlighterColors.STRING))
        private val NUMBER = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_NUMBER", DefaultLanguageHighlighterColors.NUMBER))
        private val COMMENT = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT))
        private val OPERATOR = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_OPERATOR", DefaultLanguageHighlighterColors.OPERATION_SIGN))
        private val BAD = arrayOf(TextAttributesKey.createTextAttributesKey("TEKA_BAD", HighlighterColors.BAD_CHARACTER))
        private val EMPTY = emptyArray<TextAttributesKey>()
    }
}