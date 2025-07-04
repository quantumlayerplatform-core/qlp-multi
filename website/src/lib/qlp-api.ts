/**
 * QLP API Client - Complete Pipeline Integration
 * Connects frontend to the complete NLP → Capsule → Validation → Billing flow
 */

export interface QLPRequest {
  id?: string
  description: string
  user_id: string
  tenant_id: string
  requirements?: string[]
  constraints?: Record<string, any>
  metadata?: {
    target_score?: number
    save_to_disk?: boolean
    complexity?: 'simple' | 'medium' | 'complex'
    tier?: 'free' | 'pro' | 'enterprise'
  }
}

export interface PipelineResult {
  pipeline_id: string
  status: 'processing' | 'completed' | 'failed'
  total_time: number
  timestamp: number
  
  capsule: {
    id: string
    request_id: string
    title: string
    files_generated: number
    languages: string[]
    output_path?: string
  }
  
  validation: {
    runtime: {
      success: boolean
      confidence_score: number
      execution_time: number
      memory_usage: number
      language: string
      install_success: boolean
      runtime_success: boolean
      test_success: boolean
      issues: string[]
      recommendations: string[]
    }
    confidence: {
      overall_score: number
      confidence_level: 'critical' | 'high' | 'medium' | 'low' | 'very_low'
      deployment_recommendation: string
      estimated_success_probability: number
      human_review_required: boolean
      risk_factors: string[]
      success_indicators: string[]
    }
  }
  
  deployment: {
    ready: boolean
    recommendation: string
    auto_deployed: boolean
    result?: {
      status: string
      environment: string
      url: string
      deployment_id: string
    }
  }
  
  billing: {
    cost: number
    credits_used: number
    tier: string
    breakdown: {
      generation: number
      validation: number
      confidence: number
      base_fee: number
    }
  }
  
  performance: {
    generation_time: number
    validation_time: number
    confidence_time: number
    total_time: number
    efficiency_score: number
  }
  
  next_steps: string[]
  
  frontend: {
    dashboard_url: string
    validation_url: string
    deployment_url: string
    billing_url: string
    download_url: string
  }
}

export interface UsageStats {
  current_month: {
    capsules_generated: number
    total_cost: number
    credits_used: number
    credits_remaining: number
  }
  tier_limits: {
    max_capsules: number
    max_credits: number
    features: string[]
  }
  upgrade_benefits?: {
    next_tier: string
    additional_features: string[]
    cost_savings: number
  }
}

class QLPAPIClient {
  private baseUrl: string
  private apiKey?: string

