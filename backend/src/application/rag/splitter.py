import re
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

def sanitize_metadata_keys(metadata: dict) -> dict:
    """Membersihkan metadata di tahap akhir agar Weaviate tidak error."""
    sanitized = {}
    for key, value in metadata.items():
        clean_key = re.sub(r'[^_A-Za-z0-9]', '_', key)
        if re.match(r'^[0-9]', clean_key):
            clean_key = f"_{clean_key}"
        clean_key = clean_key.lower()
        sanitized[clean_key] = value
    return sanitized

def split_docs(docs):
    # Gunakan penamaan yang sudah aman (tanpa spasi) sebagai best practice awal
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len
    )
    
    final_chunks = []
    for doc in docs:
        try:
            md_chunks = markdown_splitter.split_text(doc.page_content)
        except Exception as e:
            print(f"Error markdown splitting doc: {e}")
            md_chunks = [doc]
            
        if not md_chunks:
            md_chunks = [doc]
            
        for md_chunk in md_chunks:
            # 1. Gabungkan metadata kotor dari Loader dan Splitter
            merged_metadata = doc.metadata.copy()
            merged_metadata.update(md_chunk.metadata)
            
            # 2. CUCI BERSIH SEMUANYA DI SINI (Satu kali saja!)
            md_chunk.metadata = sanitize_metadata_keys(merged_metadata)
            
        sub_chunks = recursive_splitter.split_documents(md_chunks)
        final_chunks.extend(sub_chunks)
        
    return final_chunks