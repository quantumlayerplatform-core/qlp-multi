/**
 * Basic usage examples for QLP JavaScript Client
 */

const { QLPClient } = require('@qlp/client');

async function main() {
  // Initialize client
  const client = new QLPClient({
    apiKey: process.env.QLP_API_KEY,
    baseUrl: process.env.QLP_API_URL || 'http://localhost:8000'
  });

  console.log('QLP JavaScript Client - Basic Examples');
  console.log('=====================================\n');

  try {
    // Example 1: Simple function generation
    console.log('1. Generating a simple function...');
    const factorial = await client.generateBasic(
      'Create a JavaScript function to calculate factorial'
    );
    
    console.log('✓ Generated successfully!');
    console.log(`  Capsule ID: ${factorial.capsuleId}`);
    console.log(`  Files: ${Object.keys(factorial.sourceCode).join(', ')}`);
    console.log('\n  Generated code:');
    console.log('  ' + '-'.repeat(40));
    console.log(factorial.sourceCode['index.js'] || factorial.sourceCode['main.js']);
    
    // Example 2: REST API generation
    console.log('\n\n2. Generating a REST API...');
    const api = await client.generateComplete(
      'Create a REST API for a blog with posts and comments',
      {
        constraints: {
          language: 'javascript',
          framework: 'express'
        }
      }
    );
    
    console.log('✓ API generated successfully!');
    console.log(`  Files generated: ${Object.keys(api.sourceCode).length}`);
    console.log('  File list:');
    Object.keys(api.sourceCode).forEach(file => {
      console.log(`    - ${file}`);
    });
    
    // Example 3: Async workflow monitoring
    console.log('\n\n3. Starting async workflow...');
    const workflow = await client.generate({
      description: 'Create a React component for a todo list',
      options: { mode: 'complete' }
    });
    
    console.log(`  Workflow ID: ${workflow.workflowId}`);
    console.log('  Checking status...');
    
    // Check status a few times
    for (let i = 0; i < 3; i++) {
      const status = await client.getStatus(workflow.workflowId);
      console.log(`  Status: ${status.status} - ${status.progress.message}`);
      
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        break;
      }
      
      // Wait 2 seconds before next check
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Run the examples
main().catch(console.error);