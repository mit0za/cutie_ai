#!/usr/bin/env python3
"""
测试纯语义检索管道 (Pure Semantic Retrieval)
运行: python test_retrieval.py [查询词]
示例: python test_retrieval.py "welcome"
"""
import os
import sys
from PySide6.QtWidgets import QApplication

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from backend.engine_manager import EngineManager


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "welcome"
    app = QApplication(sys.argv)

    retriever_ref = [None]
    results_ref = [None]

    def on_retriever_ready(r):
        retriever_ref[0] = r
        print("\n[OK] Retriever 已就绪，开始检索...")
        run_retrieval(r, query, results_ref, app)

    def on_error(e):
        print(f"\n[ERROR] {e}")
        app.quit()

    def on_critical(e):
        print(f"\n[CRITICAL] {e}")
        app.quit()

    print("初始化引擎 (加载 LLM、Embedding、Index)...")
    engine = EngineManager()
    engine.retriever_ready.connect(on_retriever_ready)
    engine.error.connect(on_error)
    engine.critical_error.connect(on_critical)
    engine.start()

    app.exec()

    if results_ref[0] is not None:
        print("\n" + "=" * 60)
        print("检索测试完成")
        print("=" * 60)


def run_retrieval(retriever, query, results_ref, app):
    """执行检索（主线程，retrieve 较快）"""
    try:
        nodes = retriever.retrieve(query)
        results_ref[0] = nodes
        print(f"\n检索到 {len(nodes)} 条结果:")
        print("-" * 50)
        for i, nws in enumerate(nodes, 1):
            node = nws.node
            score = nws.score
            meta = getattr(node, "metadata", {}) or {}
            fname = meta.get("file_name") or meta.get("source") or "Unknown"
            text = (getattr(node, "text", "") or "")[:150].replace("\n", " ")
            print(f"  #{i} score={score:.4f} | {fname}")
            print(f"      {text}...")
        print("-" * 50)
    except Exception as e:
        print(f"[ERROR] {e}")
    app.quit()


if __name__ == "__main__":
    main()
