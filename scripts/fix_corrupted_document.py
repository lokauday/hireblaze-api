"""
Fix corrupted document by clearing binary content.
This script clears the corrupted content from document ID 1.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.db.models.document import Document

def fix_corrupted_document():
    """Clear corrupted binary content from documents."""
    db = SessionLocal()
    try:
        # Find documents with binary/corrupted content
        documents = db.query(Document).all()
        
        fixed_count = 0
        for doc in documents:
            content = doc.content_text or ""
            
            # Check if content is corrupted (starts with PK, has null bytes, etc.)
            is_corrupted = (
                content.startswith('PK') or
                '\x00' in content[:1000] or
                (len(content) > 100 and sum(1 for c in content[:1000] if ord(c) < 32 and c not in '\n\r\t') > len(content[:1000]) * 0.1)
            )
            
            if is_corrupted:
                print(f"Found corrupted document: ID={doc.id}, Title='{doc.title}', Content length={len(content)}")
                doc.content_text = ""  # Clear corrupted content
                fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"\nFixed {fixed_count} corrupted document(s)")
        else:
            print("\nNo corrupted documents found")
            
    except Exception as e:
        db.rollback()
        print(f"Error fixing documents: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_corrupted_document()
