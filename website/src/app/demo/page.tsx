'use client'

import React, { useState } from 'react'
import QLPPipeline from '@/components/QLPPipeline'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Rocket, 
  DollarSign, 
  Clock, 
  Shield, 
  Users, 
  TrendingUp,
  CheckCircle,
  ArrowRight,
  Star
} from 'lucide-react'

export default function DemoPage() {
  const [completedPipelines, setCompletedPipelines] = useState<any[]>([])
  const [totalRevenue, setTotalRevenue] = useState(0)

  const handlePipelineComplete = (result: any) => {
    setCompletedPipelines(prev => [result, ...prev.slice(0, 4)]) // Keep last 5
    setTotalRevenue(prev => prev + result.billing.cost)
  }

  const demoExamples = [
    {
      title: "JWT Authentication API",
      description: "Create a secure JWT authentication system with rate limiting, password hashing, and user management",
      complexity: "Medium",
      estimatedTime: "45s",
      estimatedCost: "$2.50",
      features: ["JWT tokens", "Rate limiting", "Password hashing", "Docker support"]
    },
    {
      title: "E-commerce Backend",
      description: "Build a complete e-commerce API with products, cart, orders, payments, and admin dashboard",
      complexity: "Complex", 
      estimatedTime: "90s",
      estimatedCost: "$4.75",
      features: ["Product catalog", "Shopping cart", "Payment processing", "Admin panel"]
    },
    {
      title: "Todo List App",
      description: "Simple todo application with CRUD operations and user authentication",
      complexity: "Simple",
      estimatedTime: "30s", 
      estimatedCost: "$1.25",
      features: ["CRUD operations", "User auth", "Simple UI", "Database"]
    }
  ]

  const pricingTiers = [
    {
      name: "Free",
      price: "$0",
      period: "/month",
      features: [
        "5 capsules per month",
        "Basic validation",
        "Community support",
        "Standard templates"
      ],
      limits: "Basic features only",
      buttonText: "Current Plan",
      popular: false
    },
    {
      name: "Pro",
      price: "$29",
      period: "/month", 
      features: [
        "100 capsules per month",
        "Runtime validation",
        "Confidence analysis",
        "Priority support",
        "Custom templates",
        "Auto-deployment"
      ],
      limits: "Perfect for professionals",
      buttonText: "Upgrade Now",
      popular: true
    },
    {
      name: "Enterprise",
      price: "$299",
      period: "/month",
      features: [
        "Unlimited capsules",
        "Custom validators",
        "Private cloud deployment",
        "24/7 dedicated support",
        "SLA guarantee",
        "Advanced analytics",
        "Team collaboration"
      ],
      limits: "For teams and organizations",
      buttonText: "Contact Sales",
      popular: false
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto px-4 py-16">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-4">
              QLP Complete Pipeline Demo
            </h1>
            <p className="text-xl mb-8 text-blue-100">
              Watch your ideas transform into production-ready code in seconds
            </p>
            <div className="flex justify-center gap-8 text-sm">
              <div className="flex items-center gap-2">
                <Rocket className="h-5 w-5" />
                <span>Generate in ~60s</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                <span>Docker Validated</span>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                <span>Usage-based Pricing</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <Tabs defaultValue="demo" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="demo">Live Demo</TabsTrigger>
            <TabsTrigger value="examples">Examples</TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="demo" className="space-y-6">
            <QLPPipeline onComplete={handlePipelineComplete} />
          </TabsContent>

          <TabsContent value="examples" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {demoExamples.map((example, index) => (
                <Card key={index} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg">{example.title}</CardTitle>
                      <Badge variant={
                        example.complexity === 'Simple' ? 'secondary' :
                        example.complexity === 'Medium' ? 'default' : 'destructive'
                      }>
                        {example.complexity}
                      </Badge>
                    </div>
                    <CardDescription className="text-sm">
                      {example.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between text-sm">
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {example.estimatedTime}
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="h-4 w-4" />
                          {example.estimatedCost}
                        </span>
                      </div>
                      
                      <div>
                        <div className="text-sm font-medium mb-2">Features:</div>
                        <div className="flex flex-wrap gap-1">
                          {example.features.map((feature, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs">
                              {feature}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      
                      <Button className="w-full" size="sm">
                        Try This Example
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Alert className="bg-blue-50 border-blue-200">
              <Rocket className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>How it works:</strong> Enter your description → QLP generates complete project → 
                Docker validates code → Confidence engine scores quality → Auto-deploy if ready → 
                Pay only for what you use
              </AlertDescription>
            </Alert>
          </TabsContent>

          <TabsContent value="pricing" className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-4">Simple, Usage-Based Pricing</h2>
              <p className="text-gray-600 text-lg">
                Pay only for the capsules you generate. No hidden fees, no long-term contracts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {pricingTiers.map((tier, index) => (
                <Card key={index} className={`relative ${tier.popular ? 'ring-2 ring-blue-500' : ''}`}>
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-blue-500 text-white flex items-center gap-1">
                        <Star className="h-3 w-3" />
                        Most Popular
                      </Badge>
                    </div>
                  )}
                  
                  <CardHeader className="text-center">
                    <CardTitle className="text-xl">{tier.name}</CardTitle>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-3xl font-bold">{tier.price}</span>
                      <span className="text-gray-600">{tier.period}</span>
                    </div>
                    <CardDescription>{tier.limits}</CardDescription>
                  </CardHeader>
                  
                  <CardContent>
                    <ul className="space-y-3 mb-6">
                      {tier.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    
                    <Button 
                      className="w-full" 
                      variant={tier.popular ? "default" : "outline"}
                      disabled={tier.name === "Free"}
                    >
                      {tier.buttonText}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Usage-Based Billing Breakdown</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="font-medium">Generation</div>
                  <div className="text-gray-600">$0.10/second</div>
                </div>
                <div>
                  <div className="font-medium">Validation</div>
                  <div className="text-gray-600">$0.15/second</div>
                </div>
                <div>
                  <div className="font-medium">Confidence Analysis</div>
                  <div className="text-gray-600">$0.20/second</div>
                </div>
                <div>
                  <div className="font-medium">Base Fee</div>
                  <div className="text-gray-600">$1.00/capsule</div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Total Pipelines</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{completedPipelines.length}</div>
                  <div className="text-xs text-gray-600">This session</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Revenue Generated</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    ${totalRevenue.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-600">Demo revenue</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">
                    {completedPipelines.length > 0 ? 
                      Math.round(completedPipelines.reduce((acc, p) => acc + p.validation.confidence.overall_score, 0) / completedPipelines.length * 100) 
                      : 0}%
                  </div>
                  <div className="text-xs text-gray-600">Quality score</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Auto-Deploy Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-purple-600">
                    {completedPipelines.length > 0 ?
                      Math.round(completedPipelines.filter(p => p.deployment.auto_deployed).length / completedPipelines.length * 100)
                      : 0}%
                  </div>
                  <div className="text-xs text-gray-600">Automated</div>
                </CardContent>
              </Card>
            </div>

            {completedPipelines.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Recent Pipeline Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {completedPipelines.map((pipeline, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <div className="font-medium">{pipeline.capsule.title}</div>
                          <div className="text-sm text-gray-600">
                            {pipeline.capsule.files_generated} files • {pipeline.performance.total_time.toFixed(1)}s
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <Badge className={
                            pipeline.validation.confidence.confidence_level === 'critical' ? 'bg-green-500' :
                            pipeline.validation.confidence.confidence_level === 'high' ? 'bg-blue-500' :
                            pipeline.validation.confidence.confidence_level === 'medium' ? 'bg-yellow-500' :
                            'bg-red-500'
                          }>
                            {Math.round(pipeline.validation.confidence.overall_score * 100)}%
                          </Badge>
                          <div className="text-sm font-medium text-green-600">
                            ${pipeline.billing.cost.toFixed(2)}
                          </div>
                          {pipeline.deployment.auto_deployed && (
                            <Badge variant="outline" className="text-xs">
                              Auto-deployed
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Business Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span>Average Revenue per Capsule:</span>
                      <span className="font-medium">
                        ${completedPipelines.length > 0 ? (totalRevenue / completedPipelines.length).toFixed(2) : '0.00'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Success Rate:</span>
                      <span className="font-medium">
                        {completedPipelines.length > 0 ?
                          Math.round(completedPipelines.filter(p => p.validation.runtime.success).length / completedPipelines.length * 100)
                          : 0}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Average Generation Time:</span>
                      <span className="font-medium">
                        {completedPipelines.length > 0 ?
                          (completedPipelines.reduce((acc, p) => acc + p.performance.generation_time, 0) / completedPipelines.length).toFixed(1)
                          : 0}s
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    User Experience
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span>Human Review Rate:</span>
                      <span className="font-medium">
                        {completedPipelines.length > 0 ?
                          Math.round(completedPipelines.filter(p => p.validation.confidence.human_review_required).length / completedPipelines.length * 100)
                          : 0}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Time to Deployment:</span>
                      <span className="font-medium">
                        {completedPipelines.length > 0 ?
                          (completedPipelines.reduce((acc, p) => acc + p.performance.total_time, 0) / completedPipelines.length).toFixed(1)
                          : 0}s
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Efficiency Score:</span>
                      <span className="font-medium">
                        {completedPipelines.length > 0 ?
                          Math.round(completedPipelines.reduce((acc, p) => acc + p.performance.efficiency_score, 0) / completedPipelines.length * 100)
                          : 0}%
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}