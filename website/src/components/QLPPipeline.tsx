'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  Download, 
  Play, 
  DollarSign,
  FileCode,
  TestTube,
  Shield,
  Rocket,
  Monitor,
  User
} from 'lucide-react'

interface PipelineResult {
  pipeline_id: string
  status: string
  total_time: number
  capsule: {
    id: string
    title: string
    files_generated: number
    languages: string[]
  }
  validation: {
    runtime: {
      success: boolean
      confidence_score: number
      language: string
      execution_time: number
      memory_usage: number
      issues: string[]
      recommendations: string[]
    }
    confidence: {
      overall_score: number
      confidence_level: string
      deployment_recommendation: string
      estimated_success_probability: number
      human_review_required: boolean
      risk_factors: string[]
      success_indicators: string[]
    }
  }
  deployment: {
    ready: boolean
    auto_deployed: boolean
    result?: {
      status: string
      environment: string
      url: string
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

interface QLPPipelineProps {
  onComplete?: (result: PipelineResult) => void
}

export default function QLPPipeline({ onComplete }: QLPPipelineProps) {
  const [request, setRequest] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const steps = [
    { name: 'Generate', icon: FileCode, description: 'Creating QLCapsule from your request' },
    { name: 'Validate', icon: TestTube, description: 'Running Docker validation and tests' },
    { name: 'Analyze', icon: Shield, description: 'Multi-dimensional confidence analysis' },
    { name: 'Deploy', icon: Rocket, description: 'Making deployment decision' },
    { name: 'Bill', icon: DollarSign, description: 'Calculating usage and costs' }
  ]

  const runPipeline = async () => {
    if (!request.trim()) return
    
    setIsProcessing(true)
    setCurrentStep(0)
    setError(null)
    setResult(null)

    try {
      // Simulate step progression
      const stepInterval = setInterval(() => {
        setCurrentStep(prev => {
          if (prev < steps.length - 1) return prev + 1
          clearInterval(stepInterval)
          return prev
        })
      }, 2000)

      // Call the complete pipeline endpoint
      const response = await fetch('http://localhost:8000/generate/complete-pipeline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: `req-${Date.now()}`,
          description: request,
          user_id: 'demo-user',
          tenant_id: 'demo-tenant',
          requirements: [request],
          constraints: {},
          metadata: {
            target_score: 0.85,
            save_to_disk: true,
            complexity: 'medium'
          }
        })
      })

      if (!response.ok) {
        throw new Error(`Pipeline failed: ${response.statusText}`)
      }

      const pipelineResult = await response.json()
      setResult(pipelineResult)
      onComplete?.(pipelineResult)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline failed')
    } finally {
      setIsProcessing(false)
      setCurrentStep(steps.length - 1)
    }
  }

