# Generates demo.gif for the README.
# Regenerate after any output-affecting change with: vhs demo.tape

Output demo.gif

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 620
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 40ms
Set WindowBar Colorful

Hide
Type "source .venv/bin/activate && clear"
Enter
Sleep 500ms
Show

Type "ai-quality-analyzer scan ./examples/bad_app"
Sleep 600ms
Enter
Sleep 5s

Type "clear"
Enter
Sleep 400ms

Type "ai-quality-analyzer scan ./examples/good_app"
Sleep 600ms
Enter
Sleep 3s
