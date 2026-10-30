package dev.teka.ide

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.lexer.Lexer
import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.extapi.psi.ASTWrapperPsiElement
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet

/**
 * Minimal IntelliJ PSI for .teka files.
 * The authoritative syntax/type checker is the TekaLang compiler, not this
 * lightweight token parser. Having a real PSI file enables IDE annotations.
 */
class TekaParserDefinition : ParserDefinition {
    override fun createLexer(project: Project?): Lexer = TekaLexer()

    override fun createParser(project: Project?): PsiParser = PsiParser { root, builder ->
        val marker = builder.mark()
        while (!builder.eof()) {
            builder.advanceLexer()
        }
        marker.done(root)
        builder.treeBuilt
    }

    override fun getFileNodeType(): IFileElementType = FILE
    override fun getWhitespaceTokens(): TokenSet = TokenSet.WHITE_SPACE
    override fun getCommentTokens(): TokenSet = COMMENTS
    override fun getStringLiteralElements(): TokenSet = STRINGS

    override fun createElement(node: ASTNode): PsiElement = ASTWrapperPsiElement(node)
    override fun createFile(viewProvider: FileViewProvider): PsiFile = TekaPsiFile(viewProvider)

    override fun spaceExistenceTypeBetweenTokens(
        left: ASTNode,
        right: ASTNode
    ): ParserDefinition.SpaceRequirements = ParserDefinition.SpaceRequirements.MAY

    companion object {
        @JvmField val FILE = IFileElementType(TekaLanguage)
        @JvmField val COMMENTS = TokenSet.create(TekaTokens.COMMENT)
        @JvmField val STRINGS = TokenSet.create(TekaTokens.STRING)
    }
}

class TekaPsiFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, TekaLanguage) {
    override fun getFileType(): FileType = TekaFileType.INSTANCE
    override fun toString(): String = "T+ file"
}