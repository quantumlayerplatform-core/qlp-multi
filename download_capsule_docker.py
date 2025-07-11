#!/usr/bin/env python3
"""
Download capsules using Docker exec to access PostgreSQL
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import zipfile


def run_psql_query(query):
    """Run a PostgreSQL query through Docker"""
    cmd = [
        "docker", "exec", "qlp-postgres",
        "psql", "-U", "qlp_user", "-d", "qlp_db",
        "-t", "-A", "-c", query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Database error: {result.stderr}")
    return result.stdout.strip()


def list_capsules(limit=10):
    """List available capsules"""
    query = f"""
    SELECT json_build_object(
        'id', id,
        'manifest', manifest::json,
        'metadata', meta_data::json,
        'created_at', created_at
    ) FROM capsules 
    ORDER BY created_at DESC 
    LIMIT {limit};
    """
    
    result = run_psql_query(query)
    if not result:
        print("No capsules found in database")
        return
    
    print(f"\n📦 Available Capsules:")
    print("=" * 80)
    
    for line in result.split('\n'):
        if line:
            capsule = json.loads(line)
            manifest = capsule.get('manifest', {})
            metadata = capsule.get('metadata', {})
            
            print(f"\n🆔 ID: {capsule['id']}")
            print(f"   📋 Name: {manifest.get('name', 'Unnamed')}")
            print(f"   📝 Description: {manifest.get('description', 'No description')[:60]}...")
            print(f"   💻 Language: {manifest.get('language', 'Unknown')}")
            print(f"   🛠️ Framework: {manifest.get('framework', 'Unknown')}")
            print(f"   📅 Created: {capsule['created_at']}")
            print(f"   💯 Confidence: {metadata.get('confidence_score', 0) * 100:.0f}%")


def download_capsule(capsule_id, output_dir=".", as_directory=False):
    """Download a specific capsule"""
    # Get the full capsule data
    query = f"""
    SELECT json_build_object(
        'id', id,
        'manifest', manifest::json,
        'source_code', source_code::json,
        'tests', tests::json,
        'documentation', documentation,
        'metadata', meta_data::json,
        'deployment_config', deployment_config::json,
        'validation_report', validation_report::json
    ) FROM capsules 
    WHERE id = '{capsule_id}';
    """
    
    result = run_psql_query(query)
    if not result:
        print(f"❌ Capsule {capsule_id} not found")
        return
    
    capsule = json.loads(result)
    manifest = capsule.get('manifest', {})
    source_code = capsule.get('source_code', {})
    tests = capsule.get('tests', {})
    metadata = capsule.get('metadata', {})
    
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
        if source_code:
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
        if capsule.get('documentation'):
            (capsule_dir / "README.md").write_text(capsule['documentation'])
            print("\n📚 Documentation:")
            print("   📚 README.md")
        
        # Save metadata
        with open(capsule_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save deployment config
        if capsule.get('deployment_config'):
            with open(capsule_dir / "deployment_config.json", 'w') as f:
                json.dump(capsule['deployment_config'], f, indent=2)
            print("\n🚀 Deployment config:")
            print("   🚀 deployment_config.json")
        
        # Save validation report
        if capsule.get('validation_report'):
            with open(capsule_dir / "validation_report.json", 'w') as f:
                json.dump(capsule['validation_report'], f, indent=2)
            print("\n✅ Validation report:")
            print("   ✅ validation_report.json")
        
        print(f"\n✅ Successfully extracted capsule to: {capsule_dir}")
        print(f"📊 Total files: {len(source_code) + len(tests) + 4}")
        
        # Show capsule quality info
        print("\n🎯 Capsule Quality:")
        print(f"   Confidence Score: {metadata.get('confidence_score', 0) * 100:.0f}%")
        print(f"   Production Ready: {'Yes ✅' if metadata.get('production_ready') else 'No ❌'}")
        
        return capsule_dir
    
    else:
        # Create ZIP file
        zip_name = f"{name}_capsule_{timestamp}.zip"
        zip_path = Path(output_dir) / zip_name
        
        print(f"\n📦 Creating ZIP archive: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Add source files
            for filename, content in source_code.items():
                zf.writestr(filename, content)
            
            # Add test files
            for filename, content in tests.items():
                zf.writestr(filename, content)
            
            # Add documentation
            if capsule.get('documentation'):
                zf.writestr("README.md", capsule['documentation'])
            
            # Add deployment config
            if capsule.get('deployment_config'):
                zf.writestr("deployment_config.json", json.dumps(capsule['deployment_config'], indent=2))
            
            # Add validation report
            if capsule.get('validation_report'):
                zf.writestr("validation_report.json", json.dumps(capsule['validation_report'], indent=2))
        
        print(f"✅ Successfully created: {zip_path}")
        return zip_path


def inspect_capsule(capsule_id):
    """Inspect capsule without downloading"""
    query = f"""
    SELECT json_build_object(
        'id', id,
        'manifest', manifest::json,
        'source_code', source_code::json,
        'tests', tests::json,
        'documentation', documentation,
        'metadata', meta_data::json,
        'validation_report', validation_report::json,
        'created_at', created_at
    ) FROM capsules 
    WHERE id = '{capsule_id}';
    """
    
    result = run_psql_query(query)
    if not result:
        print(f"❌ Capsule {capsule_id} not found")
        return
    
    capsule = json.loads(result)
    manifest = capsule.get('manifest', {})
    source_code = capsule.get('source_code', {})
    tests = capsule.get('tests', {})
    metadata = capsule.get('metadata', {})
    validation_report = capsule.get('validation_report', {})
    
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
    
    # Documentation preview
    if capsule.get('documentation'):
        print("\n📚 DOCUMENTATION:")
        doc = capsule['documentation']
        preview = doc[:200] + "..." if len(doc) > 200 else doc
        print(f"   {preview}")
    
    # Validation report
    if validation_report:
        print(f"\n✅ VALIDATION REPORT:")
        print(f"   Status: {validation_report.get('overall_status', 'Unknown')}")
        print(f"   Confidence: {validation_report.get('confidence_score', 0) * 100:.0f}%")
        print(f"   Human Review: {'Required' if validation_report.get('requires_human_review') else 'Not Required'}")
    
    # Metadata
    print("\n📊 METADATA:")
    print(f"   Confidence Score: {metadata.get('confidence_score', 0) * 100:.0f}%")
    print(f"   Production Ready: {'Yes ✅' if metadata.get('production_ready') else 'No ❌'}")
    print(f"   Total Lines: {metadata.get('total_lines', 0):,}")
    print(f"   Languages: {', '.join(metadata.get('languages', []))}")
    print(f"   Frameworks: {', '.join(metadata.get('frameworks', []))}")
    
    print("\n" + "=" * 80)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Download QLCapsules using Docker")
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