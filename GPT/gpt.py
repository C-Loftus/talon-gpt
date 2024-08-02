import os
from typing import Any, ClassVar

from talon import Module, actions, clip, imgui, settings

from ..lib.HTMLBuilder import Builder
from ..lib.modelHelpers import (
    clear_context,
    generate_payload,
    gpt_send_request,
    new_thread,
    notify,
    paste_and_modify,
    push_context,
    push_thread,
    string_context,
    string_thread,
)

mod = Module()


class GPTState:
    text_to_confirm: ClassVar[str] = ""
    last_response: ClassVar[str] = ""
    last_was_pasted: ClassVar[bool] = False


@imgui.open()
def confirmation_gui(gui: imgui.GUI):
    gui.text("Confirm model output before pasting")
    gui.line()
    gui.spacer()
    gui.text(GPTState.text_to_confirm)

    gui.spacer()
    if gui.button("Paste model output"):
        actions.user.paste_model_confirmation_gui()

    gui.spacer()
    if gui.button("Copy model output"):
        actions.user.copy_model_confirmation_gui()

    gui.spacer()
    if gui.button("Deny model output"):
        actions.user.close_model_confirmation_gui()


def gpt_query(prompt: str, content: str, modifier: str = "") -> str:
    """Send a prompt to the GPT API and return the response"""

    # Reset state before pasting
    GPTState.last_was_pasted = False

    headers, data = generate_payload(prompt, content, None, modifier)

    response = gpt_send_request(headers, data)
    GPTState.last_response = response
    if modifier == "thread":
        push_thread(prompt)
        push_thread(content)
        push_thread(response)
    return response


