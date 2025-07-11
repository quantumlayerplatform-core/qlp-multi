#!/usr/bin/env python3
"""
Download QLCapsule from Database
Downloads a capsule by ID and extracts its contents
"""

import os
import sys
import json
import zipfile
import tarfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add src to path
sys.path.append('.')

from src.orchestrator.capsule_storage import CapsuleStorageService as PostgresCapsuleStorage
from src.orchestrator.capsule_export import CapsuleExporter
from src.common.models import QLCapsule
from src.common.database import get_db


class CapsuleDownloader:
    """Downloads and extracts capsules from database"""
    
    def __init__(self):
        # Get database session
        db_gen = get_db()
        self.db = next(db_gen)
        self.storage = PostgresCapsuleStorage(self.db)
        self.exporter = CapsuleExporter()
    
    async def list_capsules(self, limit: int = 10) -> None:
        """List available capsules in the database"""
        capsules = await self.storage.list_capsules(limit=limit)
        
        if not capsules:
            print("No capsules found in database")
            return
        
        print(f"\n📦 Available Capsules (showing {len(capsules)} of {limit} max):")
        print("=" * 80)
        
        for capsule in capsules:
            created_at = capsule.get('created_at', 'Unknown')
            manifest = capsule.get('manifest', {})
            name = manifest.get('name', 'Unnamed')
            language = manifest.get('language', 'Unknown')
            framework = manifest.get('framework', 'Unknown')
            
            print(f"\n🆔 ID: {capsule['id']}")
            print(f"   📋 Name: {name}")
            print(f"   💻 Language: {language} | Framework: {framework}")
            print(f"   📅 Created: {created_at}")
            print(f"   📁 Files: {len(capsule.get('source_code', {}))} source, {len(capsule.get('tests', {}))} tests")
    
    async def download_capsule(self, capsule_id: str, output_dir: str = ".", format: str = "zip") -> Path:
        """Download a capsule and save it to disk"""
        # Fetch capsule from database
        print(f"\n🔍 Fetching capsule {capsule_id} from database...")
        capsule_data = await self.storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise ValueError(f"Capsule {capsule_id} not found in database")
        
        # Convert to QLCapsule model
        capsule = QLCapsule(**capsule_data)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get capsule name for filename
        manifest = capsule.manifest
        name = manifest.get('name', 'unnamed').lower().replace(' ', '-')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == "zip":
            # Export as ZIP
            print(f"📦 Creating ZIP archive...")
            zip_data = await self.exporter.export_as_zip(capsule)
            
            filename = f"{name}_capsule_{timestamp}.zip"
            filepath = output_path / filename
            
            with open(filepath, 'wb') as f:
                f.write(zip_data)
            
            print(f"✅ Downloaded to: {filepath}")
            return filepath
            
        elif format == "tar":
            # Export as TAR.GZ
            print(f"📦 Creating TAR.GZ archive...")
            tar_data = await self.exporter.export_as_tar(capsule, "gz")
            
            filename = f"{name}_capsule_{timestamp}.tar.gz"
            filepath = output_path / filename
            
            with open(filepath, 'wb') as f:
                f.write(tar_data)
            
            print(f"✅ Downloaded to: {filepath}")
            return filepath
            
        elif format == "directory":
            # Extract directly to directory
            dir_name = f"{name}_capsule_{timestamp}"
            capsule_dir = output_path / dir_name
            capsule_dir.mkdir(exist_ok=True)
            
            print(f"📂 Extracting to directory: {capsule_dir}")
            
            # Save manifest
            with open(capsule_dir / "manifest.json", 'w') as f:
                json.dump(capsule.manifest, f, indent=2)
            
            # Save source code
            for filename, content in capsule.source_code.items():
                file_path = capsule_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                print(f"   📄 {filename}")
            
            # Save tests
            for filename, content in capsule.tests.items():
                file_path = capsule_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                print(f"   🧪 {filename}")
            
            # Save documentation
            if capsule.documentation:
                (capsule_dir / "README.md").write_text(capsule.documentation)
                print(f"   📚 README.md")
            
            # Save validation report
            if capsule.validation_report:
                with open(capsule_dir / "validation_report.json", 'w') as f:
                    json.dump(capsule.validation_report.model_dump(), f, indent=2)
                print(f"   ✅ validation_report.json")
            
            # Save deployment config
            if capsule.deployment_config:
                with open(capsule_dir / "deployment_config.json", 'w') as f:
                    json.dump(capsule.deployment_config, f, indent=2)
                print(f"   🚀 deployment_config.json")
            
            # Save metadata
            with open(capsule_dir / "metadata.json", 'w') as f:
                json.dump(capsule.metadata, f, indent=2)
            
            print(f"\n✅ Extracted to: {capsule_dir}")
            return capsule_dir
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def inspect_capsule(self, capsule_id: str) -> None:
        """Show detailed information about a capsule without downloading"""
        capsule_data = await self.storage.get_capsule(capsule_id)
        
        if not capsule_data:
            print(f"❌ Capsule {capsule_id} not found")
            return
        
        capsule = QLCapsule(**capsule_data)
        
        print("\n" + "=" * 80)
        print(f"🔍 CAPSULE INSPECTION: {capsule_id}")
        print("=" * 80)
        
        # Manifest
        print("\n📋 MANIFEST:")
        for key, value in capsule.manifest.items():
            print(f"   {key}: {value}")
        
        # File listing
        print("\n📁 SOURCE FILES:")
        for filename in sorted(capsule.source_code.keys()):
            size = len(capsule.source_code[filename])
            print(f"   📄 {filename} ({size:,} bytes)")
        
        print("\n🧪 TEST FILES:")
        for filename in sorted(capsule.tests.keys()):
            size = len(capsule.tests[filename])
            print(f"   🧪 {filename} ({size:,} bytes)")
        
        # Validation report
        if capsule.validation_report:
            report = capsule.validation_report
            print(f"\n✅ VALIDATION REPORT:")
            print(f"   Status: {report.overall_status}")
            print(f"   Confidence: {report.confidence_score * 100:.0f}%")
            print(f"   Human Review: {'Required' if report.requires_human_review else 'Not Required'}")
        
        # Metadata
        print("\n📊 METADATA:")
        meta = capsule.metadata
        print(f"   Confidence Score: {meta.get('confidence_score', 0) * 100:.0f}%")
        print(f"   Production Ready: {'Yes' if meta.get('production_ready') else 'No'}")
        print(f"   Total Lines: {meta.get('total_lines', 0):,}")
        print(f"   Languages: {', '.join(meta.get('languages', []))}")
        print(f"   Frameworks: {', '.join(meta.get('frameworks', []))}")
        
        print("\n" + "=" * 80)
    
    async def extract_file(self, capsule_id: str, file_path: str, output: Optional[str] = None) -> None:
        """Extract a specific file from a capsule"""
        capsule_data = await self.storage.get_capsule(capsule_id)
        
        if not capsule_data:
            print(f"❌ Capsule {capsule_id} not found")
            return
        
        capsule = QLCapsule(**capsule_data)
        
        # Look for file in source code and tests
        content = None
        if file_path in capsule.source_code:
            content = capsule.source_code[file_path]
        elif file_path in capsule.tests:
            content = capsule.tests[file_path]
        else:
            print(f"❌ File '{file_path}' not found in capsule")
            print("\nAvailable files:")
            for f in sorted(list(capsule.source_code.keys()) + list(capsule.tests.keys())):
                print(f"  - {f}")
            return
        
        if output:
            # Save to file
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(content)
            print(f"✅ Extracted {file_path} to {output}")
        else:
            # Print to console
            print(f"\n📄 Contents of {file_path}:")
            print("-" * 80)
            print(content)
            print("-" * 80)


async def main():
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
    download_parser.add_argument('--format', '-f', choices=['zip', 'tar', 'directory'], 
                               default='zip', help='Download format')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect capsule contents')
    inspect_parser.add_argument('capsule_id', help='Capsule ID to inspect')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract specific file')
    extract_parser.add_argument('capsule_id', help='Capsule ID')
    extract_parser.add_argument('file_path', help='File path within capsule')
    extract_parser.add_argument('--output', '-o', help='Output file (or print to console)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    downloader = CapsuleDownloader()
    
    try:
        if args.command == 'list':
            await downloader.list_capsules(args.limit)
        
        elif args.command == 'download':
            await downloader.download_capsule(args.capsule_id, args.output, args.format)
        
        elif args.command == 'inspect':
            await downloader.inspect_capsule(args.capsule_id)
        
        elif args.command == 'extract':
            await downloader.extract_file(args.capsule_id, args.file_path, args.output)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())