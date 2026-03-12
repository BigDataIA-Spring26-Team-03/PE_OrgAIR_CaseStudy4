# scripts/inspect_chroma.py
import chromadb
from collections import Counter

client = chromadb.PersistentClient(path="./chroma_data")

try:
    collection = client.get_collection("pe_evidence")
except Exception as e:
    print(f"❌ Collection not found: {e}")
    print("ChromaDB is empty — run the indexing script first")
    exit(1)

# 1. Total count
total = collection.count()
print(f"\n{'='*50}")
print(f"Total documents indexed: {total}")
print(f"{'='*50}")

if total == 0:
    print("❌ No documents indexed yet")
    exit(1)

# 2. Peek at first 3 documents
print("\n--- Sample Documents (first 3) ---")
peek = collection.peek(limit=3)
for i in range(len(peek["ids"])):
    print(f"\nDoc {i+1}:")
    print(f"  ID:           {peek['ids'][i]}")
    print(f"  Content:      {peek['documents'][i][:100]}...")
    print(f"  Metadata:     {peek['metadatas'][i]}")

# 3. Full metadata scan
all_data = collection.get(include=["metadatas"])
metadatas = all_data["metadatas"]

# 4. Companies indexed
companies = Counter(m.get("company_id", "unknown") for m in metadatas)
print(f"\n--- Companies Indexed ({len(companies)} total) ---")
for company, count in sorted(companies.items()):
    print(f"  {company}: {count} chunks")

# 5. Breakdown by company + dimension
print("\n--- Chunks by Company + Dimension ---")
combos = Counter(
    (m.get("company_id", "?"), m.get("dimension", "?"))
    for m in metadatas
)
for (company, dim), count in sorted(combos.items()):
    print(f"  {company:<8} | {dim:<25} : {count}")

# 6. Breakdown by source type
print("\n--- Chunks by Source Type ---")
sources = Counter(m.get("source_type", "unknown") for m in metadatas)
for source, count in sorted(sources.items(), key=lambda x: -x[1]):
    print(f"  {source:<30} : {count}")

# 7. Confidence distribution
confidences = [m.get("confidence", 0) for m in metadatas]
if confidences:
    print(f"\n--- Confidence Stats ---")
    print(f"  Min:  {min(confidences):.2f}")
    print(f"  Max:  {max(confidences):.2f}")
    print(f"  Avg:  {sum(confidences)/len(confidences):.2f}")

print(f"\n{'='*50}")
print("✅ Inspection complete")
print(f"{'='*50}\n")