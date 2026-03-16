# Task 1 & Task 2 完成说明 —— 给组员们的修改说明

大家好，我在大家现有工作的基础上完成了 **Task 1（纯语义检索管道）** 和 **Task 2（Document Search 视图）**。下面按任务说明我做了哪些修改，方便大家 review 和后续维护。

---

## 一、先说一下整体思路

现有架构里，EngineManager 已经构建了 CitationQueryEngine（Retriever + Reranker + LLM），Chat 对话走的是完整 Q&A 流程。我这次做的是：

1. **Task 1**：在 EngineManager 里额外暴露一个「纯检索」的 retriever，不经过 LLM，直接返回 Node 列表。
2. **Task 2**：新增一个 Document Search 视图，用这个 retriever 做语义检索，把结果用卡片形式展示出来。

两个任务都尽量复用大家已有的 index、embedding、vector store，只做必要的扩展。

---

## 二、环境与运行相关（顺带做的）

### 2.1 工作目录 (`main.py`)

我在 `main()` 开头加了 `os.chdir(app_dir)`，保证 `./data`、`./models`、`./chroma_db` 等相对路径能正确解析。之前在不同目录下启动时，这些路径可能会跑偏。

### 2.2 Windows 依赖 (`requirements-windows.txt`)

新增了一个 `requirements-windows.txt`，去掉了 ROCm、uvloop 等 Linux 专用包，方便在 Windows 上安装和运行。大家如果在 Windows 上跑，可以用这个文件。

### 2.3 默认数据路径 (`backend/engine_manager.py`)

在 engine_manager 里加了一个 fallback：当 Settings 里没配置数据路径、且索引为空时，自动用 `./data`。这样新同学拉下来跑的时候，只要往 `./data` 放文件就能用。

### 2.4 LLM 文件名兼容 (`backend/engine_manager.py`)

LLM 模型文件名支持了 `Q6_K_L` 和 `Q6_K` 两种，按顺序尝试加载，避免因为量化版本不同而报错。

---

## 三、Task 1：纯语义检索管道

### 3.1 在 EngineManager 里加的 (`backend/engine_manager.py`)

- 新增信号：`retriever_ready = Signal(object)`
- 在 `query_engine` 就绪后，用 `index.as_retriever(similarity_top_k=20)` 创建一个纯检索器，然后 `emit(retriever)`

注意：`VectorIndexRetriever` 不支持 `node_postprocessors`，所以这里没有接 Reranker，返回的是原始检索结果。如果后面需要重排，可以再讨论方案。

### 3.2 新建 RetrievalWorker (`backend/retrieval_worker.py`)

新建了这个文件，里面有两个东西：

- **`_node_to_dict(nws)`**：把 LlamaIndex 的 `NodeWithScore` 转成纯 Python dict（`text`、`score`、`metadata`），metadata 里的值都转成 str，方便跨线程和序列化。
- **`RetrievalWorker`**：接收 retriever 和 query，执行 `retrieve()`，可以发出 `finished` 或 `error` 信号。

目前 SearchController 是**在主线程同步调用** retriever，没有用 QThread，所以 RetrievalWorker 主要是提供 `_node_to_dict` 这个转换函数。如果以后要改成后台线程检索，可以直接用这个 Worker。

### 3.3 EngineController 的改动 (`ui/controller/engine_controller.py`)

- 让 EngineController 继承 `QObject`，并新增 `chat_ready` 信号，供 ChatInterface 启用发送按钮。
- 订阅 `retriever_ready`，在 `on_retriever_ready` 里保存 `self.retriever`。
- 重启引擎时把 `self.retriever` 置为 `None`，并重新订阅信号。

这样 Chat 和 Document Search 都能共用同一个 EngineController，retriever 在引擎就绪后自动可用。

---

## 四、Task 2：Document Search 视图

### 4.1 MainWindow 的改动 (`ui/main_window.py`)

- 在 MainWindow 里创建**共享的** `EngineController`，传给 ChatInterface 和 SearchInterface。
- 新建 `SearchInterface`，传入 `engine_controller`。
- 在侧边栏加了一个 Document Search 入口（FluentIcon.SEARCH），和 Chat、Settings 并列。

### 4.2 新建 SearchInterface (`ui/view/search_interface.py`)

