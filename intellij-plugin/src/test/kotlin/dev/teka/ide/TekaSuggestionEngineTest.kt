package dev.teka.ide

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class TekaSuggestionEngineTest {
    private fun choices(text: String) = TekaSuggestionEngine.candidates(text, text.length)
    private fun ghost(text: String) = TekaSuggestionEngine.inlineSuffix(text, text.length)

    @Test fun singleICompletesIf() {
        assertEquals("f", ghost("i"))
        assertNull(ghost("p"))
    }

    @Test fun repeatEnglishSnippet() {
        assertTrue(choices("rep").any { it.word == "repeat" })
        assertTrue(choices("say").any { it.kind == "snippet" })
    }

    @Test fun printCompletesWithTabInline() {
        assertEquals("nt()", ghost("pri"))
        val candidate = choices("pri").first()
        assertEquals("print", candidate.word)
        assertEquals("print()", candidate.insertedText())
        assertEquals(6, candidate.caretIndex())
    }

    @Test fun functionCompletionInsertsCall() {
        val code = "def square(x: int) -> int:\n\treturn x * x\n\nsqua"
        assertEquals("re()", ghost(code))
        assertEquals("square", choices(code).first().word)
        assertEquals("square()", choices(code).first().insertedText())
    }

    @Test fun suggestsVariableFromFile() {
        val code = "var total = 42\ntot"
        assertEquals("al", ghost(code))
        assertEquals("variable", choices(code).first().kind)
    }

    @Test fun suggestsImplicitVariable() {
        val code = "username = 'teka'\nuser"
        assertEquals("name", ghost(code))
    }

    @Test fun suggestsLoopVariable() {
        val code = "for number in range(5):\n\tprint(num"
        assertEquals("ber", ghost(code))
    }

    @Test fun suggestsFunctionParameter() {
        val code = "def compute(value: int) -> int:\n\treturn val"
        assertEquals("ue", ghost(code))
    }

    @Test fun forKeywordExpandsToMultilineSnippet() {
        val candidate = choices("for").first()
        assertEquals("snippet", candidate.kind)
        assertTrue(candidate.insertedText().startsWith("for i in range(5):"))
        assertTrue(candidate.insertedText().contains("\n\tprint(i)"))
        assertEquals(" i in range(5):\n\tprint(i)", ghost("for"))
    }

    @Test fun ifKeywordExpandsWithRealTab() {
        val candidate = choices("if").first()
        assertEquals("if True:\n\tprint('ready')", candidate.insertedText())
        assertTrue(candidate.caretIndex() > 0)
    }

    @Test fun defKeywordExpandsWithPlaceholders() {
        assertTrue(choices("def").any { it.kind == "snippet" && it.insertedText().contains("return x") })
    }

    @Test fun suppressInsideString() {
        assertNull(ghost("print('pri"))
        assertTrue(choices("print('pri").isEmpty())
    }

    @Test fun suppressInsideComment() {
        assertNull(ghost("# pri"))
        assertNull(ghost("// pri"))
        assertNull(ghost("print(1) # pri"))
    }

    @Test fun suppressMemberCompletion() {
        assertNull(ghost("obj.pr"))
        assertTrue(choices("obj.pr").isEmpty())
    }

    @Test fun suppressAtBlankCaret() {
        assertNull(ghost(""))
        assertNull(ghost("p"))
        assertNull(ghost("print(1)\n\t"))
    }

    @Test fun newlineHandling() {
        assertNull(ghost("\n"))
        assertEquals("nt()", ghost("\npri"))
    }

    @Test fun booleanCompletion() {
        assertEquals("ue", ghost("Tr"))
    }

    @Test fun returnAsStatement() {
        assertEquals("urn ", ghost("ret"))
        assertEquals("snippet", choices("ret").first().kind)
    }

    @Test fun caretMarkersStripped() {
        for (candidate in choices("pri")) {
            assertFalse(candidate.insertedText().contains("¦"))
            assertTrue(candidate.caretIndex() in 0..candidate.insertedText().length)
        }
    }

    @Test fun noMatch() {
        assertTrue(choices("qqznotreal").isEmpty())
        assertNull(ghost("qqznotreal"))
    }

    @Test fun worksWithManyFunctions() {
        val source = buildString {
            for (i in 1..50) append("def f$i(x: int) -> int:\n\treturn x\n\n")
            append("f4")
        }
        assertTrue(choices(source).any { it.word == "f49" })
        assertNotNull(ghost(source))
    }

    @Test fun nativeGraphicsCompletion() {
        val items = choices("game_")
        assertTrue(items.any { it.word == "game_open" })
        assertTrue(items.any { it.word == "game_circle" })
        assertTrue(items.any { it.word == "game_dt" })
    }

    @Test fun nativeGraphicsCallInsertion() {
        val item = choices("game_op").first { it.word == "game_open" }
        assertTrue(item.insertedText().startsWith("game_open("))
        assertTrue(item.caretIndex() in 0..item.insertedText().length)
    }

    @Test fun stringConversionAutocomplete() {
        val item = choices("st").first { it.word == "str" }
        assertEquals("str()", item.insertedText())
    }
}