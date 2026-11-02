plugins {
    kotlin("jvm") version "2.4.21"
    id("org.jetbrains.intellij.platform") version "2.19.0"
}

group = "dev.teka"
val compilerSource = file("../teka.py").readText()
val releaseVersions = Regex("""(?m)^VERSION = ['"]([0-9]+\.[0-9]+\.[0-9]+)['"]$""")
    .findAll(compilerSource).map { it.groupValues[1] }.toList()
require(releaseVersions.size == 1) { "teka.py must define exactly one release version" }
version = releaseVersions.single()

tasks.withType<AbstractArchiveTask>().configureEach {
    isPreserveFileTimestamps = false
    isReproducibleFileOrder = true
}

repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}

dependencies {
    intellijPlatform {
        intellijIdea("2026.2.3")
    }
    testImplementation("org.junit.jupiter:junit-jupiter:5.11.4")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
    }
}

intellijPlatform {
    pluginConfiguration {
        name = "T+"
        version = project.version.toString()
        ideaVersion { sinceBuild = "262" }
    }
}