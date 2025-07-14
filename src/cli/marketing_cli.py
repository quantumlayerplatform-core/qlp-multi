#!/usr/bin/env python3
"""
QuantumLayer Marketing CLI

Command-line interface for the AI-powered marketing campaign system.
"""

import click
import asyncio
import json
from datetime import datetime
from typing import Optional
import requests
from tabulate import tabulate

from src.agents.marketing.models import (
    CampaignRequest, CampaignObjective, Channel, 
    ContentType, ToneStyle
)


API_BASE = "http://localhost:8000/api/v2/marketing"


@click.group()
def cli():
    """QuantumLayer Marketing Campaign CLI"""
    pass


@cli.command()
@click.option("--objective", type=click.Choice([
    "launch_awareness", "technical_evangelism", "founder_authority",
    "lead_generation", "community_building", "investor_outreach"
]), required=True, help="Campaign objective")
@click.option("--description", required=True, help="Product description")
@click.option("--audience", required=True, help="Target audience")
@click.option("--duration", type=int, default=30, help="Campaign duration in days")
@click.option("--channels", multiple=True, help="Marketing channels to use")
@click.option("--features", multiple=True, help="Key features to highlight")
def create(objective, description, audience, duration, channels, features):
    """Create a new marketing campaign"""
    
    # Default channels if none specified
    if not channels:
        channels = ["twitter", "linkedin", "email"]
    
    # Default features if none specified
    if not features:
        features = ["AI-powered", "Fast", "Reliable"]
    
    request_data = {
        "objective": objective,
        "product_description": description,
        "target_audience": audience,
        "duration_days": duration,
        "channels": list(channels),
        "key_features": list(features),
        "unique_value_prop": f"{description} for {audience}"
    }
    
    click.echo(f"Creating {objective} campaign...")
    
    try:
        response = requests.post(f"{API_BASE}/campaigns", json=request_data)
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(click.style("✓ Campaign created successfully!", fg="green"))
        click.echo(f"Campaign ID: {result['campaign_id']}")
        click.echo(f"Total Content: {result['total_content']} pieces")
        click.echo(f"Channels: {', '.join(result['channels'])}")
        click.echo(f"\nUse 'qlp-marketing export {result['campaign_id']}' to download")
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
@click.argument("campaign_id")
@click.option("--format", type=click.Choice(["zip", "json", "markdown"]), 
              default="zip", help="Export format")
@click.option("--platform", type=click.Choice(["buffer", "hootsuite", "mailchimp"]),
              help="Platform-specific format")
@click.option("--output", "-o", help="Output file path")
def export(campaign_id, format, platform, output):
    """Export a campaign"""
    
    params = {"format": format}
    if platform:
        params["platform"] = platform
    
    click.echo(f"Exporting campaign {campaign_id}...")
    
    try:
        response = requests.post(
            f"{API_BASE}/campaigns/{campaign_id}/export",
            params=params
        )
        response.raise_for_status()
        
        # Determine output filename
        if not output:
            ext = "zip" if format == "zip" else format
            output = f"campaign_{campaign_id}.{ext}"
        
        # Save content
        if format == "json":
            with open(output, 'w') as f:
                json.dump(response.json(), f, indent=2)
        else:
            with open(output, 'wb') as f:
                f.write(response.content)
        
        click.echo(click.style(f"✓ Exported to {output}", fg="green"))
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
@click.argument("campaign_id")
def analytics(campaign_id):
    """View campaign analytics"""
    
    click.echo(f"Fetching analytics for campaign {campaign_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/campaigns/{campaign_id}/analytics")
        response.raise_for_status()
        
        data = response.json()
        analytics = data['analytics']
        
        # Display overview
        click.echo("\n" + click.style("Campaign Analytics", bold=True))
        click.echo("=" * 50)
        
        overview = [
            ["Total Impressions", f"{analytics['total_impressions']:,}"],
            ["Total Clicks", f"{analytics['total_clicks']:,}"],
            ["Total Conversions", f"{analytics['total_conversions']:,}"],
            ["Avg Engagement Rate", f"{analytics['avg_engagement_rate']:.2%}"]
        ]
        
        click.echo(tabulate(overview, tablefmt="grid"))
        
        # Display channel performance
        if analytics['channel_performance']:
            click.echo("\n" + click.style("Channel Performance", bold=True))
            
            channel_data = []
            for channel, metrics in analytics['channel_performance'].items():
                channel_data.append([
                    channel,
                    f"{metrics['total_impressions']:,}",
                    f"{metrics.get('avg_engagement_rate', 0):.2%}",
                    f"{metrics.get('click_rate', 0):.2%}"
                ])
            
            headers = ["Channel", "Impressions", "Engagement", "CTR"]
            click.echo(tabulate(channel_data, headers=headers, tablefmt="grid"))
        
        # Display recommendations
        if analytics['recommendations']:
            click.echo("\n" + click.style("Recommendations", bold=True))
            for i, rec in enumerate(analytics['recommendations'], 1):
                click.echo(f"{i}. {rec}")
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
@click.option("--type", "content_type", 
              type=click.Choice(["tweet_thread", "linkedin_post", "blog_post", "email"]),
              required=True, help="Content type")
