# Task 1 & Task 2 Completion Summary — Changes for the Team

Hi everyone, I’ve finished **Task 1 (Pure Semantic Retrieval Pipeline)** and **Task 2 (Document Search View)** on top of the existing codebase. Here’s what I changed so you can review and maintain it.

---

## 1. Overview

The current setup already has EngineManager building CitationQueryEngine (Retriever + Reranker + LLM), and Chat uses the full Q&A flow. What I added:

1. **Task 1**: Expose a “pure retrieval” retriever from EngineManager that skips the LLM and returns raw Node lists.
2. **Task 2**: Add a Document Search view that uses this retriever for semantic search and shows results as cards.

Both tasks reuse the existing index, embedding, and vector store where possible.

---

## 2. Environment and Runtime (Minor Fixes)

### 2.1 Working Directory (`main.py`)

Added `os.chdir(app_dir)` at the start of `main()` so relative paths like `./data`, `./models`, and `./chroma_db` resolve correctly when the app is started from different directories.

### 2.2 Windows Dependencies (`requirements-windows.txt`)

Added `requirements-windows.txt` without ROCm, uvloop, etc., for easier installation on Windows.

### 2.3 Default Data Path (`backend/engine_manager.py`)

Added a fallback: when no data path is configured in Settings and the index is empty, use `./data` so new setups can just drop files there.

### 2.4 LLM Filename Compatibility (`backend/engine_manager.py`)

Support both `Q6_K_L` and `Q6_K` GGUF filenames and try them in order to avoid failures from different quantization versions.

---

## 3. Task 1: Pure Semantic Retrieval Pipeline

### 3.1 Changes in EngineManager (`backend/engine_manager.py`)

- New signal: `retriever_ready = Signal(object)`
- After `query_engine` is ready, create `retriever = index.as_retriever(similarity_top_k=20)` and emit it

Note: `VectorIndexRetriever` doesn’t support `node_postprocessors`, so Reranker isn’t used here; it returns raw retrieval results. We can revisit if we want reranking later.

### 3.2 New RetrievalWorker (`backend/retrieval_worker.py`)

Added this file with:

- **`_node_to_dict(nws)`**: Converts LlamaIndex `NodeWithScore` to a plain Python dict (`text`, `score`, `metadata`), with metadata values converted to str for cross-thread/serialization safety.
- **`RetrievalWorker`**: Takes retriever and query, runs `retrieve()`, can emit `finished` or `error`.

Right now SearchController calls the retriever **synchronously on the main thread**, so RetrievalWorker mainly provides `_node_to_dict`. If we move retrieval to a background thread later, we can use this Worker.

### 3.3 EngineController Changes (`ui/controller/engine_controller.py`)

- EngineController now inherits `QObject` and has a `chat_ready` signal for ChatInterface to enable the send button.
- Subscribes to `retriever_ready` and stores `self.retriever` in `on_retriever_ready`.
- On engine restart, sets `self.retriever = None` and re-subscribes.

Chat and Document Search share the same EngineController, and the retriever becomes available once the engine is ready.

---

## 4. Task 2: Document Search View

### 4.1 MainWindow Changes (`ui/main_window.py`)

- Create a **shared** `EngineController` and pass it to ChatInterface and SearchInterface.
- Add `SearchInterface` and pass `engine_controller`.
- Add a Document Search entry in the sidebar (FluentIcon.SEARCH) next to Chat and Settings.

### 4.2 New SearchInterface (`ui/view/search_interface.py`)

New document search UI with:

- **SearchLineEdit**: Search box, supports Enter and search button.
- **SearchResultCard**: Single result card with rank, score, filename, excerpt, and “Open File” button.
- **results_container**: Uses `QVBoxLayout` for the result cards.
- **display_results(nodes)**: Accepts a list of dicts, clears old cards, then renders new results.
- **`_refresh_results_layout()`**: Uses `QTimer.singleShot(0, ...)` to defer layout refresh so the ScrollArea computes content size correctly.

Styling follows the Settings interface using `StyleSheet.SETTING_INTERFACE`.

### 4.3 New SearchController (`ui/controller/search_controller.py`)

Handles:

- Validating empty query and retriever readiness.
- **Synchronous** `retriever.retrieve(query)` on the main thread, converts with `_node_to_dict`, then calls `parent.display_results(data)`.
- Shows errors via InfoBar.

I chose main-thread retrieval because QThread + signals with `NodeWithScore` caused Qt cross-thread pickle issues and the cards didn’t show. Synchronous retrieval is fast enough and doesn’t block the UI for long.

### 4.4 ChatInterface Changes (`ui/view/chat_interface.py`)

- Added `engine_controller=None` to `__init__` to accept an external EngineController.
- Uses `chat_ready` to enable the send button instead of creating its own EngineController.
- If no `engine_controller` is passed, falls back to creating one (keeps old behavior).

---

## 5. Search Results Not Showing (Debugging Notes)

During implementation, results showed “Found N result(s)” but the cards didn’t appear.

**Causes**:
1. Qt cross-thread signals pickle arguments; LlamaIndex `NodeWithScore` doesn’t serialize well.
2. ScrollArea needs a deferred layout update after dynamic content changes.

**Fixes**:
1. Switched to main-thread synchronous retrieval instead of QThread with complex objects.
2. Use `_node_to_dict` to convert results to plain Python dicts before passing to the UI.
3. Call `QTimer.singleShot(0, self._refresh_results_layout)` at the end of `display_results` to refresh layout.

If you have a better approach (e.g., keep background thread but change how data is passed), we can refine this.

---

## 6. Test Script

Added `test_retrieval.py` for command-line testing of pure semantic retrieval without the UI:

```bash
python test_retrieval.py [query]
# Example: python test_retrieval.py "welcome"
```

It starts EngineManager, waits for retriever readiness, runs retrieval, and prints rank, score, filename, and excerpt.

---

## 7. File Change Summary

| Type   | File                              | Changes |
|--------|-----------------------------------|---------|
| Modified | `main.py`                       | Added `os.chdir(app_dir)` |
| Modified | `backend/engine_manager.py`     | `retriever_ready` signal, default data path, LLM filename compatibility, retriever creation |
| Added  | `backend/retrieval_worker.py`    | RetrievalWorker, _node_to_dict |
| Modified | `ui/controller/engine_controller.py` | Inherit QObject, chat_ready, subscribe to retriever_ready, store retriever |
| Added  | `ui/controller/search_controller.py` | SearchController |
| Added  | `ui/view/search_interface.py`    | SearchInterface, SearchResultCard |
| Modified | `ui/view/chat_interface.py`     | Accept engine_controller, chat_ready enables send |
| Modified | `ui/main_window.py`              | Shared EngineController, Document Search entry |
| Added  | `requirements-windows.txt`      | Windows-compatible dependencies |
| Added  | `test_retrieval.py`              | Command-line retrieval test |

---

## 8. References

- [DESIGN_PURE_RETRIEVAL_AND_SEARCH_VIEW.md](./DESIGN_PURE_RETRIEVAL_AND_SEARCH_VIEW.md) - Design doc
- [CHANGELOG_MODIFICATIONS.md](./CHANGELOG_MODIFICATIONS.md) - Chinese version

Feel free to reach out if you have questions or suggestions.
