import os
import torch
import shutil
from typing import Union, List
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from PySide6.QtCore import QMetaObject, Qt
from utils.metadata_extractor import MetaDataExtractor
from llama_index.readers.file import DocxReader, PDFReader
import math

# TODO[Engine]: Re-enable multiprocessing once GUI-safe process spawning is implemented.
# Issue: PySide6 event loop + multiprocessing.spawn causes deadlock on Windows.
# Suggested fix: Move ingestion to standalone process via multiprocessing.Process or subprocess.Popen().


def load_or_create_index(vector_store, storage_context, data_path: Union[str, List[str]] = "./data", callback=None):
    """
    Load an index from the vector store if it has data else build a new index.
    Supports multiple data paths.
    """

    def log(msg: str):
        print(msg)
        if callback:
            try:
                if hasattr(callback, "__self__") and hasattr(callback.__self__, "metaObject"):
                    QMetaObject.invokeMethod(
                        callback.__self__,
                        callback.__name__ if hasattr(callback, "__name__") else "emit",
                        Qt.QueuedConnection,
                        args=(msg,)
                    )
                else:
                    callback(msg)
            except Exception as e:
                print(f"[Callback Error] {e}")

    # Normalize and validate data paths
    if isinstance(data_path, str):
        data_paths = [data_path]
    else:
        data_paths = data_path

    valid_paths = [p for p in data_paths if os.path.exists(p)]
    if not valid_paths:
        log("[Warning] No valid data folders found. Using ./data as fallback.")
        valid_paths = ["./data"]

    # Explicitly define extractors so llamaindex know which lib to use
    file_extractor = {
        ".docx": DocxReader(),
        ".pdf": PDFReader(return_full_document=True)
    }

    # Count current collection
    get_collection = vector_store._collection.count()

    if get_collection == 0:
        log(f"Index empty. Rebuilding from {valid_paths} (this may take a while)...")

        # Load documents from each data folder, reporting progress per-folder
        documents = []
        for i, path in enumerate(valid_paths):
            log(f"[{i+1}/{len(valid_paths)}] Loading documents from: {path}")
            reader = SimpleDirectoryReader(
                path,
                file_extractor=file_extractor,
                recursive=True)
            docs = reader.load_data(show_progress=True)
            log(f"[{i+1}/{len(valid_paths)}] Loaded {len(docs)} documents from {path}")
            documents.extend(docs)

        # Copy source files into chroma_db/documents/ so the database is fully
        # self-contained. Recipients only need the chroma_db/ folder to get both
        # the vector index and the original reference files without re-indexing.
        docs_dir = os.path.join(".", "chroma_db", "documents")
        os.makedirs(docs_dir, exist_ok=True)
        copied = set()
        for doc in documents:
            abs_path = doc.metadata.get("file_path", "")
            if not abs_path or not os.path.isfile(abs_path):
                continue
            file_name = os.path.basename(abs_path)
            dest = os.path.join(docs_dir, file_name)
            # Handle duplicate filenames from different source folders
            if file_name in copied and not os.path.samefile(abs_path, dest):
                base, ext = os.path.splitext(file_name)
                counter = 1
                while os.path.exists(dest):
                    file_name = f"{base}_{counter}{ext}"
                    dest = os.path.join(docs_dir, file_name)
                    counter += 1
            if file_name not in copied:
                shutil.copy2(abs_path, dest)
                copied.add(file_name)
            # Update metadata to point to the portable relative path
            doc.metadata["file_path"] = os.path.join("chroma_db", "documents", file_name)

        log(f"Total {len(documents)} documents loaded from all paths.")

        # Ingestion pipeline: split into chunks and extract metadata
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=512, chunk_overlap=64, include_metadata=True),
                MetaDataExtractor(),
                Settings.embed_model,
            ],
            cache=IngestionCache()
        )

        log("Running ingestion pipeline (chunking + metadata extraction)…")

        BATCH_SIZE = 50
        total_batches = math.ceil(len(documents) / BATCH_SIZE)
        all_nodes = []

        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            log(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)…")

            batch_nodes = pipeline.run(documents=batch, show_progress=True)
            all_nodes.extend(batch_nodes)

            pipeline.cache.persist("./cache")
            torch.cuda.empty_cache()
            log(f"Batch {batch_num} done - {len(batch_nodes)} nodes produced")


        log(f"Pipeline complete — {len(all_nodes)} total nodes")

        CHROMA_BATCH = 5000
        log(f"Inserting {len(all_nodes)} nodes into ChromaDB…")

        for i in range(0, len(all_nodes), CHROMA_BATCH):
            chunk = all_nodes[i:i + CHROMA_BATCH]
            chunk_num = (i // CHROMA_BATCH) + 1
            total_chunks = math.ceil(len(all_nodes) / CHROMA_BATCH)
            log(f"ChromaDB insert {chunk_num}/{total_chunks} ({len(chunk)} nodes)…")
            vector_store.add(chunk)

        log("All nodes inserted into ChromaDB")

        if all_nodes:
            sample = all_nodes[0].metadata
            log(f"Sample metadata from first node:")
            log(f"  year={sample.get('year')}  source={sample.get('source')}")
            log(f"  title={sample.get('title')}")
            log(f"  people={sample.get('people', [])[:3]}")

        # Build the vector store index from the produced nodes
        log("Building VectorStoreIndex (embedding all nodes)…")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            show_progress=True)
        storage_context.persist(persist_dir="./storageContext")
        log("Index successfully built")
        return index
    else:
        log(f"Found {get_collection} in collection. Loading index...")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            show_progress=True)
        log(f"BOOM LET'S GO!!!")
        return index