@mod.action_class
class UserActions:
    def gpt_blend(source_text: str, destination_text: str):
        """Blend all the source text and send it to the destination"""
        prompt = f"""
        Act as a text transformer. I'm going to give you some source text and destination text, and I want you to modify the destination text based on the contents of the source text in a way that combines both of them together. Use the structure of the destination text, reordering and renaming as necessary to ensure a natural and coherent flow. Please return only the final text with no decoration for insertion into a document in the specified language.

        Here is the destination text:
        ```
        {destination_text}
        ```

        Please return only the final text. What follows is all of the source texts separated by '---'.
        """
        return gpt_query(prompt, source_text)

    def gpt_blend_list(source_text: list[str], destination_text: str):
        """Blend all the source text as a list and send it to the destination"""

        return actions.user.gpt_blend("\n---\n".join(source_text), destination_text)

    def gpt_generate_shell(text_to_process: str) -> str:
        """Generate a shell command from a spoken instruction"""
        shell_name = settings.get("user.model_shell_default")
        if shell_name is None:
            raise Exception("GPT Error: Shell name is not set. Set it in the settings.")

        prompt = f"""
        Generate a {shell_name} shell command that will perform the given task.
        Only include the code. Do not include any comments, backticks, or natural language explanations. Do not output the shell name, only the code that is valid {shell_name}.
        Condense the code into a single line such that it can be ran in the terminal.
        """

        result = gpt_query(prompt, text_to_process)
        return result

    def gpt_generate_sql(text_to_process: str) -> str:
        """Generate a SQL query from a spoken instruction"""

        prompt = """
       Generate SQL to complete a given request.
       Output only the SQL in one line without newlines.
       Do not output comments, backticks, or natural language explanations.
       Prioritize SQL queries that are database agnostic.
        """
        return gpt_query(prompt, text_to_process)

    def add_to_confirmation_gui(model_output: str):
        """Add text to the confirmation gui"""
        GPTState.text_to_confirm = model_output
        confirmation_gui.show()

    def gpt_clear_context():
        """Reset the stored context"""
        clear_context()

    def gpt_new_thread():
        """Create a new thread"""
        new_thread()

    def gpt_push_context(context: str):
        """Add the selected text to the stored context"""
        push_context(context)

    def gpt_push_thread(content: str):
        """Add the selected text to the active thread"""
        push_thread(content)

    def gpt_get_context():
        """Fetch the user context as a string"""
        return string_context()

    def gpt_get_thread():
        """Fetch the user thread as a string"""
        return string_thread()

    def contextual_user_context():
        """This is an override function that can be used to add additional context to the prompt"""
        return []

    def close_model_confirmation_gui():
        """Close the model output without pasting it"""
        GPTState.text_to_confirm = ""
        confirmation_gui.hide()

    def copy_model_confirmation_gui():
        """Copy the model output to the clipboard"""
        clip.set_text(GPTState.text_to_confirm)
        GPTState.text_to_confirm = ""

        confirmation_gui.hide()

    def paste_model_confirmation_gui():
        """Paste the model output"""
        actions.user.paste(GPTState.text_to_confirm)
        GPTState.text_to_confirm = ""
        confirmation_gui.hide()

    def gpt_select_last():
        """select all the text in the last GPT output"""
        if not GPTState.last_was_pasted:
            notify("Tried to select GPT output, but it was not pasted in an editor")
            return

        lines = GPTState.last_response.split("\n")
        for _ in lines[:-1]:
            actions.edit.extend_up()
        actions.edit.extend_line_end()
        for _ in lines[0]:
            actions.edit.extend_left()

    def gpt_apply_prompt(
        prompt: str, text_to_process: str | list[str], modifier: str = ""
    ) -> str:
        """Apply an arbitrary prompt to arbitrary text"""
        text_to_process = (
            " ".join(text_to_process)
            if isinstance(text_to_process, list)
            else text_to_process
        )

        # Apply modifiers to prompt before handling special cases
        match modifier:
            case "snip":
                prompt += "\n\nPlease return the response as a snippet with placeholders. A snippet can control cursors and text insertion using constructs like tabstops ($1, $2, etc., with $0 as the final position). Linked tabstops update together. Placeholders, such as ${1:foo}, allow easy changes and can be nested (${1:another ${2:placeholder}}). Choices, using ${1|one,two,three|}, prompt user selection."

        # Ask is a special case, where the text to process is the prompted question, not the selected text
        if prompt.startswith("ask"):
            text_to_process = prompt.removeprefix("ask")
            prompt = """Generate text that satisfies the question or request given in the input."""
        # If the user is just moving the source to the destination, we don't need to apply a query
        elif prompt == "pass":
            if text_to_process == "__CONTEXT__":
                return string_context()
            elif text_to_process == "__THREAD__":
                return string_thread()
            return text_to_process

        response = gpt_query(prompt, text_to_process, modifier)

        return response

    def gpt_help():
        """Open the GPT help file in the web browser"""
        # get the text from the file and open it in the web browser
        current_dir = os.path.dirname(__file__)
        file_path = os.path.join(current_dir, "lists", "staticPrompt.talon-list")
        with open(file_path, "r") as f:
            lines = f.readlines()[2:]

        builder = Builder()
        builder.h1("Talon GPT Prompt List")
        for line in lines:
            if "##" in line:
                builder.h2(line)
            else:
                builder.p(line)

        builder.render()

    def gpt_reformat_last(how_to_reformat: str):
        """Reformat the last model output"""
        PROMPT = f"""The last phrase was written using voice dictation. It has an error with spelling, grammar, or just general misrecognition due to a lack of context. Please reformat the following text to correct the error with the context that it was {how_to_reformat}."""
        last_output = actions.user.get_last_phrase()
        if last_output:
            actions.user.clear_last_phrase()
            return gpt_query(PROMPT, last_output)
        else:
            notify("No text to reformat")
            raise Exception("No text to reformat")

    def gpt_insert_response(
        result: str,
        method: str = "",
        modifier: str = "",
        cursorless_destination: Any = None,
    ):
        """Insert a GPT result in a specified way"""
        match method:
            case "above":
                actions.key("left")
                actions.edit.line_insert_up()
                GPTState.last_was_pasted = True
                paste_and_modify(result, modifier)
            case "below":
                actions.key("right")
                actions.edit.line_insert_down()
                GPTState.last_was_pasted = True
                paste_and_modify(result, modifier)
            case "clipboard":
                clip.set_text(result)
            case "context":
                push_context(result)
            case "newContext":
                clear_context()
                push_context(result)
            case "thread":
                push_thread(result)
            case "newThread":
                new_thread()
                push_thread(result)
            case "appendClipboard":
                clip.set_text(clip.text() + "\n" + result)
            case "browser":
                builder = Builder()
                builder.h1("Talon GPT Result")
                for line in result.split("\n"):
                    builder.p(line)
                builder.render()
            case "textToSpeech":
                try:
                    actions.user.tts(result)
                except KeyError:
                    notify("GPT Failure: text to speech is not installed")

            # Although we can insert to a cursorless dpestination, the cursorless_target capture
            # Greatly increases DFA compliation times and should be avoided if possible
            case "cursorless":
                actions.user.cursorless_insert(cursorless_destination, result)
            case "paste" | _:
                GPTState.last_was_pasted = True
                paste_and_modify(result, modifier)

    def gpt_get_source_text(spoken_text: str) -> str:
        """Get the source text that is will have the prompt applied to it"""
        match spoken_text:
            case "clipboard":
                clipboard_text = clip.text()
                if clipboard_text is None:
                    if clip.image():
                        return "__IMAGE__"
                    else:
                        notify(
                            "GPT Failure: User applied a prompt to the phrase clipboard, but there was no clipboard text or image stored"
                        )
                        return
                return clipboard_text
            case "context":
                return "__CONTEXT__"
            case "thread":
                return "__THREAD__"
            case "gptResponse":
                if GPTState.last_response == "":
                    raise Exception(
                        "GPT Failure: User applied a prompt to the phrase GPT response, but there was no GPT response stored"
                    )
                return GPTState.last_response

            case "lastTalonDictation":
                last_output = actions.user.get_last_phrase()
                if last_output:
                    actions.user.clear_last_phrase()
                    return last_output
                else:
                    notify(
                        "GPT Failure: User applied a prompt to the phrase last Talon Dictation, but there was no text to reformat"
                    )
                    raise Exception(
                        "GPT Failure: User applied a prompt to the phrase last Talon Dictation, but there was no text to reformat"
                    )
            case "this" | _:
                return actions.edit.selected_text()
