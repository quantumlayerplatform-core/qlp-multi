#!/usr/bin/env python3
"""
Simple capsule download script that directly queries the database
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import argparse


def get_db_connection():
    """Create a direct database connection"""
    return psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="qlp_db",
        user="qlp_user",
        password="qlp_password",
        cursor_factory=RealDictCursor
    )


def list_capsules(limit=10):
    """List capsules directly from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get recent capsules
        cursor.execute("""
            SELECT id, manifest, metadata, created_at
            FROM capsules
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        
        capsules = cursor.fetchall()
        
        if not capsules:
            print("No capsules found in database")
            return
        
        print(f"\n📦 Available Capsules (showing {len(capsules)} capsules):")
        print("=" * 80)
        
        for capsule in capsules:
            manifest = json.loads(capsule['manifest']) if capsule['manifest'] else {}
            metadata = json.loads(capsule['metadata']) if capsule['metadata'] else {}
            
            print(f"\n🆔 ID: {capsule['id']}")
            print(f"   📋 Name: {manifest.get('name', 'Unnamed')}")
            print(f"   📝 Description: {manifest.get('description', 'No description')[:60]}...")
            print(f"   💻 Language: {manifest.get('language', 'Unknown')}")
            print(f"   🛠️ Framework: {manifest.get('framework', 'Unknown')}")
            print(f"   📅 Created: {capsule['created_at']}")
            print(f"   💯 Confidence: {metadata.get('confidence_score', 0) * 100:.0f}%")
            
    finally:
        cursor.close()
        conn.close()


def download_capsule(capsule_id, output_dir=".", as_directory=False):
    """Download a specific capsule"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get the capsule
        cursor.execute("""
            SELECT * FROM capsules WHERE id = %s
        """, (capsule_id,))
        
        capsule = cursor.fetchone()
        
        if not capsule:
            print(f"❌ Capsule {capsule_id} not found")
            return
        
        # Parse JSON fields
        manifest = json.loads(capsule['manifest']) if capsule['manifest'] else {}
        source_code = json.loads(capsule['source_code']) if capsule['source_code'] else {}
        tests = json.loads(capsule['tests']) if capsule['tests'] else {}
        metadata = json.loads(capsule['metadata']) if capsule['metadata'] else {}
        deployment_config = json.loads(capsule['deployment_config']) if capsule['deployment_config'] else {}
        validation_report = json.loads(capsule['validation_report']) if capsule['validation_report'] else {}
        
        name = manifest.get('name', 'unnamed').lower().replace(' ', '-')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if as_directory:
            # Extract to directory
            dir_name = f"{name}_capsule_{timestamp}"
            capsule_dir = Path(output_dir) / dir_name
            capsule_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📂 Extracting capsule to: {capsule_dir}")
            print("=" * 60)
            
            # Save manifest
            with open(capsule_dir / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            print("   📋 manifest.json")
            
            # Save source code files
            print("\n📁 Source files:")
            for filename, content in source_code.items():
                file_path = capsule_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                print(f"   📄 {filename}")
            
            # Save test files
            if tests:
                print("\n🧪 Test files:")
                for filename, content in tests.items():
                    file_path = capsule_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    print(f"   🧪 {filename}")
            
            # Save documentation
            if capsule['documentation']:
                (capsule_dir / "README.md").write_text(capsule['documentation'])
                print("\n📚 Documentation:")
                print("   📚 README.md")
            
            # Save other metadata
            with open(capsule_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if deployment_config:
                with open(capsule_dir / "deployment_config.json", 'w') as f:
                    json.dump(deployment_config, f, indent=2)
                print("\n🚀 Deployment config:")
                print("   🚀 deployment_config.json")
            
            if validation_report:
                with open(capsule_dir / "validation_report.json", 'w') as f:
                    json.dump(validation_report, f, indent=2)
                print("\n✅ Validation report:")
                print("   ✅ validation_report.json")
            
            print(f"\n✅ Successfully extracted capsule to: {capsule_dir}")
            print(f"📊 Total files: {len(source_code) + len(tests) + 4}")
            
            # Show capsule quality info
            print("\n🎯 Capsule Quality:")
            print(f"   Confidence Score: {metadata.get('confidence_score', 0) * 100:.0f}%")
            print(f"   Production Ready: {'Yes ✅' if metadata.get('production_ready') else 'No ❌'}")
            
            if validation_report:
                print(f"   Validation Status: {validation_report.get('overall_status', 'Unknown')}")
                print(f"   Test Coverage: {validation_report.get('metadata', {}).get('test_coverage', 0)}%")
            
            return capsule_dir
            
        else:
            # Create a ZIP file
            import zipfile
            
            zip_name = f"{name}_capsule_{timestamp}.zip"
            zip_path = Path(output_dir) / zip_name
            
            print(f"\n📦 Creating ZIP archive: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add all files
                for filename, content in source_code.items():
                    zf.writestr(filename, content)
                
                for filename, content in tests.items():
                    zf.writestr(filename, content)
                
                if capsule['documentation']:
                    zf.writestr("README.md", capsule['documentation'])
                
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))
                
                if deployment_config:
                    zf.writestr("deployment_config.json", json.dumps(deployment_config, indent=2))
                
                if validation_report:
                    zf.writestr("validation_report.json", json.dumps(validation_report, indent=2))
            
            print(f"✅ Successfully created: {zip_path}")
            return zip_path
            
    finally:
        cursor.close()
        conn.close()


def inspect_capsule(capsule_id):
    """Show capsule details without downloading"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM capsules WHERE id = %s
        """, (capsule_id,))
        
        capsule = cursor.fetchone()
        
        if not capsule:
            print(f"❌ Capsule {capsule_id} not found")
            return
        
        # Parse JSON fields
        manifest = json.loads(capsule['manifest']) if capsule['manifest'] else {}
        source_code = json.loads(capsule['source_code']) if capsule['source_code'] else {}
        tests = json.loads(capsule['tests']) if capsule['tests'] else {}
        metadata = json.loads(capsule['metadata']) if capsule['metadata'] else {}
        validation_report = json.loads(capsule['validation_report']) if capsule['validation_report'] else {}
        
        print("\n" + "=" * 80)
        print(f"🔍 CAPSULE INSPECTION: {capsule_id}")
        print("=" * 80)
        
        # Manifest
        print("\n📋 MANIFEST:")
        for key, value in manifest.items():
            if isinstance(value, (dict, list)):
                print(f"   {key}: {json.dumps(value, indent=6)}")
            else:
                print(f"   {key}: {value}")
        
        # File listing
        print("\n📁 SOURCE FILES:")
        for filename in sorted(source_code.keys()):
            size = len(source_code[filename])
            print(f"   📄 {filename} ({size:,} bytes)")
        
        if tests:
            print("\n🧪 TEST FILES:")
            for filename in sorted(tests.keys()):
                size = len(tests[filename])
                print(f"   🧪 {filename} ({size:,} bytes)")
        
        # Documentation
        if capsule['documentation']:
            print("\n📚 DOCUMENTATION:")
            doc_preview = capsule['documentation'][:200] + "..." if len(capsule['documentation']) > 200 else capsule['documentation']
            print(f"   {doc_preview}")
        
        # Validation report
        if validation_report:
            print(f"\n✅ VALIDATION REPORT:")
            print(f"   Status: {validation_report.get('overall_status', 'Unknown')}")
            print(f"   Confidence: {validation_report.get('confidence_score', 0) * 100:.0f}%")
            print(f"   Human Review: {'Required' if validation_report.get('requires_human_review') else 'Not Required'}")
            
            if 'checks' in validation_report:
                print(f"   Checks: {len(validation_report['checks'])} performed")
        
        # Metadata
        print("\n📊 METADATA:")
        print(f"   Generated by: {metadata.get('generated_by', 'Unknown')}")
        print(f"   Confidence Score: {metadata.get('confidence_score', 0) * 100:.0f}%")
        print(f"   Production Ready: {'Yes ✅' if metadata.get('production_ready') else 'No ❌'}")
        print(f"   Total Lines: {metadata.get('total_lines', 0):,}")
        print(f"   Languages: {', '.join(metadata.get('languages', []))}")
        print(f"   Frameworks: {', '.join(metadata.get('frameworks', []))}")
        
        if 'features' in metadata:
            print(f"   Features: {', '.join(metadata['features'][:5])}...")
        
        print("\n" + "=" * 80)
        
    finally:
        cursor.close()
        conn.close()


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Download and inspect QLCapsules")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available capsules')
    list_parser.add_argument('--limit', type=int, default=10, help='Maximum number to show')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a capsule')
    download_parser.add_argument('capsule_id', help='Capsule ID to download')
    download_parser.add_argument('--output', '-o', default='.', help='Output directory')
    download_parser.add_argument('--directory', '-d', action='store_true', 
                               help='Extract as directory instead of ZIP')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect capsule contents')
    inspect_parser.add_argument('capsule_id', help='Capsule ID to inspect')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            list_capsules(args.limit)
        
        elif args.command == 'download':
            download_capsule(args.capsule_id, args.output, args.directory)
        
        elif args.command == 'inspect':
            inspect_capsule(args.capsule_id)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()