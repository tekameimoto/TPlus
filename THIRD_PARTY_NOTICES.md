# Third-party notices

T+ source is licensed under the [MIT license](LICENSE). Bundled third-party files retain their own licenses and copyright notices.

## Gradle Wrapper

The IntelliJ plugin build includes the Gradle Wrapper:

- `intellij-plugin/gradlew`
- `intellij-plugin/gradlew.bat`
- `intellij-plugin/gradle/wrapper/gradle-wrapper.jar`

These files are provided by the Gradle project under the Apache License, Version 2.0. The original notices in the wrapper scripts are retained.

- [License text](licenses/gradle-Apache-2.0.txt)
- [Upstream project](https://github.com/gradle/gradle)
- [Upstream license for Gradle 9.6.0](https://github.com/gradle/gradle/blob/v9.6.0/LICENSE)

## Build dependencies

The IntelliJ build downloads its platform, Kotlin, and test dependencies through Gradle. Their licenses remain with their respective projects. The license copy above covers the Gradle Wrapper; it does not relicense those dependencies.
