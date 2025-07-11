"""
Debug script to analyze GitHub push issues
"""

import asyncio
import json
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.common.database import get_db
from src.common.models import QLCapsule
import structlog

logger = structlog.get_logger()

async def debug_capsule_contents(capsule_id: str):
    """Debug what files are actually in the capsule"""
    
    # Get database session
    db = next(get_db())
    storage = CapsuleStorageService(db)
    
    try:
        # Retrieve capsule
        capsule = await storage.get_capsule(capsule_id)
        
        if not capsule:
            print(f"❌ Capsule {capsule_id} not found!")
            return
        
        print(f"✅ Found capsule: {capsule_id}")
        print(f"📝 Request ID: {capsule.request_id}")
        
        # Analyze source code files
        print(f"\n📁 Source Code Files ({len(capsule.source_code)}):")
        for file_path, content in capsule.source_code.items():
            content_preview = content[:100] if isinstance(content, str) else str(content)[:100]
            print(f"  - {file_path}: {len(content) if isinstance(content, str) else 'DICT'} chars")
            print(f"    Preview: {content_preview}...")
            
        # Analyze test files
        print(f"\n🧪 Test Files ({len(capsule.tests)}):")
        for file_path, content in capsule.tests.items():
            content_preview = content[:100] if isinstance(content, str) else str(content)[:100]
            print(f"  - {file_path}: {len(content) if isinstance(content, str) else 'DICT'} chars")
            print(f"    Preview: {content_preview}...")
            
        # Check for content wrapped in dicts
        print("\n🔍 Checking for wrapped content...")
        for file_path, content in capsule.source_code.items():
            if isinstance(content, dict):
                print(f"  ⚠️ {file_path} has dict content: {list(content.keys())}")
                if "content" in content:
                    print(f"     Actual content length: {len(content['content'])}")
                    
        for file_path, content in capsule.tests.items():
            if isinstance(content, dict):
                print(f"  ⚠️ {file_path} has dict content: {list(content.keys())}")
                if "content" in content:
                    print(f"     Actual content length: {len(content['content'])}")
        
        # Check raw database model
        print("\n🔧 Checking raw database content...")
        from src.common.database import CapsuleModel
        capsule_model = db.query(CapsuleModel).filter(CapsuleModel.id == capsule_id).first()
        
        if capsule_model:
            # Check if source_code is stored as string
            if isinstance(capsule_model.source_code, str):
                print("  📄 source_code is stored as JSON string")
                try:
                    source_data = json.loads(capsule_model.source_code)
                    print(f"     Parsed files: {list(source_data.keys())}")
                except Exception as e:
                    print(f"     ❌ Failed to parse: {e}")
            else:
                print(f"  📄 source_code is stored as: {type(capsule_model.source_code)}")
                
            # Check if tests is stored as string
            if isinstance(capsule_model.tests, str):
                print("  📄 tests is stored as JSON string")
                try:
                    test_data = json.loads(capsule_model.tests)
                    print(f"     Parsed files: {list(test_data.keys())}")
                except Exception as e:
                    print(f"     ❌ Failed to parse: {e}")
            else:
                print(f"  📄 tests is stored as: {type(capsule_model.tests)}")
        
        # Check what files SHOULD be pushed
        print("\n📤 Files that should be pushed to GitHub:")
        expected_files = []
        
        # Source files
        for file_path in capsule.source_code.keys():
            expected_files.append(file_path)
            
        # Test files  
        for file_path in capsule.tests.keys():
            expected_files.append(file_path)
            
        # Additional files
        if capsule.documentation:
            expected_files.append("README.md")
        expected_files.extend(["qlp-manifest.json", "qlp-metadata.json", ".gitignore"])
        
        if capsule.deployment_config:
            expected_files.append("qlp-deployment.json")
            
        if capsule.validation_report:
            expected_files.append("qlp-validation.json")
            
        print(f"  Total expected files: {len(expected_files)}")
        for f in expected_files:
            print(f"  - {f}")
            
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    # Run debug for the specific capsule
    capsule_id = "2b2ced40-9b02-48d0-a7f3-eb8b65f6c5c7"
    asyncio.run(debug_capsule_contents(capsule_id))