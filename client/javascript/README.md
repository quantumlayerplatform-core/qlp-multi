# QLP JavaScript/TypeScript Client

Official JavaScript/TypeScript client library for the Quantum Layer Platform v2 API.

## Installation

```bash
npm install @qlp/client
# or
yarn add @qlp/client
# or
pnpm add @qlp/client
```

## Quick Start

```javascript
import { QLPClient } from '@qlp/client';

// Initialize client
const client = new QLPClient({
  apiKey: 'your-api-key'
});

// Generate code
const result = await client.generateAndWait(
  'Create a REST API for user management with authentication'
);

// Access generated code
console.log(result.sourceCode);
```

## Usage Examples

### Basic Usage

```javascript
import { QLPClient } from '@qlp/client';

const client = new QLPClient({ apiKey: process.env.QLP_API_KEY });

// Simple function generation
const result = await client.generateBasic(
  'Create a function to validate email addresses'
);

console.log(result.sourceCode['main.js']);
```

### TypeScript with Full Type Support

```typescript
import { QLPClient, GenerateRequest, CapsuleResult } from '@qlp/client';

const client = new QLPClient({ apiKey: process.env.QLP_API_KEY });

const request: GenerateRequest = {
  description: 'Create a TypeScript REST API with Express',
  options: {
    mode: 'complete',
    tierOverride: 'T2'
  },
  constraints: {
    language: 'typescript',
    framework: 'express'
  }
};

const result: CapsuleResult = await client.generateAndWait(request);
```

### Production Application

```javascript
// Generate production-grade application
const result = await client.generateRobust(
  'Create an e-commerce platform with microservices architecture',
  {
    constraints: {
      language: 'javascript',
      framework: 'nestjs',
      database: 'postgresql'
    }
  }
);
```

### GitHub Integration

```javascript
// Generate and push to GitHub
const result = await client.generateWithGitHub(
  'Create a machine learning data pipeline',
  {
    token: process.env.GITHUB_TOKEN,
    repoName: 'ml-pipeline',
    private: true
  }
);

console.log(`Repository created: ${result.metadata.githubUrl}`);
```

### Monitoring Progress

```javascript
// Start generation
const workflow = await client.generate({
  description: 'Create a complex application',
  options: { mode: 'robust' }
});

console.log(`Workflow started: ${workflow.workflowId}`);

// Check status periodically
const checkStatus = async () => {
  const status = await client.getStatus(workflow.workflowId);
  console.log(`Status: ${status.status} (${status.progress.percentage}%)`);
  
  if (status.status === 'COMPLETED') {
    const result = await client.getResult(workflow.workflowId);
    console.log('Generation complete!');
    return result;
  } else if (status.status === 'RUNNING') {
    setTimeout(checkStatus, 2000);
  }
};

checkStatus();
```

### Download Generated Code

```javascript
// Get result
const result = await client.generateAndWait('Create a web scraper');

// Download as zip
const zipBlob = await client.downloadCapsule(result.capsuleId, 'zip');

// Save to file (Node.js)
import { writeFileSync } from 'fs';
const buffer = await zipBlob.arrayBuffer();
writeFileSync('generated-code.zip', Buffer.from(buffer));
```

### Error Handling

```javascript
try {
  const result = await client.generateAndWait('Create something');
} catch (error) {
  if (error.message.includes('Rate limit')) {
    console.error('Too many requests. Please wait and try again.');
  } else if (error.message.includes('Authentication failed')) {
    console.error('Invalid API key');
  } else if (error.message.includes('Workflow failed')) {
    console.error('Generation failed. Check your description.');
  } else {
    console.error('Error:', error.message);
  }
}
```

## API Reference

### Constructor

```typescript
new QLPClient(config?: {
  apiKey?: string;      // API key (defaults to QLP_API_KEY env var)
  baseUrl?: string;     // API base URL (defaults to production)
  timeout?: number;     // Request timeout in ms (default: 300000)
})
```

### Methods

#### `generate(request: GenerateRequest | string): Promise<WorkflowResult>`
Start a code generation workflow.

#### `getStatus(workflowId: string): Promise<WorkflowStatus>`
Get current workflow status.

#### `getResult(workflowId: string): Promise<CapsuleResult>`
Get workflow result (completed workflows only).

#### `waitForCompletion(workflowId: string, options?): Promise<CapsuleResult>`
Wait for workflow to complete.

#### `generateAndWait(request: GenerateRequest | string): Promise<CapsuleResult>`
Generate and wait for completion (convenience method).

#### `generateBasic(description: string, options?): Promise<CapsuleResult>`
Generate with basic mode (fast, minimal validation).

#### `generateComplete(description: string, options?): Promise<CapsuleResult>`
Generate with complete mode (standard validation and tests).

#### `generateRobust(description: string, options?): Promise<CapsuleResult>`
Generate with robust mode (production-grade).

#### `generateWithGitHub(description, githubOptions, options?): Promise<CapsuleResult>`
Generate and push to GitHub.

#### `downloadCapsule(capsuleId: string, format?: 'zip'|'tar'|'targz'): Promise<Blob>`
Download generated code in specified format.

#### `cancelWorkflow(workflowId: string): Promise<CancellationResult>`
Cancel a running workflow.

## Environment Variables

- `QLP_API_KEY`: Your API key (used if not provided in constructor)
- `QLP_API_URL`: API base URL (for development/testing)

## Browser Usage

The client works in modern browsers with ES2015+ support:

```html
<script type="module">
  import { QLPClient } from 'https://unpkg.com/@qlp/client@2.0.0/dist/index.mjs';
  
  const client = new QLPClient({ apiKey: 'your-api-key' });
  const result = await client.generateBasic('Create a countdown timer');
  console.log(result);
</script>
```

## TypeScript Support

Full TypeScript support with exported types:

```typescript
import {
  QLPClient,
  GenerateRequest,
  WorkflowResult,
  WorkflowStatus,
  CapsuleResult,
  ExecutionOptions,
  ExecutionMode
} from '@qlp/client';
```

## Support

- Documentation: https://docs.quantumlayer.com
- API Reference: https://api.quantumlayer.com/docs
- Issues: https://github.com/quantumlayer/qlp-js-client/issues

## License

MIT License - see LICENSE file for details.