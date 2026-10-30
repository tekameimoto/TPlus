# Contributing to T+

Bug reports, small fixes, and example programs are welcome.

## Report a bug

Open an issue with:

- The output of `teka --version`.
- Your operating system and C++ compiler.
- A short `.teka` program that reproduces the problem.
- The command you ran, the full error, and what you expected.

Remove passwords, tokens, personal paths, and private source code before posting.

## Send a change

Keep a pull request focused on one change. Describe what it fixes and include a small example when the behavior changes. For language changes, update the handbook and add a regression test.

Run the compiler tests before opening a pull request:

```sh
python3 -m unittest discover -s tests -v
```

On Windows, use `python` if that is the name of your Python 3.11+ command.

For IntelliJ plugin changes, use Java 25 and run `./gradlew test` from `intellij-plugin` (`gradlew.bat test` on Windows).

CI checks the compiler on macOS, Linux, and Windows, and tests the IntelliJ plugin.

## License

Contributions to T+ are made under the project's [MIT license](LICENSE). Preserve the license and attribution of any third-party material you include, and document it in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
