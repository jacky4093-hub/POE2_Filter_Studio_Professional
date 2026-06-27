# MainWindow Behavior Contract (P12.0)

This document records the current MainWindow behavior contract so the upcoming P12 refactor can preserve the existing UI and test surface without changing functionality.

## 1. Current responsibilities of MainWindow

MainWindow is the top-level façade for the editor workflow. It currently owns:

- creating and wiring the main editor UI shell
- coordinating document state, file I/O, and dirty tracking
- bridging user interactions between widgets and the document model
- maintaining search/category/filter state and UI synchronization
- handling welcome screen, recent files, and startup restore flows

It is not a pure view. It still acts as the orchestration layer between:

- FilterDocument
- RuleCardBrowser
- RuleDetailEditor
- PreviewPanel
- category/search UI widgets
- settings and recent-file state

## 2. P12 refactor must preserve these façade responsibilities

The P12 refactor should keep MainWindow as the public façade for the editor shell. It must continue to expose the same high-level behavior and widget access points that current tests and UI flows rely on.

The following should remain intact:

- the main window lifecycle and startup behavior
- file open/save/new actions
- category and search-driven refresh behavior
- selection synchronization between the rule list and detail editor
- preview updates when rules are selected or cleared
- undo/redo integration with pending editor edits
- recent-files and welcome-screen synchronization

## 3. Widget attributes that must remain available

These attributes are part of the existing contract and should not be renamed or removed during P12:

- welcome_screen
- rule_card_browser
- filter_search_bar
- search_bar
- category_sidebar
- rule_detail_editor
- preview_panel

The detail editor façade is currently exposed as `rule_detail_editor`.

## 4. Behaviors that must be preserved

The following behaviors are part of the current contract and should remain unchanged in P12:

- startup restore silent failure: invalid or missing startup restore files must not show a modal dialog
- load_file resets category and search state after loading a new file
- save success clears the dirty state
- when a selected rule becomes filtered out, the editor and preview are cleared
- recent files and welcome screen stay synchronized after preference changes or file operations
- undo/redo flushes pending editor edits before applying changes

## 5. Explicit non-goals for P12 initial phase

The initial P12 work must not:

- rewrite MainWindow wholesale
- rename any public signals or widget attributes
- introduce a new controller/presenter layer prematurely
- extract FileSessionController or similar abstractions
- change parser/exporter behavior
- change core document/model/command semantics

## 6. Practical interpretation for future refactors

P12 should be treated as a structural extraction step, not a behavior change.

In practice, this means:

- preserve the current public façade surface
- keep existing widget wiring alive for now
- keep the current signal names and attribute names stable
- defer any deeper separation until after the façade contract is locked in
