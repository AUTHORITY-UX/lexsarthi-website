import PyPDF2
import os
import csv

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text

# Your PDF files - UPDATE THESE PATHS TO WHERE YOUR FILES ARE
pdf_files = [
    "companies act.pdf",
    "the_constitution_of_india.pdf",
    "AI ACT.pdf",
    "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.pdf",
    "DATA_ACT.pdf",
    "Indian contract act.pdf",
    "EVIDENCE ACT.pdf",
    "data_broker_reg_delete_act_statute_eff_20260101.pdf",
    "PDPPA.pdf",
    "ai-court-comments.html.txt"
]

# Create chunks
chunks = []
for pdf_file in pdf_files:
    print(f"Processing: {pdf_file}")
    full_text = extract_text_from_pdf(pdf_file)
    
    # Split into chunks (e.g., 500 words each)
    words = full_text.split()
    chunk_size = 500
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i:i+chunk_size])
        chunks.append({
            'text': chunk_text,
            'source': pdf_file,
            'label': pdf_file.replace('.pdf', '').replace('.txt', '').replace('_', ' ').title()
        })

print(f"✅ Created {len(chunks)} chunks from {len(pdf_files)} files")

# Save to CSV
with open('legal_chunks.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['text', 'label'])
    for chunk in chunks:
        writer.writerow([chunk['text'][:500], chunk['label']])  # Truncate for Edge Impulse

print("✅ legal_chunks.csv created")