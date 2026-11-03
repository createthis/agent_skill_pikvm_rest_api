# KVMD web keymap reference

Key names accepted by the PiKVM/KVMD REST API `key`, `shortcut`, and `keys=` arguments.
These are the `web_name` values from the KVMD keymap. evdev names (e.g. `Super_L`, `KEY_A`) and
X11 names (e.g. `XK_a`) are **not** accepted by the API.

macOS equivalents: `MetaLeft`/`MetaRight` = ⌘ Command, `AltLeft`/`AltRight` = ⌥ Option,
`ControlLeft`/`ControlRight` = ⌃ Control.

| web_name | common / macOS | X11 name |
| --- | --- | --- |
| `KeyA` | A | XK_A |
| `KeyB` | B | XK_B |
| `KeyC` | C | XK_C |
| `KeyD` | D | XK_D |
| `KeyE` | E | XK_E |
| `KeyF` | F | XK_F |
| `KeyG` | G | XK_G |
| `KeyH` | H | XK_H |
| `KeyI` | I | XK_I |
| `KeyJ` | J | XK_J |
| `KeyK` | K | XK_K |
| `KeyL` | L | XK_L |
| `KeyM` | M | XK_M |
| `KeyN` | N | XK_N |
| `KeyO` | O | XK_O |
| `KeyP` | P | XK_P |
| `KeyQ` | Q | XK_Q |
| `KeyR` | R | XK_R |
| `KeyS` | S | XK_S |
| `KeyT` | T | XK_T |
| `KeyU` | U | XK_U |
| `KeyV` | V | XK_V |
| `KeyW` | W | XK_W |
| `KeyX` | X | XK_X |
| `KeyY` | Y | XK_Y |
| `KeyZ` | Z | XK_Z |
| `Digit1` | Digit1 | XK_exclam |
| `Digit2` | Digit2 | XK_at |
| `Digit3` | Digit3 | XK_numbersign |
| `Digit4` | Digit4 | XK_dollar |
| `Digit5` | Digit5 | XK_percent |
| `Digit6` | Digit6 | XK_asciicircum |
| `Digit7` | Digit7 | XK_ampersand |
| `Digit8` | Digit8 | XK_asterisk |
| `Digit9` | Digit9 | XK_parenleft |
| `Digit0` | Digit0 | XK_parenright |
| `Enter` | Enter | XK_Return |
| `Escape` | Escape | XK_Escape |
| `Backspace` | Backspace | XK_BackSpace |
| `Tab` | Tab | XK_Tab |
| `Space` | Space | XK_space |
| `Minus` | Minus | XK_underscore |
| `Equal` | Equal | XK_plus |
| `BracketLeft` | BracketLeft | XK_braceleft |
| `BracketRight` | BracketRight | XK_braceright |
| `Backslash` | Backslash | XK_bar |
| `Semicolon` | Semicolon | XK_colon |
| `Quote` | Quote | XK_quotedbl |
| `Backquote` | Backquote | XK_asciitilde |
| `Comma` | Comma | XK_less |
| `Period` | Period | XK_greater |
| `Slash` | Slash | XK_question |
| `CapsLock` | CapsLock | XK_Caps_Lock |
| `F1` | F1 | XK_F1 |
| `F2` | F2 | XK_F2 |
| `F3` | F3 | XK_F3 |
| `F4` | F4 | XK_F4 |
| `F5` | F5 | XK_F5 |
| `F6` | F6 | XK_F6 |
| `F7` | F7 | XK_F7 |
| `F8` | F8 | XK_F8 |
| `F9` | F9 | XK_F9 |
| `F10` | F10 | XK_F10 |
| `F11` | F11 | XK_F11 |
| `F12` | F12 | XK_F12 |
| `PrintScreen` | PrintScreen | XK_Sys_Req |
| `Insert` | Insert | XK_Insert |
| `Home` | Home | XK_Home |
| `PageUp` | PageUp | XK_Page_Up |
| `Delete` | Delete | XK_Delete |
| `End` | End | XK_End |
| `PageDown` | PageDown | XK_Page_Down |
| `ArrowRight` | ArrowRight | XK_Right |
| `ArrowLeft` | ArrowLeft | XK_Left |
| `ArrowDown` | ArrowDown | XK_Down |
| `ArrowUp` | ArrowUp | XK_Up |
| `ControlLeft` | ControlLeft | XK_Control_L |
| `ShiftLeft` | ShiftLeft | XK_Shift_L |
| `AltLeft` | AltLeft | XK_Alt_L |
| `MetaLeft` | MetaLeft | XK_Meta_L |
| `ControlRight` | ControlRight | XK_Control_R |
| `ShiftRight` | ShiftRight | XK_Shift_R |
| `AltRight` | AltRight | XK_Alt_R |
| `MetaRight` | MetaRight | XK_Meta_R |
| `Pause` | Pause | XK_Pause |
| `ScrollLock` | ScrollLock | XK_Scroll_Lock |
| `NumLock` | NumLock | XK_Num_Lock |
| `ContextMenu` | ContextMenu | XK_Menu |
| `NumpadDivide` | NumpadDivide | XK_KP_Divide |
| `NumpadMultiply` | NumpadMultiply | XK_multiply |
| `NumpadSubtract` | NumpadSubtract | XK_KP_Subtract |
| `NumpadAdd` | NumpadAdd | XK_KP_Add |
| `NumpadEnter` | NumpadEnter | XK_KP_Enter |
| `Numpad1` | Numpad1 | XK_KP_1 |
| `Numpad2` | Numpad2 | XK_KP_2 |
| `Numpad3` | Numpad3 | XK_KP_3 |
| `Numpad4` | Numpad4 | XK_KP_4 |
| `Numpad5` | Numpad5 | XK_KP_5 |
| `Numpad6` | Numpad6 | XK_KP_6 |
| `Numpad7` | Numpad7 | XK_KP_7 |
| `Numpad8` | Numpad8 | XK_KP_8 |
| `Numpad9` | Numpad9 | XK_KP_9 |
| `Numpad0` | Numpad0 | XK_KP_0 |
| `NumpadDecimal` | NumpadDecimal | XK_KP_Decimal |
| `Power` | Power | XK_XF86_Sleep |
| `IntlBackslash` | IntlBackslash |  |
| `IntlYen` | IntlYen |  |
| `IntlRo` | IntlRo |  |
| `KanaMode` | KanaMode |  |
| `Convert` | Convert |  |
| `NonConvert` | NonConvert |  |
| `AudioVolumeMute` | AudioVolumeMute |  |
| `AudioVolumeUp` | AudioVolumeUp |  |
| `AudioVolumeDown` | AudioVolumeDown |  |
| `F20` | F20 |  |
| `F21` | F21 |  |
| `F22` | F22 |  |
| `F23` | F23 |  |
| `F24` | F24 |  |
| `F13` | F13 |  |
| `F14` | F14 |  |
| `F15` | F15 |  |
| `F16` | F16 |  |
| `F17` | F17 |  |
| `F18` | F18 |  |
| `F19` | F19 |  |
