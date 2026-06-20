# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - THE COMPLETE LEGAL OS
# $10B VISION - SINGLE PROVIDER FOR ALL LEGAL WORK AUTOMATION
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================

import os
import json
from datetime import datetime

LEGAL_DOCS_DIR = "legal_docs"

def build_index():
    """Build search index for legal documents"""
    print("Building LexSarthi legal document index...")
    
    index_data = {
        "version": "4.0.0",
        "build_date": datetime.utcnow().isoformat(),
        "documents": []
    }
    
    if os.path.exists(LEGAL_DOCS_DIR):
        for filename in os.listdir(LEGAL_DOCS_DIR):
            if filename.endswith('.txt') or filename.endswith('.md'):
                filepath = os.path.join(LEGAL_DOCS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    index_data["documents"].append({
                        "filename": filename,
                        "title": filename.replace('.txt', '').replace('.md', '').replace('_', ' '),
                        "content": content[:2000],
                        "word_count": len(content.split()),
                        "indexed_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    print(f"Error indexing {filename}: {e}")
    
    # Save index
    with open("legal_index.json", "w", encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"Index built: {len(index_data['documents'])} documents indexed")

if __name__ == "__main__":
    build_index()