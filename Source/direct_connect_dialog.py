from prompt_toolkit.layout import Window, FormattedTextControl, HSplit, VSplit
from prompt_toolkit.widgets import Shadow, TextArea
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import ConditionalContainer, Float
from prompt_toolkit.formatted_text import HTML


class DirectConnectDialog:

    def __init__(self, tui):
        self.tui = tui
        self.textarea = None
        self._placeholder = True

    def get_container(self):
        return Float(
            content=ConditionalContainer(
                content=self._build_dialog(),
                filter=Condition(lambda: self.tui.show_direct_connect)
            )
        )

    def _build_dialog(self):
        self.textarea = TextArea(
            text="IP:PORT",
            multiline=False,
            accept_handler=self._handle_accept,
        )

        def _on_changed(buf):
            if self._placeholder:
                self._placeholder = False
                ph = "IP:PORT"
                if ph in buf.text:
                    buf.text = buf.text.replace(ph, "", 1)

        self.textarea.buffer.on_text_changed += _on_changed

        W = 52
        T = " DIRECT CONNECT "
        dash_left = (W - len(T)) // 2
        dash_right = W - len(T) - dash_left
        hint_text = "  Enter to connect   Ctrl+Q to cancel"
        hint_pad = W - len(hint_text)

        body = HSplit([
            Window(
                content=FormattedTextControl(
                    HTML(
                        f'<ansigreen>╭{"─" * dash_left}'
                        f'<b>{T}</b>'
                        f'{"─" * dash_right}╮</ansigreen>'
                    )
                ),
                height=1, always_hide_cursor=True,
            ),
            Window(
                content=FormattedTextControl(
                    HTML(f'<ansigreen>│</ansigreen>{" " * W}<ansigreen>│</ansigreen>')
                ),
                height=1, always_hide_cursor=True,
            ),
            VSplit([
                Window(
                    content=FormattedTextControl(HTML('<ansigreen>│</ansigreen>  ')),
                    width=3, always_hide_cursor=True,
                ),
                Window(
                    content=self.textarea.control,
                    style=lambda: "fg:ansibrightblack" if self._placeholder else "",
                ),
                Window(
                    content=FormattedTextControl(HTML('  <ansigreen>│</ansigreen>')),
                    width=3, always_hide_cursor=True,
                ),
            ]),
            Window(
                content=FormattedTextControl(
                    HTML(f'<ansigreen>│</ansigreen>{" " * W}<ansigreen>│</ansigreen>')
                ),
                height=1, always_hide_cursor=True,
            ),
            Window(
                content=FormattedTextControl(
                    HTML(
                        f'<ansigreen>│</ansigreen>'
                        f'<dim>{hint_text}</dim>'
                        f'{" " * hint_pad}<ansigreen>│</ansigreen>'
                    )
                ),
                height=1, always_hide_cursor=True,
            ),
            Window(
                content=FormattedTextControl(
                    HTML(f'<ansigreen>╰{"─" * W}╯</ansigreen>')
                ),
                height=1, always_hide_cursor=True,
            ),
        ])

        return Shadow(body=body)

    def _handle_accept(self, buffer):
        text = buffer.text.strip()
        if text and text != "IP:PORT":
            self.tui._handle_direct_connect(text)

    def clear(self):
        if self.textarea:
            self._placeholder = True
            self.textarea.text = "IP:PORT"
            self.textarea.buffer.cursor_position = 0
