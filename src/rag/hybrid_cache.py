"""Content-verified FAISS cache, without pickle or cached query results."""
import json
from pathlib import Path
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from .acceptance import config_id, hash_file
from .chunk_identity import validate_document
from .vector_store import create_embeddings, create_vector_store


def cached_vector_store(chunks, settings, config, cache_root):
    ids = [d.metadata["chunk_id"] for d in chunks]
    for doc in chunks:
        validate_document(doc)
    signature = config_id({"config": config, "chunks": ids,
                           "metadata": [d.metadata for d in chunks]})
    directory = Path(cache_root) / "hybrid-faiss" / signature
    index_path, manifest_path = directory / "index.faiss", directory / "manifest.json"
    embeddings = create_embeddings(settings)
    if index_path.is_file() and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (manifest["signature"] == signature and manifest["ids"] == ids
                    and hash_file(index_path) == manifest["index_sha256"]):
                index = faiss.read_index(str(index_path))
                if index.ntotal == len(chunks):
                    return FAISS(embeddings, index, InMemoryDocstore(dict(zip(ids, chunks))), dict(enumerate(ids)))
        except (ValueError, KeyError, OSError, RuntimeError):
            pass  # Invalid derived cache is rebuilt; source inputs remain immutable.
    vector = create_vector_store(chunks, settings, embeddings)
    directory.mkdir(parents=True, exist_ok=True)
    faiss.write_index(vector.index, str(index_path))
    manifest_path.write_text(json.dumps({"signature": signature, "ids": ids,
                                       "index_sha256": hash_file(index_path)}), encoding="utf-8")
    return vector
