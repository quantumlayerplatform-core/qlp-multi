#!/usr/bin/env python3
"""Generate architecture diagram for QLP documentation"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import matplotlib.lines as mlines

# Create figure and axis
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# Define colors
primary_color = '#2E86AB'
secondary_color = '#A23B72'
tertiary_color = '#F18F01'
bg_color = '#F6F6F6'
text_color = '#2D3436'

# Title
ax.text(7, 9.5, 'Quantum Layer Platform Architecture', 
        fontsize=20, fontweight='bold', ha='center', color=text_color)

# Client Layer
client_box = FancyBboxPatch((1, 7.5), 12, 1.2, 
                           boxstyle="round,pad=0.1",
                           facecolor=bg_color, 
                           edgecolor=primary_color,
                           linewidth=2)
ax.add_patch(client_box)
ax.text(7, 8.1, 'Client Layer', fontsize=12, fontweight='bold', ha='center')
ax.text(3, 7.7, 'Web UI', fontsize=10, ha='center')
ax.text(5.5, 7.7, 'REST API', fontsize=10, ha='center')
ax.text(8.5, 7.7, 'CLI Tool', fontsize=10, ha='center')
ax.text(11, 7.7, 'Webhooks', fontsize=10, ha='center')

# API Gateway
gateway_box = FancyBboxPatch((4, 6.2), 6, 0.8,
                           boxstyle="round,pad=0.1",
                           facecolor=secondary_color,
                           edgecolor=secondary_color,
                           alpha=0.8)
ax.add_patch(gateway_box)
ax.text(7, 6.6, 'API Gateway (NGINX)', fontsize=11, ha='center', color='white', fontweight='bold')

# Microservices Layer
services = [
    {'name': 'Meta-Orchestrator', 'port': '8000', 'x': 2, 'y': 4},
    {'name': 'Agent Factory', 'port': '8001', 'x': 5, 'y': 4},
    {'name': 'Validation Mesh', 'port': '8002', 'x': 8, 'y': 4},
    {'name': 'Vector Memory', 'port': '8003', 'x': 11, 'y': 4},
    {'name': 'Execution Sandbox', 'port': '8004', 'x': 6.5, 'y': 2.5}
]

for service in services:
    box = FancyBboxPatch((service['x']-1.2, service['y']-0.4), 2.4, 1,
                        boxstyle="round,pad=0.1",
                        facecolor=primary_color,
                        edgecolor=primary_color,
                        alpha=0.9)
    ax.add_patch(box)
    ax.text(service['x'], service['y']+0.2, service['name'], 
           fontsize=9, ha='center', color='white', fontweight='bold')
    ax.text(service['x'], service['y']-0.1, f"Port {service['port']}", 
           fontsize=8, ha='center', color='white')

# Infrastructure Layer
infra_box = FancyBboxPatch((0.5, 0.2), 13, 1.5,
                          boxstyle="round,pad=0.1",
                          facecolor=bg_color,
                          edgecolor=tertiary_color,
                          linewidth=2)
ax.add_patch(infra_box)
ax.text(7, 1.4, 'Infrastructure Layer', fontsize=12, fontweight='bold', ha='center')

# Infrastructure components
infra_components = [
    {'name': 'PostgreSQL', 'x': 2, 'y': 0.7},
    {'name': 'Redis', 'x': 4.5, 'y': 0.7},
    {'name': 'Qdrant', 'x': 7, 'y': 0.7},
    {'name': 'Temporal', 'x': 9.5, 'y': 0.7},
    {'name': 'Prometheus', 'x': 12, 'y': 0.7}
]

for comp in infra_components:
    box = FancyBboxPatch((comp['x']-0.8, comp['y']-0.2), 1.6, 0.4,
                        boxstyle="round,pad=0.05",
                        facecolor=tertiary_color,
                        edgecolor=tertiary_color,
                        alpha=0.7)
    ax.add_patch(box)
    ax.text(comp['x'], comp['y'], comp['name'], 
           fontsize=8, ha='center', color='white')

# Draw connections
# Client to Gateway
ax.arrow(7, 7.5, 0, -0.6, head_width=0.1, head_length=0.05, 
         fc=primary_color, ec=primary_color, alpha=0.5)

# Gateway to Services
for x in [2, 5, 8, 11]:
    ax.arrow(7, 6.2, x-7, -1.5, head_width=0.1, head_length=0.05,
             fc=primary_color, ec=primary_color, alpha=0.3)

# Services to Infrastructure
for service in services[:4]:
    ax.arrow(service['x'], service['y']-0.4, 0, -1.8, 
             head_width=0.08, head_length=0.04,
             fc=tertiary_color, ec=tertiary_color, alpha=0.3)

# Add legend
legend_elements = [
    mlines.Line2D([0], [0], color=primary_color, lw=4, label='Core Services'),
    mlines.Line2D([0], [0], color=secondary_color, lw=4, label='API Gateway'),
    mlines.Line2D([0], [0], color=tertiary_color, lw=4, label='Infrastructure')
]
ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))

# Add annotations
ax.text(0.5, 9, 'User Requests', fontsize=9, style='italic', alpha=0.7)
ax.text(0.5, 5.5, 'Service Mesh', fontsize=9, style='italic', alpha=0.7)
ax.text(0.5, 2, 'Data Layer', fontsize=9, style='italic', alpha=0.7)

# Key features box
features_box = FancyBboxPatch((10.5, 3), 3, 2,
                             boxstyle="round,pad=0.1",
                             facecolor='white',
                             edgecolor=primary_color,
                             linewidth=1)
ax.add_patch(features_box)
ax.text(12, 4.7, 'Key Features', fontsize=10, fontweight='bold', ha='center')
ax.text(12, 4.4, '• Multi-tier AI Agents', fontsize=8, ha='center')
ax.text(12, 4.1, '• 5-Stage Validation', fontsize=8, ha='center')
ax.text(12, 3.8, '• Semantic Memory', fontsize=8, ha='center')
ax.text(12, 3.5, '• Secure Execution', fontsize=8, ha='center')
ax.text(12, 3.2, '• Cloud Native', fontsize=8, ha='center')

plt.tight_layout()
plt.savefig('docs/qlp-architecture-diagram.png', dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.savefig('docs/qlp-architecture-diagram.pdf', bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.close()

print("Architecture diagram generated:")
print("- docs/qlp-architecture-diagram.png")
print("- docs/qlp-architecture-diagram.pdf")