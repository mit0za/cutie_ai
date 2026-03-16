# 纯语义检索管道 & 文档搜索视图 - 设计方案

## 一、任务概述

| 任务 | 描述 |
|------|------|
| **Task 1** | 实现 Pure Semantic Retrieval Pipeline：基于 VectorIndexRetriever 的纯检索管道，绕过 LLM，直接返回 Node 列表 |
| **Task 2** | 设计 Document Search 视图：独立的文档搜索界面，支持查询输入与检索结果的可视化展示 |

---

## 二、当前架构分析

### 2.1 现有数据流

```
用户输入 → ChatInterface → PushButtonController → QueryWorker
                                              ↓
                                    CitationQueryEngine.query()
                                              ↓
                            [Index Retriever] → [Reranker] → [LLM 生成] → 响应文本
                                              ↓
                                    response.source_nodes (附带引用)
```

- **EngineManager** 构建 `CitationQueryEngine`，内部包含：Retriever + Reranker + LLM
- **QueryWorker** 调用 `engine.query()`，始终经过 LLM 生成
- 检索到的 Node 仅作为 `source_nodes` 附带在响应中，无法单独使用

### 2.2 目标架构

```
                    ┌─────────────────────────────────────┐
                    │           EngineManager              │
                    │  (共享: index, vector_store, reranker)│
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ CitationQuery   │  │ VectorIndex     │  │ (未来扩展)       │
    │ Engine (Q&A)    │  │ Retriever       │  │                 │
    │ + LLM           │  │ (纯检索)         │  │                 │
    └────────┬────────┘  └────────┬────────┘  └─────────────────┘
             │                    │
             ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐
    │ ChatInterface   │  │ SearchInterface │
    │ Q&A 对话        │  │ 文档搜索        │
    └─────────────────┘  └─────────────────┘
```

---

## 三、Task 1：Pure Semantic Retrieval Pipeline

### 3.1 设计目标

- 复用现有 `VectorStoreIndex`，不增加额外存储
- 使用 `VectorIndexRetriever`（即 `index.as_retriever()`）进行纯语义检索
- 可选：复用 Reranker 做后处理，提升相关性
- **不加载、不调用 LLM**，节省算力与延迟

### 3.2 实现方案

#### 3.2.1 新增信号与返回值

在 `EngineManager` 中：

- 新增信号：`retriever_ready = Signal(object)`，传递 `BaseRetriever` 对象
- 在构建完 `index` 后，构建 Retriever 并发出信号

#### 3.2.2 Retriever 构建逻辑

```python
# 伪代码
retriever = index.as_retriever(
    similarity_top_k=10,  # 可配置，如 20
    node_postprocessors=[reranker]  # 可选，与 Q&A 共用
)
self.retriever_ready.emit(retriever)
```

- `index.as_retriever()` 返回 `VectorIndexRetriever`
- 支持 `node_postprocessors`，可传入 `SentenceTransformerRerank` 做重排序

#### 3.2.3 检索接口

```python
# 纯检索：返回 List[NodeWithScore]
nodes = retriever.retrieve(query_str)
# 每个 node 含: node.node (Node), node.score
```

#### 3.2.4 文件结构

| 文件 | 变更 |
|------|------|
| `backend/engine_manager.py` | 构建 retriever，发出 `retriever_ready` |
| `backend/retrieval_worker.py` | **新建**：后台检索 Worker，输入 query，输出 `List[NodeWithScore]` |
| `ui/controller/engine_controller.py` | 订阅 `retriever_ready`，保存 retriever 引用 |
| `ui/controller/search_controller.py` | **新建**：封装检索触发与结果回调 |

### 3.3 与 Chat 管道的复用关系

| 组件 | Q&A 管道 | 纯检索管道 |
|------|----------|------------|
| Index | ✓ 共用 | ✓ 共用 |
| Embedding | ✓ 共用 | ✓ 共用 |
| Reranker | ✓ 共用 | ✓ 可选 |
| LLM | ✓ 使用 | ✗ 不使用 |

---

## 四、Task 2：Document Search 视图与数据可视化

### 4.1 设计目标

- 独立于 Chat 的「文档搜索」视图
- 用户输入查询 → 触发纯检索 → 展示文档列表
- 支持对检索结果的可视化「消化」：标题、来源、摘要、相关性分数等

### 4.2 UI 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│  Document Search                                    [图标]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐  [Search]  │
│  │ 输入搜索关键词...                             │            │
│  └─────────────────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  检索结果 (共 N 条)                                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ #1  score: 0.89  │  document.pdf                        ││
│  │ 摘要: ...相关文本片段...                                  ││
│  │ [打开文件]                                                ││
│  ├─────────────────────────────────────────────────────────┤│
│  │ #2  score: 0.85  │  report.docx                          ││
│  │ 摘要: ...                                                ││
│  │ [打开文件]                                                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 4.3 组件设计

#### 4.3.1 新建视图：`SearchInterface`

