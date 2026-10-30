package dev.teka.ide

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class TekaMemberCompletionTest {
    private fun suggestions(text: String) = TekaSuggestionEngine.candidates(text, text.length)
    private fun ghost(text: String) = TekaSuggestionEngine.inlineSuffix(text, text.length)

    @Test fun tekaNamespaceOffersImportedModule() {
        val items = suggestions("import teka.random\nteka.ra")
        assertTrue(items.any { it.word == "random" })
    }

    @Test fun tekaNamespaceOffersMembers() {
        val items = suggestions("import teka.text\nteka.text.up")
        assertTrue(items.any { it.word == "upper" })
        assertEquals("upper()", items.first { it.word == "upper" }.insertedText())
    }

    @Test fun namespaceDoesNotInventModules() {
        assertTrue(suggestions("import teka.math\nteka.files.").isEmpty())
    }

    @Test fun randomModuleMembers() {
        val result = suggestions("import random\nrandom.")
        assertEquals(setOf("randint", "randrange", "random", "uniform"), result.map { it.word }.toSet())
        assertTrue(result.isNotEmpty())
    }

    @Test fun randomFunctionPrefix() {
        val matches = suggestions("import random\nrandom.randi")
        assertEquals("randint", matches.first().word)
        assertEquals("randint(1, 100)", matches.first().insertedText())
    }

    @Test fun mathStandardMembers() {
        val items = suggestions("import math\nmath.")
        assertTrue(items.any { it.word == "sqrt" })
        assertTrue(items.any { it.word == "pi" })
        assertFalse(items.any { it.word == "randint" })
    }

    @Test fun moduleAlias() {
        val items = suggestions("import random as rng\nrng.ran")
        assertTrue(items.any { it.word == "randint" })
        assertTrue(items.any { it.word == "random" })
    }

    @Test fun missingImportReturnsNoMemberSuggestions() {
        assertTrue(suggestions("random.").isEmpty())
        assertTrue(suggestions("import math\nrandom.").isEmpty())
    }

    @Test fun objectFieldsFromSource() {
        val code = "class Player:\n    def __init__(self):\n        self.health = 100\n\nplayer = Player()\nplayer.he"
        assertEquals("health", suggestions(code).first().word)
        assertEquals("alth", ghost(code))
    }

    @Test fun objectMethodsFromSource() {
        val code = "class Player:\n    def __init__(self):\n        self.health = 100\n    def move(self, x: int, y: int):\n        pass\n\nplayer = Player()\nplayer.mo"
        val found = suggestions(code).first()
        assertEquals("move", found.word)
        assertEquals("move()", found.insertedText())
    }

    @Test fun methodsWithoutArguments() {
        val code = "class Player:\n    def __init__(self):\n        pass\n    def play(self):\n        print(1)\n\nplayer = Player()\nplayer.pl"
        assertEquals("play()", suggestions(code).first().insertedText())
    }

    @Test fun currentSelfFields() {
        val code = "class Player:\n    def __init__(self):\n        self.health = 100\n    def test(self):\n        print(self.he"
        assertEquals("health", suggestions(code).first().word)
    }

    @Test fun nestedObjectChain() {
        val code = "class Position:\n    def __init__(self):\n        self.x = 10\nclass Player:\n    def __init__(self):\n        self.position = Position()\np = Player()\np.position."
        assertTrue(suggestions(code).any { it.word == "x" })
    }

    @Test fun noFakeClassMethod() {
        val code = "class Player:\n    def __init__(self):\n        self.health = 100\np = Player()\np.teleport"
        assertTrue(suggestions(code).isEmpty())
    }

    @Test fun memberSuggestionsDoNotPolluteGeneralCompletion() {
        assertTrue(suggestions("import random\npri").any { it.word == "print" })
        assertFalse(suggestions("import random\npri").any { it.word == "randint" })
    }
}