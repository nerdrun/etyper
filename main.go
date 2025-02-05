package main

import (
	"github.com/rivo/tview"
)

func main() {
	app := tview.NewApplication()

	// tview.NewPages().

	textArea := tview.NewTextArea().SetWrap(true).SetPlaceholder("Your story is about...")

	if err := app.SetRoot(textArea, true).EnableMouse(true).EnablePaste(true).Run(); err != nil {
		panic(err)
	}
}