| 元素 | 类型 | 说明 |
|------|------|------|
| 搜索框 | `SearchLineEdit` / `TextEdit` | 单行输入，支持回车触发 |
| 搜索按钮 | `PrimaryPushButton` | 与 Chat 风格一致 |
| 结果列表 | `ScrollArea` + `Card` 列表 | 每个结果一张卡片 |
| 结果卡片 | `SettingCard` / 自定义 `QFrame` | 展示：序号、分数、文件名、摘要、打开按钮 |

#### 4.3.2 单条结果卡片字段

| 字段 | 来源 | 展示方式 |
|------|------|----------|
| 序号 | 列表索引 | 左上角 #1, #2... |
| 相关性分数 | `NodeWithScore.score` | 0.00–1.00，可颜色区分 |
| 文件名 | `node.metadata["file_name"]` | 粗体标题 |
| 文件路径 | `node.metadata["file_path"]` | 小字或 tooltip |
| 文本摘要 | `node.text` | 截断 200–300 字，可展开 |
| 操作 | - | 「打开文件」按钮，调用 `QDesktopServices.openUrl(file://path)` |

#### 4.3.3 侧边栏集成

在 `MainWindow.initSidebar()` 中：

```python
self.searchInterface = SearchInterface(self)
self.addSubInterface(self.searchInterface, FluentIcon.SEARCH, self.tr("Document Search"))
# 置于 Chat 与 Settings 之间
```

### 4.4 数据流

```
SearchInterface 输入
       ↓
SearchController.on_search_clicked()
       ↓
RetrievalWorker (QThread)
       ↓
retriever.retrieve(query)  →  List[NodeWithScore]
       ↓
RetrievalWorker.finished.emit(nodes)
       ↓
SearchInterface.display_results(nodes)
       ↓
渲染结果卡片列表
```

---

## 五、实现步骤（推荐顺序）

### Phase 1：后端 - 纯检索管道

1. **修改 `engine_manager.py`**
   - 在 `index` 构建完成后，创建 `retriever = index.as_retriever(similarity_top_k=20, node_postprocessors=[reranker])`
   - 新增信号 `retriever_ready = Signal(object)`
   - 发出 `retriever_ready.emit(retriever)`

2. **新建 `backend/retrieval_worker.py`**
   - 类 `RetrievalWorker(QObject)`，接收 `retriever` 和 `query`
   - `run()` 中调用 `retriever.retrieve(query)`，发出 `finished.emit(nodes)`
   - 错误时发出 `error.emit(str)`

3. **修改 `engine_controller.py`**
   - 订阅 `retriever_ready`，保存 `self.retriever`
   - 提供 `get_retriever()` 或直接暴露 `retriever` 给 SearchInterface

### Phase 2：前端 - Document Search 视图

4. **新建 `ui/view/search_interface.py`**
   - 搜索框 + 搜索按钮
   - 结果区域（初始为空或提示文案）
   - 引用 `SearchController`

5. **新建 `ui/controller/search_controller.py`**
   - 持有 `EngineController` 或 `retriever` 引用
   - 处理搜索点击，启动 `RetrievalWorker`
   - 连接 `finished` → 调用 `SearchInterface.display_results(nodes)`

6. **实现结果卡片组件**
   - 可放在 `search_interface.py` 内或单独 `search_result_card.py`
   - 解析 `NodeWithScore`，展示字段并支持「打开文件」

7. **集成到 MainWindow**
   - 添加 `SearchInterface` 到侧边栏
   - 确保 `EngineController` 在应用启动时初始化，且 `retriever` 与 `query_engine` 一同就绪

### Phase 3：联调与优化

8. **状态与错误处理**
   - Retriever 未就绪时禁用搜索按钮，提示「等待索引加载」
   - 检索失败时 InfoBar 提示

9. **可选增强**
   - 结果数量可配置（如 10 / 20 / 50）
   - 分数阈值过滤
   - 按分数排序、高亮关键词

---

## 六、关键代码参考

### 6.1 Retriever 构建（engine_manager.py）

```python
# 在 index 构建完成后
retriever = index.as_retriever(
    similarity_top_k=20,
    node_postprocessors=[reranker]
)
self.retriever_ready.emit(retriever)
```

### 6.2 Node 数据结构

```python
# NodeWithScore
node_with_score.node      # Node 对象
node_with_score.node.text # 文本内容
node_with_score.node.metadata  # {"file_name", "file_path", ...}
node_with_score.score     # float 相关性分数
```

### 6.3 检索调用

```python
nodes = retriever.retrieve("用户输入的查询")
# nodes: List[NodeWithScore]
```

---

## 七、文件变更清单

| 操作 | 路径 |
|------|------|
| 修改 | `backend/engine_manager.py` |
| 新建 | `backend/retrieval_worker.py` |
| 修改 | `ui/controller/engine_controller.py` |
| 新建 | `ui/controller/search_controller.py` |
| 新建 | `ui/view/search_interface.py` |
| 修改 | `ui/main_window.py` |

---

## 八、验收标准

- [ ] 纯检索管道不调用 LLM，仅使用 Embedding + 可选 Reranker
- [ ] 检索返回 `List[NodeWithScore]`，可被 UI 直接消费
- [ ] Document Search 视图独立于 Chat，有独立入口
- [ ] 用户可输入查询并看到文档列表（含分数、文件名、摘要）
- [ ] 支持从结果卡片打开本地文件