  constructor(baseUrl: string = 'http://localhost:8000', apiKey?: string) {
    this.baseUrl = baseUrl
    this.apiKey = apiKey
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers
    }

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`
    }

    const response = await fetch(url, {
      ...options,
      headers
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  /**
   * Run the complete pipeline: NLP → Capsule → Validation → Billing → Deployment
   */
  async runCompletePipeline(request: QLPRequest): Promise<PipelineResult> {
    const requestData = {
      id: request.id || `req-${Date.now()}`,
      description: request.description,
      user_id: request.user_id,
      tenant_id: request.tenant_id,
      requirements: request.requirements || [request.description],
      constraints: request.constraints || {},
      metadata: {
        target_score: 0.85,
        save_to_disk: true,
        complexity: 'medium',
        ...request.metadata
      }
    }

    return this.request<PipelineResult>('/generate/complete-pipeline', {
      method: 'POST',
      body: JSON.stringify(requestData)
    })
  }

  /**
   * Generate capsule only (without validation/billing)
   */
  async generateCapsule(request: QLPRequest): Promise<any> {
    return this.request('/generate/robust-capsule', {
      method: 'POST',
      body: JSON.stringify(request)
    })
  }

  /**
   * Validate an existing capsule
   */
  async validateCapsule(capsuleData: any): Promise<any> {
    return this.request('/validate/capsule/complete', {
      method: 'POST',
      body: JSON.stringify({ capsule: capsuleData })
    })
  }

  /**
   * Get capsule details
   */
  async getCapsule(capsuleId: string): Promise<any> {
    return this.request(`/capsule/${capsuleId}`)
  }

  /**
   * Download capsule files
   */
  async downloadCapsule(capsuleId: string, format: 'zip' | 'tar' | 'tar.gz' = 'zip'): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/capsule/${capsuleId}/export/${format}`)
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }
    return response.blob()
  }

  /**
   * Get user usage statistics and billing info
   */
  async getUsageStats(userId: string): Promise<UsageStats> {
    return this.request(`/billing/usage/${userId}`)
  }

  /**
   * Get available pricing tiers
   */
  async getPricingTiers(): Promise<any> {
    return this.request('/billing/tiers')
  }

  /**
   * Upgrade user tier
   */
  async upgradeTier(userId: string, tier: string, paymentToken: string): Promise<any> {
    return this.request('/billing/upgrade', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        tier,
        payment_token: paymentToken
      })
    })
  }

  /**
   * Submit human review response
   */
  async submitHumanReview(requestId: string, approved: boolean, comments: string): Promise<any> {
    return this.request(`/hitl/respond/${requestId}`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: 'reviewer',
        confidence: approved ? 0.9 : 0.3,
        response: {
          approved,
          comments,
          modifications: {}
        },
        responded_at: new Date().toISOString()
      })
    })
  }

  /**
   * Get pending human review requests
   */
  async getPendingReviews(): Promise<any> {
    return this.request('/hitl/pending')
  }

  /**
   * Deploy capsule to environment
   */
  async deployCapsule(capsuleId: string, environment: string = 'staging'): Promise<any> {
    return this.request(`/capsule/${capsuleId}/deliver`, {
      method: 'POST',
      body: JSON.stringify([
        {
          provider: 'kubernetes',
          destination: environment,
          credentials: {},
          options: {
            namespace: `qlp-${environment}`,
            auto_scaling: true
          }
        }
      ])
    })
  }

  /**
   * Real-time pipeline status updates via Server-Sent Events
   */
  streamPipelineStatus(pipelineId: string, onUpdate: (data: any) => void): EventSource {
    const eventSource = new EventSource(`${this.baseUrl}/pipeline/${pipelineId}/stream`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onUpdate(data)
      } catch (error) {
        console.error('Failed to parse SSE data:', error)
      }
    }
    
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
    }
    
    return eventSource
  }
}

// Export singleton instance
export const qlpApi = new QLPAPIClient()

// Export class for custom instances
export { QLPAPIClient }

// Utility functions for frontend integration
export const utils = {
  /**
   * Format currency for display
   */
  formatCurrency: (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  },

  /**
   * Format duration for display
   */
  formatDuration: (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`
  },

  /**
   * Get confidence level color
   */
  getConfidenceColor: (level: string): string => {
    const colors = {
      critical: 'text-green-600',
      high: 'text-blue-600',
      medium: 'text-yellow-600',
      low: 'text-orange-600',
      very_low: 'text-red-600'
    }
    return colors[level as keyof typeof colors] || 'text-gray-600'
  },

  /**
   * Calculate tier usage percentage
   */
  calculateUsagePercentage: (used: number, limit: number): number => {
    return Math.min((used / limit) * 100, 100)
  },

  /**
   * Determine if user should upgrade
   */
  shouldSuggestUpgrade: (stats: UsageStats): boolean => {
    const usagePercentage = utils.calculateUsagePercentage(
      stats.current_month.credits_used,
      stats.tier_limits.max_credits
    )
    return usagePercentage > 80
  }
}

// Example usage for demo/testing
export const examples = {
  simpleRequest: {
    description: "Create a simple REST API for managing tasks with CRUD operations",
    user_id: "demo-user",
    tenant_id: "demo-tenant",
    metadata: {
      complexity: 'simple' as const,
      target_score: 0.8
    }
  },

  complexRequest: {
    description: "Build a complete JWT authentication system with rate limiting, email verification, password reset, user profiles, admin dashboard, and comprehensive test suite",
    user_id: "demo-user", 
    tenant_id: "demo-tenant",
    requirements: [
      "JWT token-based authentication",
      "Rate limiting for login attempts",
      "Email verification workflow",
      "Password reset functionality",
      "User profile management",
      "Admin dashboard with user management",
      "Comprehensive test coverage",
      "Docker deployment support",
      "API documentation"
    ],
    metadata: {
      complexity: 'complex' as const,
      target_score: 0.9,
      save_to_disk: true
    }
  }
}