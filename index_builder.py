import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SimpleNodeParser
from llama_parse import LlamaParse

def build_legal_index(docs_path="./legal_docs", persist_dir="./legal_index"):
    if not os.path.exists(docs_path):
        print(f"Error: {docs_path} folder not found. Create it and add legal PDFs/txt files.")
        return

    # Use LlamaParse for PDFs, fallback to default for txt
    parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="text") if os.getenv("LLAMA_CLOUD_API_KEY") else None
    reader = SimpleDirectoryReader(
        input_dir=docs_path,
        file_extractor={".pdf": parser} if parser else {},
        recursive=True
    )
    print("Loading legal documents...")
    documents = reader.load_data()
    print(f"Loaded {len(documents)} raw documents")

    # Split into smaller chunks for better retrieval
    node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200)
    nodes = node_parser.get_nodes_from_documents(documents)
    print(f"Created {len(nodes)} index nodes")

    # Build and persist index
    index = VectorStoreIndex(nodes)
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"Legal index saved to {persist_dir}")

if __name__ == "__main__":
    build_legal_index()