  const getConfidenceBadgeColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-green-500'
      case 'high': return 'bg-blue-500'
      case 'medium': return 'bg-yellow-500'
      case 'low': return 'bg-orange-500'
      default: return 'bg-red-500'
    }
  }

  const getDeploymentIcon = (recommendation: string) => {
    if (recommendation.includes('🚀')) return <Rocket className="h-5 w-5 text-green-500" />
    if (recommendation.includes('✅')) return <CheckCircle className="h-5 w-5 text-blue-500" />
    if (recommendation.includes('⚠️')) return <AlertTriangle className="h-5 w-5 text-yellow-500" />
    if (recommendation.includes('🔍')) return <User className="h-5 w-5 text-orange-500" />
    return <AlertTriangle className="h-5 w-5 text-red-500" />
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      {/* Input Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            QLP Complete Pipeline
          </CardTitle>
          <CardDescription>
            Enter your project description and watch QLP generate, validate, and deploy your code
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            className="w-full h-32 p-3 border rounded-md resize-none"
            placeholder="Describe your project... (e.g., 'Create a JWT authentication API with rate limiting and Docker support')"
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            disabled={isProcessing}
          />
          <div className="flex gap-2">
            <Button 
              onClick={runPipeline} 
              disabled={isProcessing || !request.trim()}
              className="flex items-center gap-2"
            >
              {isProcessing ? <Clock className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {isProcessing ? 'Processing...' : 'Run Pipeline'}
            </Button>
            {result && (
              <Button variant="outline" asChild>
                <a href={result.frontend.download_url} download>
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </a>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Progress Section */}
      {isProcessing && (
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Progress value={(currentStep + 1) / steps.length * 100} className="w-full" />
              <div className="grid grid-cols-5 gap-4">
                {steps.map((step, index) => {
                  const Icon = step.icon
                  const isActive = index <= currentStep
                  const isCurrent = index === currentStep
                  
                  return (
                    <div key={step.name} className={`text-center p-3 rounded-lg border ${
                      isActive ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                    }`}>
                      <Icon className={`h-6 w-6 mx-auto mb-2 ${
                        isActive ? 'text-blue-600' : 'text-gray-400'
                      } ${isCurrent ? 'animate-pulse' : ''}`} />
                      <div className={`font-medium ${isActive ? 'text-blue-900' : 'text-gray-600'}`}>
                        {step.name}
                      </div>
                      <div className={`text-xs ${isActive ? 'text-blue-700' : 'text-gray-500'}`}>
                        {step.description}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Section */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Results Section */}
      {result && (
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="validation">Validation</TabsTrigger>
            <TabsTrigger value="deployment">Deployment</TabsTrigger>
            <TabsTrigger value="billing">Billing</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Capsule Generated</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Files:</span>
                      <span className="font-medium">{result.capsule.files_generated}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Language:</span>
                      <Badge variant="secondary">{result.capsule.languages[0]}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">ID:</span>
                      <span className="text-xs font-mono">{result.capsule.id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Confidence Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">
                        {Math.round(result.validation.confidence.overall_score * 100)}%
                      </div>
                      <Badge className={getConfidenceBadgeColor(result.validation.confidence.confidence_level)}>
                        {result.validation.confidence.confidence_level.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="text-sm text-center text-gray-600">
                      Success Probability: {Math.round(result.validation.confidence.estimated_success_probability * 100)}%
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Deployment Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      {getDeploymentIcon(result.validation.confidence.deployment_recommendation)}
                      <span className="text-sm">
                        {result.deployment.ready ? 'Ready' : 'Not Ready'}
                      </span>
                    </div>
                    {result.deployment.auto_deployed && result.deployment.result && (
                      <div className="space-y-1">
                        <div className="text-xs text-gray-600">Auto-deployed:</div>
                        <a 
                          href={result.deployment.result.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline text-sm"
                        >
                          {result.deployment.result.url}
                        </a>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Next Steps */}
            <Card>
              <CardHeader>
                <CardTitle>Next Steps</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.next_steps.map((step, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-blue-500" />
                      <span className="text-sm">{step}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="validation" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Runtime Validation</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      {result.validation.runtime.success ? 
                        <CheckCircle className="h-5 w-5 text-green-500" /> : 
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                      }
                      <span className="font-medium">
                        {result.validation.runtime.success ? 'Passed' : 'Failed'}
                      </span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Execution Time:</span>
                        <span>{result.validation.runtime.execution_time.toFixed(1)}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Memory Usage:</span>
                        <span>{result.validation.runtime.memory_usage}MB</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Language:</span>
                        <Badge variant="outline">{result.validation.runtime.language}</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Risk Assessment</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {result.validation.confidence.risk_factors.length > 0 ? (
                      <div>
                        <div className="text-sm font-medium text-red-600 mb-2">Risk Factors:</div>
                        <ul className="space-y-1">
                          {result.validation.confidence.risk_factors.map((risk, index) => (
                            <li key={index} className="text-sm text-red-700 flex items-start gap-2">
                              <AlertTriangle className="h-3 w-3 mt-1 flex-shrink-0" />
                              {risk}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className="text-green-600 text-sm">No significant risks detected</div>
                    )}
                    
                    {result.validation.confidence.success_indicators.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-green-600 mb-2">Success Indicators:</div>
                        <ul className="space-y-1">
                          {result.validation.confidence.success_indicators.slice(0, 3).map((indicator, index) => (
                            <li key={index} className="text-sm text-green-700 flex items-start gap-2">
                              <CheckCircle className="h-3 w-3 mt-1 flex-shrink-0" />
                              {indicator}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="deployment" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Deployment Recommendation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
                    {getDeploymentIcon(result.validation.confidence.deployment_recommendation)}
                    <span className="text-lg font-medium">
                      {result.validation.confidence.deployment_recommendation}
                    </span>
                  </div>
                  
                  {result.deployment.auto_deployed && result.deployment.result && (
                    <div className="p-4 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Rocket className="h-5 w-5 text-green-600" />
                        <span className="font-medium text-green-800">Auto-Deployed</span>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div><strong>Environment:</strong> {result.deployment.result.environment}</div>
                        <div><strong>Status:</strong> {result.deployment.result.status}</div>
                        <div>
                          <strong>URL:</strong> 
                          <a 
                            href={result.deployment.result.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="ml-2 text-blue-600 hover:underline"
                          >
                            {result.deployment.result.url}
                          </a>
                        </div>
                      </div>
                    </div>
                  )}

                  {result.validation.confidence.human_review_required && (
                    <Alert className="border-orange-200 bg-orange-50">
                      <User className="h-4 w-4 text-orange-600" />
                      <AlertDescription className="text-orange-800">
                        Human review required before deployment. A team member will review this capsule.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="billing" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="h-5 w-5" />
                    Usage Cost
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center mb-4">
                    <div className="text-3xl font-bold text-green-600">
                      ${result.billing.cost.toFixed(2)}
                    </div>
                    <div className="text-sm text-gray-600">
                      {result.billing.credits_used} credits used
                    </div>
                    <Badge variant="outline" className="mt-2">
                      {result.billing.tier.toUpperCase()} tier
                    </Badge>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Generation:</span>
                      <span>${result.billing.breakdown.generation.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Validation:</span>
                      <span>${result.billing.breakdown.validation.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Confidence Analysis:</span>
                      <span>${result.billing.breakdown.confidence.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Base Fee:</span>
                      <span>${result.billing.breakdown.base_fee.toFixed(2)}</span>
                    </div>
                    <hr className="my-2" />
                    <div className="flex justify-between font-medium">
                      <span>Total:</span>
                      <span>${result.billing.cost.toFixed(2)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Upgrade Benefits</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="text-sm">
                      <div className="font-medium mb-1">Enterprise Features:</div>
                      <ul className="space-y-1 text-gray-600">
                        <li>• Custom validation rules</li>
                        <li>• Priority processing</li>
                        <li>• Advanced deployment options</li>
                        <li>• 24/7 support</li>
                      </ul>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      Upgrade Plan
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Monitor className="h-5 w-5" />
                    Execution Times
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Generation:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full" 
                            style={{width: `${(result.performance.generation_time / result.performance.total_time) * 100}%`}}
                          />
                        </div>
                        <span className="text-sm font-medium">{result.performance.generation_time.toFixed(1)}s</span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Validation:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-green-500 h-2 rounded-full" 
                            style={{width: `${(result.performance.validation_time / result.performance.total_time) * 100}%`}}
                          />
                        </div>
                        <span className="text-sm font-medium">{result.performance.validation_time.toFixed(1)}s</span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Confidence:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-purple-500 h-2 rounded-full" 
                            style={{width: `${(result.performance.confidence_time / result.performance.total_time) * 100}%`}}
                          />
                        </div>
                        <span className="text-sm font-medium">{result.performance.confidence_time.toFixed(1)}s</span>
                      </div>
                    </div>
                    <hr />
                    <div className="flex justify-between font-medium">
                      <span>Total Time:</span>
                      <span>{result.performance.total_time.toFixed(1)}s</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Efficiency Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-blue-600 mb-2">
                      {Math.round(result.performance.efficiency_score * 100)}%
                    </div>
                    <div className="text-sm text-gray-600 mb-4">
                      Target: Complete in under 60 seconds
                    </div>
                    <Progress value={result.performance.efficiency_score * 100} className="w-full" />
                    <div className="text-xs text-gray-500 mt-2">
                      {result.performance.efficiency_score >= 0.8 ? 'Excellent' : 
                       result.performance.efficiency_score >= 0.6 ? 'Good' : 
                       result.performance.efficiency_score >= 0.4 ? 'Average' : 'Needs Improvement'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}