package dev.teka.ide

import com.intellij.lexer.LexerBase
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IElementType

object TekaTokens {
    val KEYWORD = IElementType("TEKA_KEYWORD", TekaLanguage)
    val STRING = IElementType("TEKA_STRING", TekaLanguage)
    val NUMBER = IElementType("TEKA_NUMBER", TekaLanguage)
    val COMMENT = IElementType("TEKA_COMMENT", TekaLanguage)
    val OPERATOR = IElementType("TEKA_OPERATOR", TekaLanguage)
    val IDENTIFIER = IElementType("TEKA_IDENTIFIER", TekaLanguage)
}

class TekaLexer : LexerBase() {
    private var buffer: CharSequence = ""
    private var endOffset = 0
    private var position = 0
    private var nextPosition = 0
    private var currentType: IElementType? = null
    private val keywords = setOf("fn", "def", "elif", "range", "pass", "True", "False", "let", "var", "return", "if", "else", "while",
        "for", "in", "and", "or", "not", "true", "false", "int", "float", "string",
        "bool", "void", "list", "break", "continue", "print", "len", "push", "pop", "str", "input", "class", "import", "as", "say", "ask", "repeat", "times", "otherwise", "stop", "skip", "is", "below", "above")

    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer = buffer
        this.endOffset = endOffset
        position = startOffset
        locateNext()
    }

    override fun getState() = 0
    override fun getTokenType(): IElementType? = currentType
    override fun getTokenStart() = position
    override fun getTokenEnd() = nextPosition
    override fun getBufferSequence(): CharSequence = buffer
    override fun getBufferEnd() = endOffset

    override fun advance() {
        position = nextPosition
        locateNext()
    }

    private fun locateNext() {
        if (position >= endOffset) {
            currentType = null
            nextPosition = endOffset
            return
        }
        val c = buffer[position]
        var i = position + 1
        currentType = when {
            c.isWhitespace() -> {
                while (i < endOffset && buffer[i].isWhitespace()) i++
                TokenType.WHITE_SPACE
            }
            c == '#' || (c == '/' && i < endOffset && buffer[i] == '/') -> {
                while (i < endOffset && buffer[i] != '\n') i++
                TekaTokens.COMMENT
            }
            c == '"' || c == '\'' -> {
                val quote = c
                var escaped = false
                while (i < endOffset) {
                    val x = buffer[i++]
                    if (x == quote && !escaped) break
                    if (x == '\\' && !escaped) escaped = true
                    else escaped = false
                }
                TekaTokens.STRING
            }
            c.isDigit() -> {
                while (i < endOffset && buffer[i].isDigit()) i++
                if (i + 1 < endOffset && buffer[i] == '.' && buffer[i+1].isDigit()) {
                    i++
                    while (i < endOffset && buffer[i].isDigit()) i++
                }
                TekaTokens.NUMBER
            }
            c.isLetter() || c == '_' -> {
                while (i < endOffset && (buffer[i].isLetterOrDigit() || buffer[i] == '_')) i++
                if (buffer.subSequence(position, i).toString() in keywords) TekaTokens.KEYWORD
                else TekaTokens.IDENTIFIER
            }
            c in "+-*/%=<>!&|.,:;(){}[]" -> {
                if (i < endOffset && (buffer.subSequence(position, i+1).toString() in
                            setOf("==", "!=", "<=", ">=", "->", "..", "&&", "||"))) i++
                TekaTokens.OPERATOR
            }
            else -> TokenType.BAD_CHARACTER
        }
        nextPosition = i
    }
}