@click.option("--channel", type=click.Choice(["twitter", "linkedin", "medium", "email"]),
              required=True, help="Target channel")
@click.option("--tone", type=click.Choice(["technical", "conversational", "visionary"]),
              default="conversational", help="Content tone")
@click.option("--topic", required=True, help="Content topic")
def generate(content_type, channel, tone, topic):
    """Generate individual content piece"""
    
    click.echo(f"Generating {content_type} for {channel}...")
    
    try:
        response = requests.post(
            f"{API_BASE}/content/generate",
            params={
                "content_type": content_type,
                "channel": channel,
                "tone": tone,
                "topic": topic
            }
        )
        response.raise_for_status()
        
        result = response.json()
        content = result['content']
        
        click.echo("\n" + click.style("Generated Content", bold=True, fg="green"))
        click.echo("=" * 50)
        
        if isinstance(content, dict):
            # Structured content
            if 'title' in content:
                click.echo(click.style(f"Title: {content['title']}", bold=True))
            
            click.echo(f"\n{content.get('content', str(content))}")
            
            if 'hashtags' in content:
                click.echo(f"\nHashtags: {' '.join(content['hashtags'])}")
            
            if 'cta' in content:
                click.echo(f"\nCTA: {content['cta']}")
        else:
            # Plain text content
            click.echo(content)
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
def templates():
    """List available campaign templates"""
    
    try:
        response = requests.get(f"{API_BASE}/templates")
        response.raise_for_status()
        
        templates = response.json()['templates']
        
        click.echo(click.style("Available Campaign Templates", bold=True))
        click.echo("=" * 60)
        
        for template in templates:
            click.echo(f"\n{click.style(template['name'], bold=True)}")
            click.echo(f"  {template['description']}")
            click.echo(f"  Duration: {template['duration_days']} days")
            click.echo(f"  Channels: {', '.join(template['channels'])}")
            click.echo(f"  Content pieces: {template['content_pieces']}")
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
@click.argument("campaign_id")
def optimize(campaign_id):
    """Optimize campaign based on performance"""
    
    click.echo(f"Optimizing campaign {campaign_id}...")
    
    try:
        response = requests.post(f"{API_BASE}/campaigns/{campaign_id}/optimize")
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(click.style("✓ Campaign optimized!", fg="green"))
        click.echo(f"Optimizations applied: {result['optimizations_applied']}")
        
        if result['improvements']:
            click.echo("\n" + click.style("Improvements Applied:", bold=True))
            for improvement in result['improvements']:
                click.echo(f"\n{improvement['type']}:")
                for suggestion in improvement.get('suggestions', []):
                    click.echo(f"  • {suggestion}")
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


@cli.command()
def channels():
    """List available marketing channels"""
    
    try:
        response = requests.get(f"{API_BASE}/channels")
        response.raise_for_status()
        
        channels = response.json()['channels']
        
        click.echo(click.style("Available Marketing Channels", bold=True))
        click.echo("=" * 60)
        
        channel_data = []
        for channel in channels:
            channel_data.append([
                channel['name'],
                ', '.join(channel['optimal_times']),
                channel.get('character_limit', 'None')
            ])
        
        headers = ["Channel", "Optimal Times", "Char Limit"]
        click.echo(tabulate(channel_data, headers=headers, tablefmt="grid"))
        
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()