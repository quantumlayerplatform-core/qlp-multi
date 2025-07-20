/**
 * Quantum Layer Platform JavaScript/TypeScript Client
 * 
 * Official client library for the QLP v2 API
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

// Types
export type ExecutionMode = 'basic' | 'complete' | 'robust';
export type DownloadFormat = 'zip' | 'tar' | 'targz';

export interface ExecutionOptions {
  mode?: ExecutionMode;
  tierOverride?: string;
  github?: {
    enabled: boolean;
    token: string;
    repoName: string;
    private?: boolean;
    createPR?: boolean;
    enterpriseStructure?: boolean;
  };
  delivery?: {
    format?: DownloadFormat;
    stream?: boolean;
    method?: 'download' | 'email' | 's3';
  };
  validation?: {
    strict?: boolean;
    security?: boolean;
    performance?: boolean;
  };
  metadata?: Record<string, any>;
}

export interface GenerateRequest {
  description: string;
  userId?: string;
  tenantId?: string;
  options?: ExecutionOptions;
  constraints?: Record<string, any>;
  requirements?: string;
}

export interface WorkflowResult {
  workflowId: string;
  requestId: string;
  status: string;
  message: string;
  links: {
    status: string;
    cancel: string;
    result: string;
  };
  metadata: {
    mode: string;
    estimatedDuration: string;
    features: string[];
  };
}

export interface WorkflowStatus {
  workflowId: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  executionTime: number | null;
  progress: {
    percentage: number;
    currentStep: string;
    message: string;
  };
  resultLink?: string;
}

export interface CapsuleResult {
  capsuleId: string;
  requestId: string;
  status: string;
  sourceCode: Record<string, string>;
  downloads: {
    zip: string;
    tar: string;
    targz: string;
  };
  metadata: Record<string, any>;
}

export interface QLPClientConfig {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
}

/**
 * QLP Client for interacting with the Quantum Layer Platform API
 */
export class QLPClient {
  private client: AxiosInstance;
  
  constructor(config: QLPClientConfig = {}) {
    const {
      apiKey = process.env.QLP_API_KEY,
      baseUrl = 'https://api.quantumlayerplatform.com',
      timeout = 300000 // 5 minutes
    } = config;
    
    this.client = axios.create({
      baseURL: baseUrl,
      timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'QLP-JS-Client/2.0',
        ...(apiKey && { 'Authorization': `Bearer ${apiKey}` })
      }
    });
    
    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      this.handleError
    );
  }
  
  /**
   * Generate code from natural language description
   */
  async generate(request: GenerateRequest | string): Promise<WorkflowResult> {
    const payload: GenerateRequest = typeof request === 'string' 
      ? { description: request }
      : request;
      
    // Set defaults
    payload.userId = payload.userId || 'user';
    payload.tenantId = payload.tenantId || 'default';
    payload.options = payload.options || { mode: 'complete' };
    
    const response = await this.client.post<WorkflowResult>('/v2/execute', payload);
    return response.data;
  }
  
  /**
   * Get workflow status
   */
  async getStatus(workflowId: string): Promise<WorkflowStatus> {
    const response = await this.client.get<WorkflowStatus>(`/v2/workflows/${workflowId}`);
    return response.data;
  }
  
  /**
   * Get workflow result
   */
  async getResult(workflowId: string): Promise<CapsuleResult> {
    const response = await this.client.get<CapsuleResult>(`/v2/workflows/${workflowId}/result`);
    return response.data;
  }
  
  /**
   * Cancel a running workflow
   */
  async cancelWorkflow(workflowId: string): Promise<{ workflowId: string; status: string; message: string }> {
    const response = await this.client.post(`/v2/workflows/${workflowId}/cancel`);
    return response.data;
  }
  
  /**
   * Download capsule in specified format
   */
  async downloadCapsule(capsuleId: string, format: DownloadFormat = 'zip'): Promise<Blob> {
    const response = await this.client.get(`/v2/capsules/${capsuleId}/download`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  }
  
  /**
   * Wait for workflow completion
   */
  async waitForCompletion(
    workflowId: string,
    options: { pollInterval?: number; timeout?: number } = {}
  ): Promise<CapsuleResult> {
    const { pollInterval = 2000, timeout = 300000 } = options;
    const startTime = Date.now();
    
    while (true) {
      const status = await this.getStatus(workflowId);
      
      if (status.status === 'COMPLETED') {
        return await this.getResult(workflowId);
      } else if (status.status === 'FAILED') {
        throw new Error(`Workflow failed: ${workflowId}`);
      } else if (status.status === 'CANCELLED') {
        throw new Error(`Workflow cancelled: ${workflowId}`);
      }
      
      // Check timeout
      if (timeout && (Date.now() - startTime) > timeout) {
        throw new Error(`Workflow did not complete within ${timeout}ms`);
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }
  
  /**
   * Generate and wait for completion
   */
  async generateAndWait(request: GenerateRequest | string): Promise<CapsuleResult> {
    const workflow = await this.generate(request);
    return await this.waitForCompletion(workflow.workflowId);
  }
  
  // Convenience methods
  
  /**
   * Generate with basic mode (fast, minimal validation)
   */
  async generateBasic(description: string, options?: Partial<GenerateRequest>): Promise<CapsuleResult> {
    const request: GenerateRequest = {
      description,
      ...options,
      options: { ...options?.options, mode: 'basic' }
    };
    return this.generateAndWait(request);
  }
  
  /**
   * Generate with complete mode (standard validation and tests)
   */
  async generateComplete(description: string, options?: Partial<GenerateRequest>): Promise<CapsuleResult> {
    const request: GenerateRequest = {
      description,
      ...options,
      options: { ...options?.options, mode: 'complete' }
    };
    return this.generateAndWait(request);
  }
  
  /**
   * Generate with robust mode (production-grade)
   */
  async generateRobust(description: string, options?: Partial<GenerateRequest>): Promise<CapsuleResult> {
    const request: GenerateRequest = {
      description,
      ...options,
      options: { ...options?.options, mode: 'robust' }
    };
    return this.generateAndWait(request);
  }
  
  /**
   * Generate and push to GitHub
   */
  async generateWithGitHub(
    description: string,
    githubOptions: {
      token: string;
      repoName: string;
      private?: boolean;
    },
    options?: Partial<GenerateRequest>
  ): Promise<CapsuleResult> {
    const request: GenerateRequest = {
      description,
      ...options,
      options: {
        ...options?.options,
        github: {
          enabled: true,
          ...githubOptions
        }
      }
    };
    return this.generateAndWait(request);
  }
  
  /**
   * Handle API errors
   */
  private handleError(error: AxiosError): Promise<never> {
    if (error.response) {
      // API returned an error response
      const { status, data } = error.response;
      const message = (data as any)?.detail || (data as any)?.error || 'API Error';
      
      if (status === 429) {
        throw new Error(`Rate limit exceeded. ${message}`);
      } else if (status === 401) {
        throw new Error('Authentication failed. Check your API key.');
      } else if (status === 403) {
        throw new Error('Access forbidden. Check your permissions.');
      } else {
        throw new Error(`API Error (${status}): ${message}`);
      }
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('No response from server. Check your connection.');
    } else {
      // Something else happened
      throw error;
    }
  }
}

// Export default instance for convenience
export const qlp = new QLPClient();

// Re-export for convenience
export default QLPClient;