新建了完整的文档搜索界面，包括：

- **SearchLineEdit**：搜索框，支持回车和搜索按钮触发。
- **SearchResultCard**：单条结果卡片，展示序号、分数、文件名、摘要、以及「打开文件」按钮。
- **results_container**：用 `QVBoxLayout` 放结果卡片。
- **display_results(nodes)**：接收 dict 列表，先清空旧卡片，再渲染新结果。
- **`_refresh_results_layout()`**：用 `QTimer.singleShot(0, ...)` 延迟一帧刷新布局，避免 ScrollArea 内容尺寸算错。

样式上尽量和 Settings 界面保持一致，用了 `StyleSheet.SETTING_INTERFACE`。

### 4.3 新建 SearchController (`ui/controller/search_controller.py`)

新建了 SearchController，负责：

- 校验空查询、retriever 是否就绪。
- **在主线程同步执行** `retriever.retrieve(query)`，用 `_node_to_dict` 转成 dict 后调用 `parent.display_results(data)`。
- 出错时用 InfoBar 提示。

选择主线程同步检索，是因为之前试过 QThread + 信号传递 `NodeWithScore`，Qt 跨线程 pickle 会有问题，结果传过去后卡片不显示。改成主线程后检索速度还可以接受，界面也不会卡太久。

### 4.4 ChatInterface 的改动 (`ui/view/chat_interface.py`)

- `__init__` 增加参数 `engine_controller=None`，可以接收外部传入的 EngineController。
- 用 `chat_ready` 信号启用发送按钮，不再在 ChatInterface 内部单独创建 EngineController。
- 如果没传 `engine_controller`，则 fallback 成自己创建一个（兼容旧用法）。

---

## 五、检索结果不显示的问题（踩坑记录）

实现过程中遇到：检索执行后显示 "Found N result(s)"，但下面的卡片不显示。

**原因**：
1. Qt 跨线程信号会 pickle 参数，LlamaIndex 的 `NodeWithScore` 序列化有问题。
2. ScrollArea 在动态添加内容后，布局需要延迟一帧才能正确计算尺寸。

**解决**：
1. 改成主线程同步检索，不再用 QThread 传复杂对象。
2. 用 `_node_to_dict` 把结果转成纯 Python dict 再传给 UI。
3. 在 `display_results` 末尾用 `QTimer.singleShot(0, self._refresh_results_layout)` 触发布局刷新。

如果大家有更好的方案（比如继续用后台线程但换一种数据传递方式），可以一起优化。

---

## 六、测试脚本

新增了 `test_retrieval.py`，用于在命令行验证纯语义检索，不依赖 UI：

```bash
python test_retrieval.py [查询词]
# 示例: python test_retrieval.py "welcome"
```

会启动 EngineManager，等 retriever 就绪后执行检索，并打印序号、分数、文件名、摘要片段。

---

## 七、文件变更一览

| 类型 | 文件 | 我做的改动 |
|------|------|------------|
| 修改 | `main.py` | 加 `os.chdir(app_dir)` |
| 修改 | `backend/engine_manager.py` | `retriever_ready` 信号、默认数据路径、LLM 文件名兼容、构建 retriever |
| 新增 | `backend/retrieval_worker.py` | RetrievalWorker、_node_to_dict |
| 修改 | `ui/controller/engine_controller.py` | 继承 QObject、chat_ready、订阅 retriever_ready、保存 retriever |
| 新增 | `ui/controller/search_controller.py` | SearchController |
| 新增 | `ui/view/search_interface.py` | SearchInterface、SearchResultCard |
| 修改 | `ui/view/chat_interface.py` | 接收 engine_controller、chat_ready 启用发送 |
| 修改 | `ui/main_window.py` | 共享 EngineController、添加 Document Search 入口 |
| 新增 | `requirements-windows.txt` | Windows 兼容依赖 |
| 新增 | `test_retrieval.py` | 命令行检索测试 |

---

## 八、参考

- [DESIGN_PURE_RETRIEVAL_AND_SEARCH_VIEW.md](./DESIGN_PURE_RETRIEVAL_AND_SEARCH_VIEW.md) - 设计文档
- [CHANGELOG_MODIFICATIONS_EN.md](./CHANGELOG_MODIFICATIONS_EN.md) - 英文版说明
